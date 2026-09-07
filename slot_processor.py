"""
slot_processor.py — Xử lý 1 slot theo ENCODER SHOT EVENT (software-trigger).

Luồng mới (khớp ladder Ladder_4Slot_Encoder_*_SoftTrig.md):
    1. Thread spawn khi PLC set D10x (object request) — như cũ.
    2. KHÔNG sleep định vị. Chờ shot1 event (M12x, do PLC set khi encoder
       đạt SHOT1_OFFSET) → software-trigger camera → capture → ACK M13x NGAY
       (trước inference, để PLC kịp phát shot2 đúng vị trí).
    3. Inference shot 1. Nếu DEFECT → vẫn chờ shot2 event để ACK (giải phóng
       handshake PLC) nhưng bỏ qua capture/inference.
    4. Shot 2: chờ event M12(x+4) → capture → ACK M13(x+4) → inference.
    5. Merge 2 shot → ghi size/decision → Mx2 (result ready) → Mx1 (ack object).

Event M12x được app.py (vòng poll chính) phát hiện và set vào
threading.Event — thread này chỉ wait, không tự poll PLC.
"""

import time
import threading

from config import Config
from logger_setup import logger


class Stats:
    """Bộ đếm dùng chung giữa 4 thread slot."""

    def __init__(self):
        self._lock = threading.Lock()
        self.data = {
            "total": 0, "pass": 0, "reject": 0,
            "size1": 0, "size2": 0,
            "shot_timeout": 0,
        }

    def update(self, good_final, size_final):
        with self._lock:
            self.data["total"] += 1
            if good_final:
                self.data["pass"] += 1
                if size_final == 1:
                    self.data["size1"] += 1
                elif size_final == 2:
                    self.data["size2"] += 1
            else:
                self.data["reject"] += 1
            return dict(self.data)

    def mark_shot_timeout(self):
        with self._lock:
            self.data["shot_timeout"] += 1

    def summary(self):
        s = self.data
        return (
            f"Total={s['total']} Pass={s['pass']} Reject={s['reject']} "
            f"Size1={s['size1']} Size2={s['size2']} "
            f"ShotTimeout={s['shot_timeout']}"
        )


def merge_results(results):
    """Gộp kết quả nhiều shot của cùng 1 vật.

    Nguyên tắc bảo thủ: chỉ PASS khi TẤT CẢ shot đều PASS (all), lấy conf
    thấp nhất (min) làm conf đại diện. Một mặt bị defect là loại cả quả.
    """
    if not results:
        return 0, False, 0.0
    sizes = [r[0] for r in results]
    goods = [r[1] for r in results]
    confs = [r[2] for r in results]
    good_final = all(goods)
    size_final = max(sizes) if any(goods) else 0
    conf_final = min(confs) if confs else 0.0
    return size_final, good_final, conf_final


class SlotProcessor:
    def __init__(self, camera, classifier, plc, image_saver, stats,
                 shot1_events, shot2_events):
        self.camera = camera
        self.classifier = classifier
        self.plc = plc
        self.image_saver = image_saver
        self.stats = stats
        # threading.Event per slot — app.py set khi thấy coil M12x/M12(x+4) ON
        self.shot1_events = shot1_events
        self.shot2_events = shot2_events

    # ------------------------------------------------------------------
    def _wait_shot(self, ev, slot_idx, obj_id, label):
        """Chờ shot event từ PLC. Trả về True nếu có event.

        ev.clear() TRƯỚC khi wait: nếu app.py còn thấy coil ON (ACK chưa tới
        PLC) nó sẽ set lại -> wait thoát -> chụp/ACK lại. Chống kẹt vĩnh viễn.
        """
        ev.clear()
        t0 = time.time()
        got = ev.wait(timeout=Config.SHOT_EVENT_TIMEOUT_S)
        wait_ms = (time.time() - t0) * 1000
        if not got:
            self.stats.mark_shot_timeout()
            logger.warning(
                f"  [Slot{slot_idx}] {label} event TIMEOUT"
                f" ({Config.SHOT_EVENT_TIMEOUT_S}s, ObjID={obj_id})"
            )
        else:
            logger.info(
                f"  [Slot{slot_idx}] {label} event received"
                f" (waited {wait_ms:.0f}ms, ObjID={obj_id})"
            )
        return got

    def _shoot_and_ack(self, ev, slot_idx, obj_id, label, ack_coil):
        """Chờ event -> trigger camera -> ACK PLC ngay sau capture.

        ACK TRƯỚC inference: PLC cần ACK để chốt shot complete và phát event
        kế tiếp đúng vị trí encoder. Inference chậm không được chặn handshake.
        Trả về (image, event_latency_ms) hoặc (None, ...) nếu fail.
        """
        if not self._wait_shot(ev, slot_idx, obj_id, label):
            return None, None

        t_trig = time.time()
        img = self.camera.capture()          # gửi TriggerSoftware + GetFrame
        trig_ms = (time.time() - t_trig) * 1000

        # ACK về PLC ngay lập tức
        self.plc.write_coil(ack_coil, True)

        if img is None:
            logger.warning(
                f"  [Slot{slot_idx}] {label} capture FAILED"
                f" ({trig_ms:.0f}ms) — đã ACK để PLC không treo"
            )
            return None, trig_ms

        logger.info(
            f"  [Slot{slot_idx}] {label} captured ({trig_ms:.0f}ms"
            f" trigger->frame) + ACK M{ack_coil}"
        )
        return img, trig_ms

    # ------------------------------------------------------------------
    def process(self, slot_idx, obj_id):
        """Xử lý 1 object theo encoder shot events."""
        try:
            t_start = time.time()
            images = []
            results = []

            shot1_ev = self.shot1_events[slot_idx]
            shot2_ev = self.shot2_events[slot_idx]
            ack1 = Config.SHOT1_ACK_COILS[slot_idx]
            ack2 = Config.SHOT2_ACK_COILS[slot_idx]

            # ---- SHOT 1: chờ event encoder -> software trigger -> capture ----
            img1, _ = self._shoot_and_ack(
                shot1_ev, slot_idx, obj_id, "Shot1", ack1
            )

            skip_shot2 = False
            if img1 is None:
                # Không có ảnh shot 1. Vẫn phải chờ shot2 event để ACK,
                # tránh PLC treo latch M12(x+4) (event chỉ phát khi M14x ON
                # nên thường không phát — nhưng chờ ngắn để an toàn).
                skip_shot2 = True
            else:
                t_inf = time.time()
                res1 = self.classifier.classify(img1)
                inf_ms = (time.time() - t_inf) * 1000
                images.append(img1)
                results.append(res1)

                scls, isgood, conf, poly = res1
                if poly is None:
                    logger.info(
                        f"  [Slot{slot_idx}] Shot1: KHONG CO VAT"
                        f" (inf={inf_ms:.0f}ms) — bỏ shot 2"
                    )
                    skip_shot2 = True
                else:
                    slbl = {1: "S", 2: "L"}.get(scls, "-")
                    vlbl = "PASS" if isgood else "DEFECT"
                    logger.info(
                        f"  [Slot{slot_idx}] Shot1: {vlbl} size={slbl}"
                        f" conf={conf:.3f} inf={inf_ms:.0f}ms"
                    )
                    if not isgood:
                        logger.info(
                            f"  [Slot{slot_idx}] Shot1 DEFECT -> skip shot 2"
                            " (vẫn ACK event nếu PLC phát)"
                        )
                        skip_shot2 = True

            # ---- SHOT 2 ----
            if skip_shot2:
                # Không chụp shot 2, nhưng nếu PLC vẫn phát event (trường hợp
                # DEFECT-skip: PLC không biết kết quả AI) thì phải ACK để
                # giải phóng handshake. Chờ ngắn, không log timeout.
                shot2_ev.clear()
                if shot2_ev.wait(timeout=Config.SHOT_EVENT_TIMEOUT_S):
                    self.plc.write_coil(ack2, True)
                    logger.info(
                        f"  [Slot{slot_idx}] Shot2 event: ACK không chụp"
                        " (skip)"
                    )
            else:
                img2, _ = self._shoot_and_ack(
                    shot2_ev, slot_idx, obj_id, "Shot2", ack2
                )
                if img2 is not None:
                    t_inf = time.time()
                    res2 = self.classifier.classify(img2)
                    inf_ms = (time.time() - t_inf) * 1000
                    images.append(img2)
                    results.append(res2)

                    scls, isgood, conf, poly = res2
                    if poly is not None:
                        slbl = {1: "S", 2: "L"}.get(scls, "-")
                        vlbl = "PASS" if isgood else "DEFECT"
                        logger.info(
                            f"  [Slot{slot_idx}] Shot2: {vlbl} size={slbl}"
                            f" conf={conf:.3f} inf={inf_ms:.0f}ms"
                        )

            # ---- Kết quả -> PLC ----
            has_detection = any(r[3] is not None for r in results)
            size_final, good_final = 0, False

            if not results:
                logger.error(
                    f"  [Slot{slot_idx}] No valid captures -> reject"
                )
                self.plc.write_register(Config.SIZE_REGS[slot_idx], 0)
                self.plc.write_register(Config.DECISION_REGS[slot_idx], 2)
            elif not has_detection:
                logger.info(
                    f"  [Slot{slot_idx}] KHONG CO VAT (ObjID={obj_id},"
                    f" {(time.time() - t_start) * 1000:.0f}ms)"
                )
                self.plc.write_register(Config.SIZE_REGS[slot_idx], 0)
                self.plc.write_register(Config.DECISION_REGS[slot_idx], 2)
            else:
                sf, gf, cf = merge_results(results)
                size_final, good_final = sf, gf
                total_ms = (time.time() - t_start) * 1000
                logger.info(
                    f"  [Slot{slot_idx}] MERGED:"
                    f" {'PASS' if gf else 'REJECT'} size={sf}"
                    f" conf={cf:.3f} total={total_ms:.0f}ms"
                )
                self.plc.write_register(
                    Config.SIZE_REGS[slot_idx], sf if gf else 0
                )
                self.plc.write_register(
                    Config.DECISION_REGS[slot_idx], 1 if gf else 2
                )

            # ---- Signal result ready (M12/M22/M32/M42) ----
            # Giữ ON > 1 scan PLC rồi tắt (ladder encoder rung 5 đọc mức logic,
            # có RST Mx2 cuối rung).
            self.plc.write_coil(Config.RESULT_COILS[slot_idx], True)
            time.sleep(Config.RESULT_HOLD_S)
            self.plc.write_coil(Config.RESULT_COILS[slot_idx], False)

            # ---- ACK object (M11/M21/M31/M41) ----
            # Ladder encoder: ACK chỉ xóa request D10x/M10x; slot busy M15x
            # do PLC tự giữ đến RELEASE_OFFSET (quả qua gate).
            self.plc.write_coil(Config.ACK_COILS[slot_idx], True)

            # ---- Async save ----
            if Config.SAVE_IMAGES and images and (
                has_detection or Config.SAVE_NO_DETECTION_IMAGES
            ):
                self.image_saver.submit(
                    images, results, slot_idx, obj_id, size_final, good_final
                )

            self.stats.update(good_final, size_final)
            logger.info(
                f"  [Slot{slot_idx}] Stats: {self.stats.summary()}"
            )

        except Exception as e:
            logger.error(f"[Slot{slot_idx}] Error: {e}", exc_info=True)
            # Chống treo: ACK cả 2 shot + object để PLC không latch vĩnh viễn
            try:
                self.plc.write_coil(Config.SHOT1_ACK_COILS[slot_idx], True)
                self.plc.write_coil(Config.SHOT2_ACK_COILS[slot_idx], True)
                self.plc.write_coil(Config.ACK_COILS[slot_idx], True)
            except Exception:
                pass
