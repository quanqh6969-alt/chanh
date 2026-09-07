import sys
import os

# Cho phép chạy `python main.py` từ bất kỳ thư mục nào
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logger_setup import logger    # noqa: E402
from app import SizeSortingApp     # noqa: E402


def main():
    app = SizeSortingApp()
    if not app.initialize():
        logger.error("Initialization failed.")
        return 1
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
