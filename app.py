"""
app.py — Vòng lặp chính: polling PLC (registers + shot event coils),
điều phối state machine 4 slot theo ENCODER SOFTWARE-TRIGGER.

Kiến trúc mới (khớp ladder encoder):
    PLC chốt vị trí từng quả bằng encoder và phát EVENT LATCH:
        M120-M123 = yêu cầu shot 1 (slot 0-3)
        M124-M127 = yêu cầu shot 2
    Vòng poll này phát hiện event -> set threading.Event của slot ->
    thread slot software-trigger camera -> capture -> ghi ACK M130-M137 ->
    PLC xóa event latch.

    Inference chạy trong thread slot, KHÔNG chặn vòng poll này —
    nếu poll đứng thì event shot kế tiếp bị lỡ (PLC latch nên không mất,
    nhưng latency tăng).
"""

import time
import threading

from config import Config
from logger_setup import logger
from camera import HuarayCamera
from classifier import ONNXClassifier
from plc_client import PLCClient
from gate_settings import GateSettings
from image_saver import ImageSaver
from slot_processor import SlotProcessor, Stats

# ==============================================================
# STATE MACHINE per-slot (LEVEL-TRIGGERED — chống deadlock)
#   ST_IDLE       : chờ D10x == 1 (object request từ PLC)
#   ST_PROCESSING : thread đang chạy — chờ shot event M12x/M12(x+4),
#                   trigger camera, inference, trả kết quả
#   ST_WAIT_CLEAR : thread xong, chờ PLC clear D10x về 0
#
# Shot event (M120-M137) được đọc gộp 1 transaction mỗi vòng poll và
# đẩy vào threading.Event per-slot — thread slot tự wait/ACK.
# ==============================================================
ST_IDLE = "idle"
ST_PROCESSING = "processing"
ST_WAIT_CLEAR = "wait_clear"


class SizeSortingApp:
    def __init__(self):
        self.plc = PLCClient()
        self.camera = HuarayCamera()
        self.classifier = ONNXClassifier()
        self.image_saver = ImageSaver()
        self.gate_settings = GateSettings(self.plc)
        self.stats = Stats()

        # Shot event handoff: poll thread -> slot thread
        self.shot1_events = [threading.Event() for _ in range(Config.NUM_SLOTS)]
        self.shot2_events = [threading.Event() for _ in range(Config.NUM_SLOTS)]

        self.processor = SlotProcessor(
            self.camera, self.classifier, self.plc,
            self.image_saver, self.stats,
            self.shot1_events, self.shot2_events,
        )
        self.running = False
        self._active_threads = {}   # slot_idx -> Thread

    # ------------------------------------------------------------------
    def initialize(self):
        logger.info("=" * 55)
        logger.info(
            "=== Size Sorting - 4-SLOT ENCODER SOFTWARE-TRIGGER (v3) ==="
        )
        logger.info(
            f"=== Slots={Config.NUM_SLOTS}"
            f" | Resolution={Config.CAMERA_WIDTH}x{Config.CAMERA_HEIGHT}"
            f" | Trigger={Config.CAMERA_TRIGGER_MODE}/"
            f"{Config.CAMERA_TRIGGER_SOURCE} ==="
        )
        logger.info(
            f"=== NUM_CAPTURES={Config.NUM_CAPTURES}"
            f" (vị trí shot do PLC encoder event M120-M127)"
            f" | SIZE_RATIO={Config.SIZE_THRESHOLD_RATIO} ==="
        )
        logger.info(
            f"=== DEVICE={Config.ONNX_DEVICE}"
            f" | IMGSZ={Config.ONNX_IMG_SIZE} ==="
        )
        logger.info(
            "=== ENCODER CONFIG: "
            + "  ".join(
                f"D{a}={v}({lbl})"
                for a, (v, lbl) in sorted(Config.ENCODER_CONFIG.items())
            )
            + " ==="
        )
        logger.info("=" * 55)
        if not self.classifier.load():
            return False
        if not self.camera.connect():
            return False
        if not self.plc.connect():
            return False

        # Ghi D222-D239 (encoder config, pulses 32-bit) ghi đè M8002,
        # rồi bật watchdog tự ghi lại nếu PLC restart.
        self.gate_settings.apply()
        self.gate_settings.start_watch()

        self.image_saver.start()
        logger.info("=== Initialization complete ===")
        return True

    def shutdown(self):
        self.running = False
        self.gate_settings.stop_watch()
        self.plc.disconnect()
        self.camera.disconnect()
        logger.info("=" * 55)
        logger.info(f"FINAL: {self.stats.summary()}")
        logger.info("=" * 55)

    # ------------------------------------------------------------------
    def _init_slot_states(self):
        """Leftover trigger lúc khởi động -> wait_clear để bỏ qua vật cũ."""
        init_regs = self.plc.read_bulk_registers()
        slot_state = []
        wait_since = [0.0] * Config.NUM_SLOTS
        last_objid = [None] * Config.NUM_SLOTS   # ObjID của vật đã xử lý

        for i in range(Config.NUM_SLOTS):
            trig0 = (
                init_regs.get(Config.TRIGGER_REGS[i], 0) if init_regs else 0
            ) or 0
            if trig0 == 1:
                slot_state.append(ST_WAIT_CLEAR)
                wait_since[i] = time.time()
                last_objid[i] = (
                    init_regs.get(Config.OBJID_REGS[i], 0) if init_regs else 0
                ) or 0
                logger.warning(
                    f"D{Config.TRIGGER_REGS[i]}={trig0} on startup"
                    f" (leftover, ObjID={last_objid[i]}) — bo qua den khi ve 0"
                )
            else:
                slot_state.append(ST_IDLE)
        return slot_state, wait_since, last_objid

    def _spawn(self, slot_idx, obj_id):
        # Dọn event tồn dư trước khi thread mới wait
        self.shot1_events[slot_idx].clear()
        self.shot2_events[slot_idx].clear()
        t = threading.Thread(
            target=self.processor.process,
            args=(slot_idx, obj_id),
            daemon=True,
            name=f"Slot{slot_idx}",
        )
        t.start()
        self._active_threads[slot_idx] = t
        logger.info(f"[Slot{slot_idx}] SPAWNED (ObjID={obj_id})")

    # ------------------------------------------------------------------
    def _poll_shot_events(self, active_slots):
        """Đọc block coil M120-M137 (1 transaction) -> set Event cho slot
        đang PROCESSING. Coil là LATCH trên PLC (giữ đến khi ACK) nên nếu
        bỏ sót 1 vòng poll, vòng sau vẫn thấy.
        """
        if not active_slots:
            return
        coils = self.plc.read_coils(
            Config.SHOT_COIL_READ_START, Config.SHOT_COIL_READ_COUNT
        )
        if not coils:
            return
        for i in active_slots:
            if coils.get(Config.SHOT1_EVENT_COILS[i]):
                self.shot1_events[i].set()
            if coils.get(Config.SHOT2_EVENT_COILS[i]):
                self.shot2_events[i].set()

    # ------------------------------------------------------------------
    def run(self):
        logger.info(
            f"4-SLOT ENCODER system running ({Config.NUM_SLOTS} slots,"
            f" level-trigger + shot events). Press Ctrl+C to stop."
        )
        self.running = True
        slot_state, wait_since, last_objid = self._init_slot_states()

        try:
            while self.running:
                regs = self.plc.read_bulk_registers()
                if not regs:
                    time.sleep(Config.POLLING_INTERVAL)
                    continue

                for i in range(Config.NUM_SLOTS):
                    trigger = regs.get(Config.TRIGGER_REGS[i], 0) or 0
                    obj_now = regs.get(Config.OBJID_REGS[i], 0) or 0
                    thread_alive = (
                        i in self._active_threads
                        and self._active_threads[i].is_alive()
                    )

                    if slot_state[i] == ST_IDLE:
                        if trigger == 1 and not thread_alive:
                            self._spawn(i, obj_now)
                            last_objid[i] = obj_now
                            slot_state[i] = ST_PROCESSING

                    elif slot_state[i] == ST_PROCESSING:
                        # Thread đã gửi ACK trước khi kết thúc. Khi nó chết
                        # -> chờ PLC clear trigger trước khi nhận vật mới.
                        if not thread_alive:
                            slot_state[i] = ST_WAIT_CLEAR
                            wait_since[i] = time.time()

                    elif slot_state[i] == ST_WAIT_CLEAR:
                        if trigger == 0:
                            slot_state[i] = ST_IDLE
                        elif obj_now != last_objid[i]:
                            # PLC đã nạp vật MỚI vào slot này trước khi ta kịp
                            # thấy D10x về 0 (2 xung sensor sát nhau). ObjID
                            # đổi -> vật khác, nhận ngay, không chờ cạnh lên.
                            logger.info(
                                f"[Slot{i}] vat moi (ObjID"
                                f" {last_objid[i]}->{obj_now})"
                                f" — bo qua cho D{Config.TRIGGER_REGS[i]}=0"
                            )
                            slot_state[i] = ST_IDLE
                        elif (time.time() - wait_since[i]
                              > Config.REACK_TIMEOUT):
                            # ACK có thể bị mất -> gửi lại, không để kẹt deadlock
                            logger.warning(
                                f"[Slot{i}] D{Config.TRIGGER_REGS[i]} ket 1"
                                f" >{Config.REACK_TIMEOUT}s (ObjID={obj_now})"
                                f" -> gui lai ACK M{Config.ACK_COILS[i]}"
                            )
                            self.plc.write_coil(Config.ACK_COILS[i], True)
                            wait_since[i] = time.time()

                # Shot events cho các slot đang xử lý
                active = [
                    i for i in range(Config.NUM_SLOTS)
                    if slot_state[i] == ST_PROCESSING
                ]
                self._poll_shot_events(active)

                # Cleanup dead thread refs
                for i in list(self._active_threads):
                    if not self._active_threads[i].is_alive():
                        del self._active_threads[i]

                time.sleep(Config.POLLING_INTERVAL)

        except KeyboardInterrupt:
            logger.info("Stopped by user")
        except Exception as e:
            logger.error(f"Runtime error: {e}", exc_info=True)
        finally:
            self.shutdown()
