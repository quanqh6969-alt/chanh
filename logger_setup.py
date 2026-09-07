"""
logger_setup.py — Khởi tạo logging dùng chung cho mọi module.

Mọi module khác chỉ cần:
    from logger_setup import logger
Không tự gọi logging.basicConfig ở nơi khác để tránh cấu hình 2 lần.
"""

import sys
import logging

from config import Config


def _force_utf8_stdout():
    """Console Windows mặc định cp1252/cp437 -> log có dấu tiếng Việt sẽ
    raise UnicodeEncodeError bên trong logging (mất dòng log). Ép stdout
    sang UTF-8, nếu không được thì thay ký tự lỗi thay vì chết."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def setup_logger(name: str = "size_sorting") -> logging.Logger:
    """Tạo logger ghi đồng thời ra file và stdout. Gọi lại nhiều lần an toàn."""
    log = logging.getLogger(name)

    # Đã cấu hình rồi thì trả về luôn, tránh nhân đôi handler
    # (nhân đôi handler = mỗi dòng log in ra 2 lần).
    if log.handlers:
        return log

    _force_utf8_stdout()

    log.setLevel(logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    )

    Config.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    fh = logging.FileHandler(Config.LOG_FILE, encoding="utf-8")
    fh.setFormatter(fmt)
    log.addHandler(fh)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    log.addHandler(sh)

    # Không đẩy lên root logger để khỏi bị in trùng
    log.propagate = False
    return log


logger = setup_logger()
