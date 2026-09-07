# -- coding: utf-8 --
import sys
import os
import ctypes
import platform
from IMVDefines import *

# Load MVSDKmd.dll from absolute path (HuarayTech installation)
_DLL_DIR = r"C:\Program Files\HuarayTech\MV Viewer\Runtime\x64"
_APP_DLL_DIR = r"C:\Program Files\HuarayTech\MV Viewer\Application\x64"

if sys.platform == 'win32':
    if hasattr(os, 'add_dll_directory'):
        os.add_dll_directory(_DLL_DIR)
        os.add_dll_directory(_APP_DLL_DIR)

    # Đảm bảo Windows tìm DLL của Huaray trước các DLL khác
    os.environ["PATH"] = (
        _DLL_DIR + os.pathsep +
        _APP_DLL_DIR + os.pathsep +
        os.environ.get("PATH", "")
    )

    MVSDKdll = WinDLL(os.path.join(_DLL_DIR, "MVSDKmd.dll"))
else:
    MVSDKdll = CDLL("/usr/lib/libMVSDK.so")


class MvCamera():

    def __init__(self):
        self._handle = c_void_p()
        self.handle = pointer(self._handle)

    @staticmethod
    def IMV_GetVersion():
        MVSDKdll.IMV_GetVersion.restype = c_char_p
        return MVSDKdll.IMV_GetVersion()

    @staticmethod
    def IMV_EnumDevices(pDeviceList, interfaceType):
        MVSDKdll.IMV_EnumDevices.argtypes = [
            POINTER(IMV_DeviceList),
            c_uint
        ]
        MVSDKdll.IMV_EnumDevices.restype = c_int

        return MVSDKdll.IMV_EnumDevices(
            byref(pDeviceList),
            c_uint(interfaceType)
        )

    def IMV_CreateHandle(self, mode, pIdentifier):
        MVSDKdll.IMV_CreateHandle.argtypes = (c_void_p, c_int, c_void_p)
        MVSDKdll.IMV_CreateHandle.restype = c_int
        return MVSDKdll.IMV_CreateHandle(byref(self.handle), c_int(mode), pIdentifier)

    def IMV_DestroyHandle(self):
        MVSDKdll.IMV_DestroyHandle.argtypes = [c_void_p]
        MVSDKdll.IMV_DestroyHandle.restype = c_int
        return MVSDKdll.IMV_DestroyHandle(self.handle)

    def IMV_Open(self):
        MVSDKdll.IMV_Open.argtypes = [c_void_p]
        MVSDKdll.IMV_Open.restype = c_int
        return MVSDKdll.IMV_Open(self.handle)

    def IMV_Close(self):
        MVSDKdll.IMV_Close.argtypes = [c_void_p]
        MVSDKdll.IMV_Close.restype = c_int
        return MVSDKdll.IMV_Close(self.handle)

    def IMV_IsOpen(self):
        MVSDKdll.IMV_IsOpen.argtypes = [c_void_p]
        MVSDKdll.IMV_IsOpen.restype = c_bool
        return MVSDKdll.IMV_IsOpen(self.handle)

    def IMV_StartGrabbing(self):
        MVSDKdll.IMV_StartGrabbing.argtypes = [c_void_p]
        MVSDKdll.IMV_StartGrabbing.restype = c_int
        return MVSDKdll.IMV_StartGrabbing(self.handle)

    def IMV_StopGrabbing(self):
        MVSDKdll.IMV_StopGrabbing.argtypes = [c_void_p]
        MVSDKdll.IMV_StopGrabbing.restype = c_int
        return MVSDKdll.IMV_StopGrabbing(self.handle)

    def IMV_IsGrabbing(self):
        MVSDKdll.IMV_IsGrabbing.argtypes = [c_void_p]
        MVSDKdll.IMV_IsGrabbing.restype = c_bool
        return MVSDKdll.IMV_IsGrabbing(self.handle)

    def IMV_GetFrame(self, pFrame, timeoutMS):
        MVSDKdll.IMV_GetFrame.argtypes = (c_void_p, c_void_p, c_uint)
        MVSDKdll.IMV_GetFrame.restype = c_int
        return MVSDKdll.IMV_GetFrame(self.handle, byref(pFrame), c_uint(timeoutMS))

    def IMV_ReleaseFrame(self, pFrame):
        MVSDKdll.IMV_ReleaseFrame.argtypes = (c_void_p, c_void_p)
        MVSDKdll.IMV_ReleaseFrame.restype = c_int
        return MVSDKdll.IMV_ReleaseFrame(self.handle, byref(pFrame))

    def IMV_PixelConvert(self, pstPixelConvertParam):
        MVSDKdll.IMV_PixelConvert.argtypes = (c_void_p, c_void_p)
        MVSDKdll.IMV_PixelConvert.restype = c_int
        return MVSDKdll.IMV_PixelConvert(self.handle, byref(pstPixelConvertParam))

    def IMV_SetIntFeatureValue(self, pFeatureName, pIntValue):
        MVSDKdll.IMV_SetIntFeatureValue.argtypes = (c_void_p, c_void_p, c_int64)
        MVSDKdll.IMV_SetIntFeatureValue.restype = c_int
        return MVSDKdll.IMV_SetIntFeatureValue(self.handle, pFeatureName.encode('utf-8'), c_int64(pIntValue))

    def IMV_GetIntFeatureValue(self, pFeatureName, pIntValue):
        MVSDKdll.IMV_GetIntFeatureValue.argtypes = (c_void_p, c_void_p, c_void_p)
        MVSDKdll.IMV_GetIntFeatureValue.restype = c_int
        return MVSDKdll.IMV_GetIntFeatureValue(self.handle, pFeatureName.encode('utf-8'), byref(pIntValue))

    def IMV_SetDoubleFeatureValue(self, pFeatureName, doubleValue):
        MVSDKdll.IMV_SetDoubleFeatureValue.argtypes = (c_void_p, c_void_p, c_double)
        MVSDKdll.IMV_SetDoubleFeatureValue.restype = c_int
        return MVSDKdll.IMV_SetDoubleFeatureValue(self.handle, pFeatureName.encode('utf-8'), c_double(doubleValue))

    def IMV_GetDoubleFeatureValue(self, pFeatureName, pDoubleValue):
        MVSDKdll.IMV_GetDoubleFeatureValue.argtypes = (c_void_p, c_void_p, c_void_p)
        MVSDKdll.IMV_GetDoubleFeatureValue.restype = c_int
        return MVSDKdll.IMV_GetDoubleFeatureValue(self.handle, pFeatureName.encode('utf-8'), byref(pDoubleValue))

    def IMV_SetEnumFeatureSymbol(self, pFeatureName, pEnumSymbol):
        MVSDKdll.IMV_SetEnumFeatureSymbol.argtypes = (c_void_p, c_void_p, c_void_p)
        MVSDKdll.IMV_SetEnumFeatureSymbol.restype = c_int
        return MVSDKdll.IMV_SetEnumFeatureSymbol(self.handle, pFeatureName.encode('utf-8'), pEnumSymbol.encode('utf-8'))

    def IMV_GetEnumFeatureSymbol(self, pFeatureName, pEnumSymbol):
        MVSDKdll.IMV_GetEnumFeatureSymbol.argtypes = (c_void_p, c_void_p, c_void_p)
        MVSDKdll.IMV_GetEnumFeatureSymbol.restype = c_int
        return MVSDKdll.IMV_GetEnumFeatureSymbol(self.handle, pFeatureName.encode('utf-8'), byref(pEnumSymbol))

    def IMV_ExecuteCommandFeature(self, pFeatureName):
        MVSDKdll.IMV_ExecuteCommandFeature.argtypes = (c_void_p, c_void_p)
        MVSDKdll.IMV_ExecuteCommandFeature.restype = c_int
        return MVSDKdll.IMV_ExecuteCommandFeature(self.handle, pFeatureName.encode('utf-8'))

    def IMV_FeatureIsWriteable(self, pFeatureName):
        MVSDKdll.IMV_FeatureIsWriteable.argtypes = (c_void_p, c_void_p)
        MVSDKdll.IMV_FeatureIsWriteable.restype = c_bool
        return MVSDKdll.IMV_FeatureIsWriteable(self.handle, pFeatureName.encode('utf-8'))

    def IMV_SetBufferCount(self, nSize):
        MVSDKdll.IMV_SetBufferCount.argtypes = (c_void_p, c_uint)
        MVSDKdll.IMV_SetBufferCount.restype = c_int
        return MVSDKdll.IMV_SetBufferCount(self.handle, c_uint(nSize))

    def IMV_ClearFrameBuffer(self):
        MVSDKdll.IMV_ClearFrameBuffer.argtypes = [c_void_p]
        MVSDKdll.IMV_ClearFrameBuffer.restype = c_int
        return MVSDKdll.IMV_ClearFrameBuffer(self.handle)
