"""
gate_settings.py — Ghi và giám sát ENCODER CONFIG D222-D239 từ Python.

Ladder encoder (Ladder_4Slot_Encoder_*_SoftTrig.md) dùng các cặp thanh ghi
32-bit (2 D liên tiếp, little-endian: D[n]=low word, D[n+1]=high word):

    D222:D223  GATE_S_OFFSET      D230:D231  SHOT1_OFFSET
    D224:D225  GATE_S_WIDTH       D232:D233  SHOT2_OFFSET
    D226:D227  GATE_L_OFFSET      D234:D235  AI_DEADLINE
    D228:D229  GATE_L_WIDTH       D236:D237  SHOT_ACK_TIMEOUT
                                  D238:D239  RELEASE

Đơn vị: PULSES encoder (không còn là 100ms timer như bản cũ).

VẤN ĐỀ (như bản cũ): rung M8002 của ladder xóa/ghi đè vùng này mỗi lần PLC
STOP->RUN. Module này ghi giá trị mong muốn sau khi connect, và chạy watchdog
đọc lại định kỳ -> phát hiện lệch (PLC restart / sửa tay bằng GX) -> ghi lại.

Test độc lập:
    python gate_settings.py             # đọc giá trị hiện tại
    python gate_settings.py --write     # ghi theo config rồi đọc lại
"""

import time
import threading

from config import Config
from logger_setup import logger


def _split32(value):
    """int 32-bit -> (low_word, high_word) cho cặp D[n], D[n+1]."""
    v = int(value) & 0xFFFFFFFF
    return v & 0xFFFF, (v >> 16) & 0xFFFF


def _join32(low, high):
    """(low_word, high_word) -> int 32-bit (có dấu, khớp DSUB/LD>= FX3U)."""
    v = (int(high) << 16) | int(low)
    return v - 0x100000000 if v >= 0x80000000 else v


def _fmt(addr, value, label):
    return f"D{addr}:D{addr+1}={value} pulses ({label})"


class GateSettings:
    """Tên class giữ nguyên để app.py không đổi; nội dung là encoder config."""

    def __init__(self, plc):
        self.plc = plc
        # {start_addr: (value32, label)}
        self.desired = dict(Config.ENCODER_CONFIG)
        self._thread = None
        self._running = False
        self._addrs = sorted(self.desired)
        self._start = self._addrs[0]                     # 222
        self._end = self._addrs[-1] + 1                  # 239 (high word cuối)

    # ------------------------------------------------------------------
    def read_current(self):
        """Đọc D222-D239 -> dict {start_addr: value32}."""
        regs = self.plc.read_registers(self._start, self._end - self._start + 1)
        if not regs:
            return {}
        result = {}
        for a in self._addrs:
            if a in regs and (a + 1) in regs:
                result[a] = _join32(regs[a], regs[a + 1])
        return result

    def write_all(self):
        """Ghi toàn bộ config (1 request FC16, D222-D239 liền mạch)."""
        values = []
        for a in range(self._start, self._end + 1):
            owner = None
            for base in self._addrs:
                if a in (base, base + 1):
                    owner = base
                    break
            if owner is None:
                values.append(0)          # khe hở giữa các cặp (không có)
            else:
                low, high = _split32(self.desired[owner][0])
                values.append(low if a == owner else high)

        ok = self.plc.write_registers(self._start, values)
        if ok:
            logger.info(
                "Encoder config -> PLC: "
                + "  ".join(
                    _fmt(a, v, lbl)
                    for a, (v, lbl) in sorted(self.desired.items())
                )
            )
        else:
            logger.error(
                f"Ghi encoder config THAT BAI (D{self._start}-D{self._end})"
            )
        return ok

    def verify(self):
        """So sánh PLC với giá trị mong muốn -> list addr bị lệch."""
        current = self.read_current()
        if not current:
            return None      # không đọc được, chưa kết luận
        return [
            a for a in self._addrs
            if current.get(a) != self.desired[a][0]
        ]

    def apply(self):
        """Ghi rồi đọc lại xác nhận. Trả về True nếu PLC đã đúng."""
        if not Config.WRITE_GATE_SETTINGS:
            logger.info("WRITE_GATE_SETTINGS=False -> giữ giá trị ladder")
            return True

        before = self.read_current()
        if before:
            logger.info(
                "Encoder config PLC hiện tại: "
                + "  ".join(
                    _fmt(a, before[a], self.desired.get(a, (0, "?"))[1])
                    for a in sorted(before)
                )
            )

        self.write_all()
        time.sleep(0.1)          # cho PLC kịp 1 scan

        bad = self.verify()
        if bad is None:
            logger.warning("Không đọc lại được encoder config để xác nhận")
            return False
        if bad:
            cur = self.read_current()
            for a in bad:
                logger.error(
                    f"D{a}:D{a+1} ghi không thành công: "
                    f"muốn {self.desired[a][0]}, PLC đang {cur.get(a)}"
                )
            return False

        self._check_ordering()
        logger.info("Encoder config đã xác nhận đúng trên PLC")
        return True

    def _check_ordering(self):
        """Sanity check thứ tự vị trí — sai thứ tự là gate/shot chạy loạn."""
        d = {lbl: v for v, lbl in self.desired.values()}
        checks = [
            ("SHOT1_OFFSET", "SHOT2_OFFSET"),
            ("SHOT2_OFFSET", "SHOT_ACK_TIMEOUT"),
            ("SHOT_ACK_TIMEOUT", "AI_DEADLINE"),
            ("AI_DEADLINE", "GATE_S_OFFSET"),
            ("AI_DEADLINE", "GATE_L_OFFSET"),
            ("GATE_S_OFFSET", "RELEASE"),
            ("GATE_L_OFFSET", "RELEASE"),
        ]
        for lo, hi in checks:
            if lo in d and hi in d and d[lo] >= d[hi]:
                logger.error(
                    f"ENCODER CONFIG SAI THỨ TỰ: {lo}={d[lo]} >= {hi}={d[hi]}"
                    " — sửa Config.ENCODER_CONFIG trước khi chạy!"
                )
        if "RELEASE" in d and "GATE_S_OFFSET" in d and "GATE_S_WIDTH" in d:
            if d["RELEASE"] <= d["GATE_S_OFFSET"] + d["GATE_S_WIDTH"]:
                logger.error("RELEASE phải > GATE_S_END")
        if "RELEASE" in d and "GATE_L_OFFSET" in d and "GATE_L_WIDTH" in d:
            if d["RELEASE"] <= d["GATE_L_OFFSET"] + d["GATE_L_WIDTH"]:
                logger.error("RELEASE phải > GATE_L_END")

    # ------------------------------------------------------------------
    def start_watch(self):
        """Thread giám sát: PLC restart -> M8002 reset -> ghi lại."""
        if not (Config.WRITE_GATE_SETTINGS and Config.GATE_SETTINGS_WATCH):
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._watch_loop, daemon=True, name="GateWatch"
        )
        self._thread.start()
        logger.info(
            f"Encoder config watchdog ON "
            f"(mỗi {Config.GATE_SETTINGS_CHECK_INTERVAL}s)"
        )

    def stop_watch(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)

    def _watch_loop(self):
        fail_streak = 0
        while self._running:
            time.sleep(Config.GATE_SETTINGS_CHECK_INTERVAL)
            if not self._running:
                break
            try:
                bad = self.verify()
                if bad is None:
                    fail_streak += 1
                    if fail_streak in (1, 10) or fail_streak % 50 == 0:
                        logger.warning(
                            f"Encoder watchdog: không đọc được"
                            f" D{self._start}-D{self._end} ({fail_streak} lần)"
                        )
                    continue
                fail_streak = 0
                if bad:
                    cur = self.read_current()
                    logger.warning(
                        "Encoder config bị đổi (PLC restart / sửa tay?): "
                        + "  ".join(
                            f"D{a}: {cur.get(a)} -> {self.desired[a][0]}"
                            for a in bad
                        )
                    )
                    self.write_all()
            except Exception as e:
                logger.error(f"Encoder watchdog error: {e}")


# ======================================================================
# TEST ĐỘC LẬP:  python gate_settings.py [--write]
# ======================================================================
if __name__ == "__main__":
    import sys
    from plc_client import PLCClient

    do_write = "--write" in sys.argv

    plc = PLCClient()
    if not plc.connect():
        raise SystemExit(1)
    try:
        gs = GateSettings(plc)

        cur = gs.read_current()
        if not cur:
            logger.error(f"Không đọc được D{gs._start}-D{gs._end}")
        else:
            print("\n  === PLC đang giữ ===")
            for a in sorted(cur):
                lbl = gs.desired.get(a, (0, "?"))[1]
                print(f"    {_fmt(a, cur[a], lbl)}")

        print("\n  === config.py mong muốn ===")
        for a in sorted(gs.desired):
            v, lbl = gs.desired[a]
            print(f"    {_fmt(a, v, lbl)}")

        if do_write:
            print()
            gs.apply()
            after = gs.read_current()
            print("\n  === Sau khi ghi ===")
            for a in sorted(after):
                mark = "OK" if after[a] == gs.desired[a][0] else "LECH"
                lbl = gs.desired[a][1]
                print(f"    {_fmt(a, after[a], lbl)}  [{mark}]")
        else:
            bad = gs.verify()
            if bad:
                print(f"\n  Lệch ở: {['D%d' % a for a in bad]}")
                print("  Chạy lại với --write để ghi xuống PLC")
            elif bad is not None:
                print("\n  PLC đã khớp config, không cần ghi")
    finally:
        plc.disconnect()
