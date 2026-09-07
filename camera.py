"""
camera.py — Điều khiển camera Huaray (IMV SDK).

Hỗ trợ 2 chế độ theo Config.CAMERA_TRIGGER_MODE:
    "Off" — free-running (cũ): capture() lấy frame mới nhất trong stream.
    "On"  — software trigger (encoder mode): capture() gửi lệnh
            TriggerSoftware rồi chờ đúng frame do lệnh đó sinh ra.
            PLC quyết ĐỊNH THỜI ĐIỂM qua event encoder (M120-M127),
            Python chỉ thực thi — không còn sleep định vị.

Tách riêng để debug camera độc lập:
    python camera.py          # chụp 1 tấm, lưu ra test_capture.jpg
"""

import sys
import ctypes
import threading
from ctypes import byref, c_void_p, c_double, c_ubyte

import cv2
import numpy as np

from config import Config, BASE_DIR, PARENT_DIR
from logger_setup import logger

# IMVApi.py / IMVDefines.py được đặt NGAY TRONG folder này để repo chạy
# độc lập. Vẫn thêm PARENT_DIR làm fallback cho cây thư mục project cũ
# (Python\IMVApi.py) nếu ai đó xoá bản local.
for _p in (BASE_DIR, PARENT_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from IMVApi import *          # noqa: E402,F403


class HuarayCamera:
    def __init__(self):
        self.cam = None
        self.connected = False
        self._lock = threading.Lock()   # Camera chỉ 1, serialize capture

    def connect(self):
        try:
            deviceList = IMV_DeviceList()
            nRet = MvCamera.IMV_EnumDevices(
                deviceList, IMV_EInterfaceType.interfaceTypeAll
            )
            if nRet != IMV_OK:
                logger.error(f"Enumerate devices failed, code={nRet}")
                return False
            if deviceList.nDevNum == 0:
                logger.error("No camera found.")
                return False

            logger.info(f"Found {deviceList.nDevNum} camera(s):")
            for i in range(deviceList.nDevNum):
                info = deviceList.pDevInfo[i]
                vendor = info.vendorName.decode("utf-8", errors="ignore")
                model = info.modelName.decode("utf-8", errors="ignore")
                sn = info.serialNumber.decode("utf-8", errors="ignore")
                logger.info(f"  [{i}] {vendor} / {model} / S/N:{sn}")

            self.cam = MvCamera()
            nRet = self.cam.IMV_CreateHandle(
                IMV_ECreateHandleMode.modeByIndex,
                byref(c_void_p(Config.CAMERA_INDEX)),
            )
            if nRet != IMV_OK:
                logger.error(f"CreateHandle failed, code={nRet}")
                return False

            nRet = self.cam.IMV_Open()
            if nRet != IMV_OK:
                logger.error(f"Open camera failed, code={nRet}")
                return False

            self._configure()

            nRet = self.cam.IMV_StartGrabbing()
            if nRet != IMV_OK:
                logger.error(f"StartGrabbing failed, code={nRet}")
                return False

            self.connected = True
            mode = (
                "software-trigger"
                if Config.CAMERA_TRIGGER_MODE == "On"
                else "free-running"
            )
            logger.info(f"Camera connected ({mode})")
            return True
        except Exception as e:
            logger.error(f"Camera connect error: {e}", exc_info=True)
            return False

    def _configure(self):
        try:
            trig_mode = Config.CAMERA_TRIGGER_MODE
            nRet = self.cam.IMV_SetEnumFeatureSymbol("TriggerMode", trig_mode)
            if nRet != IMV_OK:
                logger.warning(f"Set TriggerMode={trig_mode} failed code={nRet}")
            else:
                logger.info(f"TriggerMode={trig_mode}")

            if trig_mode == "On":
                nRet = self.cam.IMV_SetEnumFeatureSymbol(
                    "TriggerSource", Config.CAMERA_TRIGGER_SOURCE
                )
                if nRet != IMV_OK:
                    logger.error(
                        f"Set TriggerSource="
                        f"{Config.CAMERA_TRIGGER_SOURCE} failed code={nRet}"
                    )
                else:
                    logger.info(
                        f"TriggerSource={Config.CAMERA_TRIGGER_SOURCE}"
                    )

            nRet = self.cam.IMV_SetDoubleFeatureValue(
                "ExposureTime", Config.CAMERA_EXPOSURE_US
            )
            logger.info(
                f"Exposure: {Config.CAMERA_EXPOSURE_US} us"
                if nRet == IMV_OK
                else f"Set ExposureTime failed code={nRet}"
            )

            nRet = self.cam.IMV_SetDoubleFeatureValue(
                "Gain", Config.CAMERA_GAIN_DB
            )
            logger.info(
                f"Gain: {Config.CAMERA_GAIN_DB} dB"
                if nRet == IMV_OK
                else f"Set Gain failed code={nRet}"
            )

            self.cam.IMV_SetIntFeatureValue("Width", Config.CAMERA_WIDTH)
            self.cam.IMV_SetIntFeatureValue("Height", Config.CAMERA_HEIGHT)

            awb = Config.CAMERA_AUTO_WHITE_BALANCE
            nRet = self.cam.IMV_SetEnumFeatureSymbol("BalanceWhiteAuto", awb)
            if nRet == IMV_OK:
                logger.info(f"BalanceWhiteAuto: {awb}")
            else:
                logger.warning(f"BalanceWhiteAuto not supported (code={nRet})")

            exp = c_double(0)
            gain = c_double(0)
            self.cam.IMV_GetDoubleFeatureValue("ExposureTime", exp)
            self.cam.IMV_GetDoubleFeatureValue("Gain", gain)
            logger.info(
                f"Actual: exposure={exp.value:.0f}us  gain={gain.value:.2f}dB"
            )

            # Xóa frame cũ còn sót trong buffer (an toàn khi chuyển mode).
            # Trong trigger mode, sau lệnh này camera chỉ sinh frame khi
            # nhận TriggerSoftware -> GetFrame luôn lấy đúng frame mới.
            if Config.CAMERA_TRIGGER_MODE == "On":
                self.cam.IMV_ClearFrameBuffer()
                logger.info("Frame buffer cleared (trigger mode)")
        except Exception as e:
            logger.warning(f"Camera configure: {e}")

    def capture(self):
        """Capture 1 frame. Thread-safe qua camera lock.

        Software-trigger mode (encoder): gửi IMV_ExecuteCommandFeature
        ("TriggerSoftware") rồi IMV_GetFrame chờ đúng frame do trigger đó
        sinh ra. Camera phải đang StartGrabbing sẵn từ connect() — KHÔNG
        open/start mỗi lần chụp.

        Free-running mode (cũ): lấy frame mới nhất trong stream.

        Vị trí chụp do PLC quyết định qua event encoder (M120-M127);
        hàm này không sleep, không định vị."""
        if not self.connected or self.cam is None:
            return None
        with self._lock:
            try:
                if Config.CAMERA_TRIGGER_MODE == "On":
                    nRet = self.cam.IMV_ExecuteCommandFeature("TriggerSoftware")
                    if nRet != IMV_OK:
                        logger.error(f"TriggerSoftware failed, code={nRet}")
                        return None

                frame = IMV_Frame()
                timeout = (
                    Config.CAPTURE_TIMEOUT_MS
                    if Config.CAMERA_TRIGGER_MODE == "On"
                    else 5000
                )
                nRet = self.cam.IMV_GetFrame(frame, timeout)
                if nRet != IMV_OK:
                    logger.error(f"GetFrame failed, code={nRet}")
                    return None

                width = frame.frameInfo.width
                height = frame.frameInfo.height
                pixfmt = frame.frameInfo.pixelFormat
                size = frame.frameInfo.size

                isMono = (pixfmt == IMV_EPixelType.gvspPixelMono8)
                nDstSize = width * height if isMono else width * height * 3
                pDstBuf = (c_ubyte * nDstSize)()

                stConvert = IMV_PixelConvertParam()
                ctypes.memset(byref(stConvert), 0, ctypes.sizeof(stConvert))
                stConvert.nWidth = width
                stConvert.nHeight = height
                stConvert.ePixelFormat = pixfmt
                stConvert.pSrcData = frame.pData
                stConvert.nSrcDataLen = size
                stConvert.nPaddingX = frame.frameInfo.paddingX
                stConvert.nPaddingY = frame.frameInfo.paddingY
                stConvert.eBayerDemosaic = (
                    IMV_EBayerDemosaic.demosaicNearestNeighbor
                )
                stConvert.eDstPixelFormat = (
                    IMV_EPixelType.gvspPixelMono8
                    if isMono
                    else IMV_EPixelType.gvspPixelBGR8
                )
                stConvert.pDstBuf = pDstBuf
                stConvert.nDstBufSize = nDstSize

                nRet = self.cam.IMV_PixelConvert(stConvert)
                self.cam.IMV_ReleaseFrame(frame)

                if nRet != IMV_OK:
                    logger.error(f"PixelConvert failed, code={nRet}")
                    return None

                if isMono:
                    arr = np.frombuffer(
                        bytearray(pDstBuf), dtype=np.uint8
                    ).reshape(height, width)
                    return cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
                else:
                    arr = np.frombuffer(
                        bytearray(pDstBuf), dtype=np.uint8
                    ).reshape(height, width, 3)
                    return arr.copy()
            except Exception as e:
                logger.error(f"Capture error: {e}", exc_info=True)
                return None

    def disconnect(self):
        if self.cam:
            try:
                self.cam.IMV_StopGrabbing()
                self.cam.IMV_Close()
                self.cam.IMV_DestroyHandle()
                logger.info("Camera disconnected")
            except Exception:
                pass
        self.connected = False


# ======================================================================
# TEST ĐỘC LẬP:  python camera.py
# ======================================================================
if __name__ == "__main__":
    cam = HuarayCamera()
    if not cam.connect():
        logger.error("Không kết nối được camera")
        sys.exit(1)
    try:
        img = cam.capture()
        if img is None:
            logger.error("Capture thất bại")
        else:
            out = Config.IMAGE_SAVE_DIR / "test_capture.jpg"
            Config.IMAGE_SAVE_DIR.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(out), img)
            logger.info(f"OK: shape={img.shape} -> {out}")
    finally:
        cam.disconnect()
