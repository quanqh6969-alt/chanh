"""
plc_client.py — Giao tiếp Modbus RTU với PLC FX3U, kèm heartbeat thread.

Tách riêng để test PLC không cần camera/AI:
    python plc_client.py       # đọc D101-D130, chạy heartbeat 5s
"""

import time
import threading

from pymodbus.client import ModbusSerialClient

from config import Config
from logger_setup import logger


class PLCClient:
    def __init__(self):
        self.client = None
        self._hb_counter = 0
        self._hb_thread = None
        self._running = False
        self._lock = threading.Lock()

    def _call_with_unit(self, func, **kwargs):
        """pymodbus đổi tên tham số slave id qua từng version
        (slave / unit / device_id) -> thử lần lượt."""
        for key in ("slave", "unit", "device_id"):
            try:
                return func(**kwargs, **{key: Config.MODBUS_SLAVE_ID})
            except TypeError:
                if key == "device_id":
                    raise
        raise RuntimeError("unreachable")

    def connect(self):
        try:
            try:
                self.client = ModbusSerialClient(
                    port=Config.MODBUS_PORT, framer="rtu",
                    baudrate=Config.MODBUS_BAUDRATE,
                    parity=Config.MODBUS_PARITY,
                    stopbits=Config.MODBUS_STOPBITS,
                    bytesize=Config.MODBUS_BYTESIZE,
                    timeout=Config.MODBUS_TIMEOUT,
                )
            except TypeError:
                self.client = ModbusSerialClient(
                    method="rtu", port=Config.MODBUS_PORT,
                    baudrate=Config.MODBUS_BAUDRATE,
                    parity=Config.MODBUS_PARITY,
                    stopbits=Config.MODBUS_STOPBITS,
                    bytesize=Config.MODBUS_BYTESIZE,
                    timeout=Config.MODBUS_TIMEOUT,
                )
            if not self.client.connect():
                logger.error(f"PLC connect failed on {Config.MODBUS_PORT}")
                return False
            logger.info(f"PLC connected: {Config.MODBUS_PORT}")
            self._running = True
            self._hb_thread = threading.Thread(
                target=self._heartbeat, daemon=True
            )
            self._hb_thread.start()
            return True
        except Exception as e:
            logger.error(f"PLC connect error: {e}")
            return False

    def disconnect(self):
        self._running = False
        if self._hb_thread:
            self._hb_thread.join(timeout=1.0)
        if self.client:
            self.client.close()
            logger.info("PLC disconnected")

    def _heartbeat(self):
        fail_count = 0
        while self._running:
            try:
                self._hb_counter = (self._hb_counter + 1) % 65536
                ok = self.write_register(
                    Config.REG_HEARTBEAT, self._hb_counter
                )
                if ok:
                    fail_count = 0
                else:
                    fail_count += 1
                    if fail_count <= 3 or fail_count % 20 == 0:
                        logger.warning(
                            f"Heartbeat FAILED ({fail_count}): "
                            f"D{Config.REG_HEARTBEAT}={self._hb_counter}"
                        )
                time.sleep(Config.HEARTBEAT_INTERVAL)
            except Exception as e:
                logger.error(f"Heartbeat exception: {e}")
                time.sleep(1.0)

    def read_bulk_registers(self):
        """Đọc 1 lần D101-D130 -> dict {addr: value}. Giảm số lần round-trip."""
        result = {}
        with self._lock:
            try:
                r = self._call_with_unit(
                    self.client.read_holding_registers,
                    address=Config.BULK_READ_START,
                    count=Config.BULK_READ_COUNT,
                )
                if hasattr(r, "isError") and r.isError():
                    return result
                if getattr(r, "registers", None):
                    for i, val in enumerate(r.registers):
                        result[Config.BULK_READ_START + i] = val
            except Exception:
                pass
        return result

    def read_register(self, addr):
        with self._lock:
            try:
                r = self._call_with_unit(
                    self.client.read_holding_registers,
                    address=addr, count=1,
                )
                if hasattr(r, "isError") and r.isError():
                    return None
                return (
                    r.registers[0]
                    if getattr(r, "registers", None)
                    else None
                )
            except Exception:
                return None

    def read_registers(self, start, count):
        """Đọc `count` register liên tiếp từ `start` -> dict {addr: value}.

        Dùng cho vùng ngoài BULK_READ (ví dụ D222-D225 gate settings).
        Trả về dict rỗng nếu lỗi.
        """
        result = {}
        with self._lock:
            try:
                r = self._call_with_unit(
                    self.client.read_holding_registers,
                    address=start, count=count,
                )
                if hasattr(r, "isError") and r.isError():
                    return result
                if getattr(r, "registers", None):
                    for i, val in enumerate(r.registers):
                        result[start + i] = val
            except Exception:
                pass
        return result

    def write_register(self, addr, value):
        with self._lock:
            try:
                r = self._call_with_unit(
                    self.client.write_register,
                    address=addr, value=int(value) & 0xFFFF,
                )
                return not (hasattr(r, "isError") and r.isError())
            except Exception:
                return False

    def write_registers(self, start, values):
        """Ghi nhiều register liên tiếp trong 1 request (FC16).

        Nhanh hơn ghi từng cái và đảm bảo PLC thấy cả nhóm cùng lúc.
        Fallback sang ghi từng register nếu PLC không hỗ trợ FC16.
        """
        vals = [int(v) & 0xFFFF for v in values]
        with self._lock:
            try:
                r = self._call_with_unit(
                    self.client.write_registers,
                    address=start, values=vals,
                )
                if not (hasattr(r, "isError") and r.isError()):
                    return True
            except Exception:
                pass
        # FC16 thất bại -> ghi lẻ từng register (write_register tự lock)
        return all(
            self.write_register(start + i, v) for i, v in enumerate(vals)
        )

    def write_coil(self, addr, value):
        with self._lock:
            try:
                r = self._call_with_unit(
                    self.client.write_coil,
                    address=addr, value=bool(value),
                )
                return not (hasattr(r, "isError") and r.isError())
            except Exception:
                return False

    def read_coils(self, start, count):
        """Đọc `count` coil liên tiếp từ `start` -> dict {addr: bool}.

        Dùng cho shot event M120-M137 (encoder software-trigger):
        đọc gộp 1 transaction thay vì từng bit.
        """
        result = {}
        with self._lock:
            try:
                r = self._call_with_unit(
                    self.client.read_coils,
                    address=start, count=count,
                )
                if hasattr(r, "isError") and r.isError():
                    return result
                bits = getattr(r, "bits", None)
                if bits:
                    for i in range(count):
                        result[start + i] = bool(bits[i])
            except Exception:
                pass
        return result


# ======================================================================
# TEST ĐỘC LẬP:  python plc_client.py
# ======================================================================
if __name__ == "__main__":
    plc = PLCClient()
    if not plc.connect():
        raise SystemExit(1)
    try:
        regs = plc.read_bulk_registers()
        if not regs:
            logger.error("Không đọc được register nào")
        else:
            print("\n  addr   value   ghi chú")
            note = {}
            for i, a in enumerate(Config.TRIGGER_REGS):
                note[a] = f"trigger slot{i}"
            for i, a in enumerate(Config.SIZE_REGS):
                note[a] = f"size slot{i}"
            for i, a in enumerate(Config.DECISION_REGS):
                note[a] = f"decision slot{i}"
            for i, a in enumerate(Config.OBJID_REGS):
                note[a] = f"objid slot{i}"
            note[Config.REG_HEARTBEAT] = "heartbeat"
            for a in sorted(regs):
                if regs[a] or a in note:
                    print(f"  D{a:<5} {regs[a]:<7} {note.get(a, '')}")
        print("\n  Heartbeat đang chạy, chờ 5s...")
        time.sleep(5)
        print(f"  heartbeat counter = {plc._hb_counter}")
    finally:
        plc.disconnect()
