#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ctypes import *


def enum(**enums):
    return type('Enum', (), enums)


IMV_GVSP_PIX_MONO = 0x01000000
IMV_GVSP_PIX_RGB = 0x02000000
IMV_GVSP_PIX_COLOR = 0x02000000
IMV_GVSP_PIX_CUSTOM = 0x80000000
IMV_GVSP_PIX_COLOR_MASK = 0xFF000000

IMV_GVSP_PIX_OCCUPY1BIT = 0x00010000
IMV_GVSP_PIX_OCCUPY2BIT = 0x00020000
IMV_GVSP_PIX_OCCUPY4BIT = 0x00040000
IMV_GVSP_PIX_OCCUPY8BIT = 0x00080000
IMV_GVSP_PIX_OCCUPY12BIT = 0x000C0000
IMV_GVSP_PIX_OCCUPY16BIT = 0x00100000
IMV_GVSP_PIX_OCCUPY24BIT = 0x00180000
IMV_GVSP_PIX_OCCUPY32BIT = 0x00200000
IMV_GVSP_PIX_OCCUPY36BIT = 0x00240000
IMV_GVSP_PIX_OCCUPY48BIT = 0x00300000
IMV_GVSP_PIX_EFFECTIVE_PIXEL_SIZE_MASK = 0x00FF0000
IMV_GVSP_PIX_EFFECTIVE_PIXEL_SIZE_SHIFT = 16

IMV_EPixelType = enum(
    gvspPixelTypeUndefined=-1,
    gvspPixelMono1p=(IMV_GVSP_PIX_MONO | IMV_GVSP_PIX_OCCUPY1BIT | 0x0037),
    gvspPixelMono2p=(IMV_GVSP_PIX_MONO | IMV_GVSP_PIX_OCCUPY2BIT | 0x0038),
    gvspPixelMono4p=(IMV_GVSP_PIX_MONO | IMV_GVSP_PIX_OCCUPY4BIT | 0x0039),
    gvspPixelMono8=(IMV_GVSP_PIX_MONO | IMV_GVSP_PIX_OCCUPY8BIT | 0x0001),
    gvspPixelMono8S=(IMV_GVSP_PIX_MONO | IMV_GVSP_PIX_OCCUPY8BIT | 0x0002),
    gvspPixelMono10=(IMV_GVSP_PIX_MONO | IMV_GVSP_PIX_OCCUPY16BIT | 0x0003),
    gvspPixelMono10Packed=(IMV_GVSP_PIX_MONO | IMV_GVSP_PIX_OCCUPY12BIT | 0x0004),
    gvspPixelMono12=(IMV_GVSP_PIX_MONO | IMV_GVSP_PIX_OCCUPY16BIT | 0x0005),
    gvspPixelMono12Packed=(IMV_GVSP_PIX_MONO | IMV_GVSP_PIX_OCCUPY12BIT | 0x0006),
    gvspPixelMono14=(IMV_GVSP_PIX_MONO | IMV_GVSP_PIX_OCCUPY16BIT | 0x0025),
    gvspPixelMono16=(IMV_GVSP_PIX_MONO | IMV_GVSP_PIX_OCCUPY16BIT | 0x0007),
    gvspPixelBayGR8=(IMV_GVSP_PIX_MONO | IMV_GVSP_PIX_OCCUPY8BIT | 0x0008),
    gvspPixelBayRG8=(IMV_GVSP_PIX_MONO | IMV_GVSP_PIX_OCCUPY8BIT | 0x0009),
    gvspPixelBayGB8=(IMV_GVSP_PIX_MONO | IMV_GVSP_PIX_OCCUPY8BIT | 0x000A),
    gvspPixelBayBG8=(IMV_GVSP_PIX_MONO | IMV_GVSP_PIX_OCCUPY8BIT | 0x000B),
    gvspPixelBayGR10=(IMV_GVSP_PIX_MONO | IMV_GVSP_PIX_OCCUPY16BIT | 0x000C),
    gvspPixelBayRG10=(IMV_GVSP_PIX_MONO | IMV_GVSP_PIX_OCCUPY16BIT | 0x000D),
    gvspPixelBayGB10=(IMV_GVSP_PIX_MONO | IMV_GVSP_PIX_OCCUPY16BIT | 0x000E),
    gvspPixelBayBG10=(IMV_GVSP_PIX_MONO | IMV_GVSP_PIX_OCCUPY16BIT | 0x000F),
    gvspPixelBayGR12=(IMV_GVSP_PIX_MONO | IMV_GVSP_PIX_OCCUPY16BIT | 0x0010),
    gvspPixelBayRG12=(IMV_GVSP_PIX_MONO | IMV_GVSP_PIX_OCCUPY16BIT | 0x0011),
    gvspPixelBayGB12=(IMV_GVSP_PIX_MONO | IMV_GVSP_PIX_OCCUPY16BIT | 0x0012),
    gvspPixelBayBG12=(IMV_GVSP_PIX_MONO | IMV_GVSP_PIX_OCCUPY16BIT | 0x0013),
    gvspPixelBayGR10Packed=(IMV_GVSP_PIX_MONO | IMV_GVSP_PIX_OCCUPY12BIT | 0x0026),
    gvspPixelBayRG10Packed=(IMV_GVSP_PIX_MONO | IMV_GVSP_PIX_OCCUPY12BIT | 0x0027),
    gvspPixelBayGB10Packed=(IMV_GVSP_PIX_MONO | IMV_GVSP_PIX_OCCUPY12BIT | 0x0028),
    gvspPixelBayBG10Packed=(IMV_GVSP_PIX_MONO | IMV_GVSP_PIX_OCCUPY12BIT | 0x0029),
    gvspPixelBayGR12Packed=(IMV_GVSP_PIX_MONO | IMV_GVSP_PIX_OCCUPY12BIT | 0x002A),
    gvspPixelBayRG12Packed=(IMV_GVSP_PIX_MONO | IMV_GVSP_PIX_OCCUPY12BIT | 0x002B),
    gvspPixelBayGB12Packed=(IMV_GVSP_PIX_MONO | IMV_GVSP_PIX_OCCUPY12BIT | 0x002C),
    gvspPixelBayBG12Packed=(IMV_GVSP_PIX_MONO | IMV_GVSP_PIX_OCCUPY12BIT | 0x002D),
    gvspPixelBayGR16=(IMV_GVSP_PIX_MONO | IMV_GVSP_PIX_OCCUPY16BIT | 0x002E),
    gvspPixelBayRG16=(IMV_GVSP_PIX_MONO | IMV_GVSP_PIX_OCCUPY16BIT | 0x002F),
    gvspPixelBayGB16=(IMV_GVSP_PIX_MONO | IMV_GVSP_PIX_OCCUPY16BIT | 0x0030),
    gvspPixelBayBG16=(IMV_GVSP_PIX_MONO | IMV_GVSP_PIX_OCCUPY16BIT | 0x0031),
    gvspPixelRGB8=(IMV_GVSP_PIX_COLOR | IMV_GVSP_PIX_OCCUPY24BIT | 0x0014),
    gvspPixelBGR8=(IMV_GVSP_PIX_COLOR | IMV_GVSP_PIX_OCCUPY24BIT | 0x0015),
    gvspPixelRGBA8=(IMV_GVSP_PIX_COLOR | IMV_GVSP_PIX_OCCUPY32BIT | 0x0016),
    gvspPixelBGRA8=(IMV_GVSP_PIX_COLOR | IMV_GVSP_PIX_OCCUPY32BIT | 0x0017),
    gvspPixelRGB10=(IMV_GVSP_PIX_COLOR | IMV_GVSP_PIX_OCCUPY48BIT | 0x0018),
    gvspPixelBGR10=(IMV_GVSP_PIX_COLOR | IMV_GVSP_PIX_OCCUPY48BIT | 0x0019),
    gvspPixelRGB12=(IMV_GVSP_PIX_COLOR | IMV_GVSP_PIX_OCCUPY48BIT | 0x001A),
    gvspPixelBGR12=(IMV_GVSP_PIX_COLOR | IMV_GVSP_PIX_OCCUPY48BIT | 0x001B),
    gvspPixelRGB16=(IMV_GVSP_PIX_COLOR | IMV_GVSP_PIX_OCCUPY48BIT | 0x0033),
    gvspPixelRGB10V1Packed=(IMV_GVSP_PIX_COLOR | IMV_GVSP_PIX_OCCUPY32BIT | 0x001C),
    gvspPixelRGB10P32=(IMV_GVSP_PIX_COLOR | IMV_GVSP_PIX_OCCUPY32BIT | 0x001D),
    gvspPixelRGB12V1Packed=(IMV_GVSP_PIX_COLOR | IMV_GVSP_PIX_OCCUPY36BIT | 0X0034),
    gvspPixelRGB565P=(IMV_GVSP_PIX_COLOR | IMV_GVSP_PIX_OCCUPY16BIT | 0x0035),
    gvspPixelBGR565P=(IMV_GVSP_PIX_COLOR | IMV_GVSP_PIX_OCCUPY16BIT | 0X0036),
    gvspPixelYUV411_8_UYYVYY=(IMV_GVSP_PIX_COLOR | IMV_GVSP_PIX_OCCUPY12BIT | 0x001E),
    gvspPixelYUV422_8_UYVY=(IMV_GVSP_PIX_COLOR | IMV_GVSP_PIX_OCCUPY16BIT | 0x001F),
    gvspPixelYUV422_8=(IMV_GVSP_PIX_COLOR | IMV_GVSP_PIX_OCCUPY16BIT | 0x0032),
    gvspPixelYUV8_UYV=(IMV_GVSP_PIX_COLOR | IMV_GVSP_PIX_OCCUPY24BIT | 0x0020),
    gvspPixelYCbCr8CbYCr=(IMV_GVSP_PIX_COLOR | IMV_GVSP_PIX_OCCUPY24BIT | 0x003A),
    gvspPixelYCbCr422_8=(IMV_GVSP_PIX_COLOR | IMV_GVSP_PIX_OCCUPY16BIT | 0x003B),
    gvspPixelYCbCr422_8_CbYCrY=(IMV_GVSP_PIX_COLOR | IMV_GVSP_PIX_OCCUPY16BIT | 0x0043),
    gvspPixelYCbCr411_8_CbYYCrYY=(IMV_GVSP_PIX_COLOR | IMV_GVSP_PIX_OCCUPY12BIT | 0x003C),
    gvspPixelYCbCr601_8_CbYCr=(IMV_GVSP_PIX_COLOR | IMV_GVSP_PIX_OCCUPY24BIT | 0x003D),
    gvspPixelYCbCr601_422_8=(IMV_GVSP_PIX_COLOR | IMV_GVSP_PIX_OCCUPY16BIT | 0x003E),
    gvspPixelYCbCr601_422_8_CbYCrY=(IMV_GVSP_PIX_COLOR | IMV_GVSP_PIX_OCCUPY16BIT | 0x0044),
    gvspPixelYCbCr601_411_8_CbYYCrYY=(IMV_GVSP_PIX_COLOR | IMV_GVSP_PIX_OCCUPY12BIT | 0x003F),
    gvspPixelYCbCr709_8_CbYCr=(IMV_GVSP_PIX_COLOR | IMV_GVSP_PIX_OCCUPY24BIT | 0x0040),
    gvspPixelYCbCr709_422_8=(IMV_GVSP_PIX_COLOR | IMV_GVSP_PIX_OCCUPY16BIT | 0x0041),
    gvspPixelYCbCr709_422_8_CbYCrY=(IMV_GVSP_PIX_COLOR | IMV_GVSP_PIX_OCCUPY16BIT | 0x0045),
    gvspPixelYCbCr709_411_8_CbYYCrYY=(IMV_GVSP_PIX_COLOR | IMV_GVSP_PIX_OCCUPY12BIT | 0x0042),
    gvspPixelRGB8Planar=(IMV_GVSP_PIX_COLOR | IMV_GVSP_PIX_OCCUPY24BIT | 0x0021),
    gvspPixelRGB10Planar=(IMV_GVSP_PIX_COLOR | IMV_GVSP_PIX_OCCUPY48BIT | 0x0022),
    gvspPixelRGB12Planar=(IMV_GVSP_PIX_COLOR | IMV_GVSP_PIX_OCCUPY48BIT | 0x0023),
    gvspPixelRGB16Planar=(IMV_GVSP_PIX_COLOR | IMV_GVSP_PIX_OCCUPY48BIT | 0x0024),
    gvspPixelBayRG10p=0x010A0058,
    gvspPixelBayRG12p=0x010c0059,
    gvspPixelMono1c=0x012000FF,
    gvspPixelMono1e=0x01080FFF
)

IMV_OK = 0
IMV_ERROR = -101
IMV_INVALID_HANDLE = -102
IMV_INVALID_PARAM = -103
IMV_INVALID_FRAME_HANDLE = -104
IMV_INVALID_FRAME = -105
IMV_INVALID_RESOURCE = -106
IMV_INVALID_IP = -107
IMV_NO_MEMORY = -108
IMV_INSUFFICIENT_MEMORY = -109
IMV_ERROR_PROPERTY_TYPE = -110
IMV_INVALID_ACCESS = -111
IMV_INVALID_RANGE = -112
IMV_NOT_SUPPORT = -113

typeGigeCamera = 0
typeU3vCamera = 1
typeCLCamera = 2
typePCIeCamera = 3
typeUndefinedCamera = 255

IMV_MAX_DEVICE_ENUM_NUM = 100
IMV_MAX_STRING_LENTH = 256
IMV_MAX_ERROR_LIST_NUM = 128
MAX_STRING_LENTH = 256

IMV_MSG_EVENT_ID_EXPOSURE_END = 0x9001
IMV_MSG_EVENT_ID_FRAME_TRIGGER = 0x9002
IMV_MSG_EVENT_ID_FRAME_START = 0x9003
IMV_MSG_EVENT_ID_ACQ_START = 0x9004
IMV_MSG_EVENT_ID_ACQ_TRIGGER = 0x9005
IMV_MSG_EVENT_ID_DATA_READ_OUT = 0x9006

IMV_EFeatureType = enum(
    featureInt=0x10000000, featureFloat=0x20000000, featureEnum=0x30000000,
    featureBool=0x40000000, featureString=0x50000000, featureCommand=0x60000000,
    featureGroup=0x70000000, featureReg=0x80000000, featureUndefined=0x90000000
)
IMV_EInterfaceType = enum(
    interfaceTypeGige=0x00000001, interfaceTypeUsb3=0x00000002,
    interfaceTypeCL=0x00000004, interfaceTypePCIe=0x00000008,
    interfaceTypeAll=0x00000000, interfaceInvalidType=0xFFFFFFFF
)
IMV_ECameraType = enum(
    typeGigeCamera=0, typeU3vCamera=1, typeCLCamera=2,
    typePCIeCamera=3, typeUndefinedCamera=255
)
IMV_ECreateHandleMode = enum(
    modeByIndex=0, modeByCameraKey=1, modeByDeviceUserID=2, modeByIPAddress=3
)
IMV_ECameraAccessPermission = enum(
    accessPermissionOpen=0, accessPermissionExclusive=1, accessPermissionControl=2,
    accessPermissionControlWithSwitchover=3, accessPermissionUnknown=254, accessPermissionUndefined=255
)
IMV_EGrabStrategy = enum(
    grabStrartegySequential=0, grabStrartegyLatestImage=1,
    grabStrartegyUpcomingImage=2, grabStrartegyUndefined=3
)
IMV_EBayerDemosaic = enum(
    demosaicNearestNeighbor=0, demosaicBilinear=1,
    demosaicEdgeSensing=2, demosaicNotSupport=255
)
IMV_EFlipType = enum(typeFlipVertical=0, typeFlipHorizontal=1)
IMV_ERotationAngle = enum(rotationAngle90=0, rotationAngle180=1, rotationAngle270=2)
IMV_ESaveType = enum(
    typeImageBmp=0, typeImageJpeg=1, typeImagePng=2,
    typeImageTif=3, typeImageUndefined=255
)

int8_t=c_int8; int16_t=c_int16; int32_t=c_int32; int64_t=c_int64
uint8_t=c_uint8; uint16_t=c_uint16; uint32_t=c_uint32; uint64_t=c_uint64
int_least8_t=c_byte; int_least16_t=c_short; int_least32_t=c_int; int_least64_t=c_long
uint_least8_t=c_ubyte; uint_least16_t=c_ushort; uint_least32_t=c_uint; uint_least64_t=c_ulong
int_fast8_t=c_byte; int_fast16_t=c_long; int_fast32_t=c_long; int_fast64_t=c_long
uint_fast8_t=c_ubyte; uint_fast16_t=c_ulong; uint_fast32_t=c_ulong; uint_fast64_t=c_ulong
intptr_t=c_long; uintptr_t=c_ulong; intmax_t=c_long; uintmax_t=c_ulong

class IMV_String(Structure):
    _fields_ = [('str', c_char * MAX_STRING_LENTH)]

class IMV_GigEDeviceInfo(Structure):
    _fields_ = [
        ('nIpConfigOptions', c_uint), ('nIpConfigCurrent', c_uint),
        ('nReserved', c_uint * 3), ('macAddress', c_char * MAX_STRING_LENTH),
        ('ipAddress', c_char * MAX_STRING_LENTH), ('subnetMask', c_char * MAX_STRING_LENTH),
        ('defaultGateWay', c_char * MAX_STRING_LENTH), ('protocolVersion', c_char * MAX_STRING_LENTH),
        ('ipConfiguration', c_char * MAX_STRING_LENTH), ('strReserved', c_char * MAX_STRING_LENTH * 6),
    ]

class IMV_UsbDeviceInfo(Structure):
    _fields_ = [
        ('bLowSpeedSupported', c_bool), ('bFullSpeedSupported', c_bool),
        ('bHighSpeedSupported', c_bool), ('bSuperSpeedSupported', c_bool),
        ('bDriverInstalled', c_bool), ('boolReserved', c_bool * 3),
        ('Reserved', c_uint * 4), ('configurationValid', c_char * MAX_STRING_LENTH),
        ('genCPVersion', c_char * MAX_STRING_LENTH), ('u3vVersion', c_char * MAX_STRING_LENTH),
        ('deviceGUID', c_char * MAX_STRING_LENTH), ('familyName', c_char * MAX_STRING_LENTH),
        ('u3vSerialNumber', c_char * MAX_STRING_LENTH), ('speed', c_char * MAX_STRING_LENTH),
        ('maxPower', c_char * MAX_STRING_LENTH), ('chReserved', c_char * MAX_STRING_LENTH * 4)
    ]

class DeviceSpecificInfo(Union):
    _fields_ = [('gigeDeviceInfo', IMV_GigEDeviceInfo), ('usbDeviceInfo', IMV_UsbDeviceInfo)]

class IMV_GigEInterfaceInfo(Structure):
    _fields_ = [
        ('description', c_char * MAX_STRING_LENTH), ('macAddress', c_char * MAX_STRING_LENTH),
        ('ipAddress', c_char * MAX_STRING_LENTH), ('subnetMask', c_char * MAX_STRING_LENTH),
        ('defaultGateWay', c_char * MAX_STRING_LENTH), ('chReserved', c_char * MAX_STRING_LENTH * 5),
    ]

class IMV_UsbInterfaceInfo(Structure):
    _fields_ = [
        ('description', c_char * MAX_STRING_LENTH), ('vendorID', c_char * MAX_STRING_LENTH),
        ('deviceID', c_char * MAX_STRING_LENTH), ('subsystemID', c_char * MAX_STRING_LENTH),
        ('revision', c_char * MAX_STRING_LENTH), ('speed', c_char * MAX_STRING_LENTH),
        ('chReserved', c_char * MAX_STRING_LENTH * 4),
    ]

class InterfaceInfo(Union):
    _fields_ = [('gigeInterfaceInfo', IMV_GigEInterfaceInfo), ('usbInterfaceInfo', IMV_UsbInterfaceInfo)]

class IMV_DeviceInfo(Structure):
    _fields_ = [
        ('nCameraType', c_int), ('nCameraReserved', c_int * 5),
        ('cameraKey', c_char * MAX_STRING_LENTH), ('cameraName', c_char * MAX_STRING_LENTH),
        ('serialNumber', c_char * MAX_STRING_LENTH), ('vendorName', c_char * MAX_STRING_LENTH),
        ('modelName', c_char * MAX_STRING_LENTH), ('manufactureInfo', c_char * MAX_STRING_LENTH),
        ('deviceVersion', c_char * MAX_STRING_LENTH), ('cameraReserved', c_char * MAX_STRING_LENTH * 5),
        ('DeviceSpecificInfo', DeviceSpecificInfo), ('nInterfaceType', c_int),
        ('nInterfaceReserved', c_int * 5), ('interfaceName', c_char * MAX_STRING_LENTH),
        ('interfaceReserved', c_char * MAX_STRING_LENTH * 5), ('InterfaceInfo', InterfaceInfo),
    ]

class IMV_DeviceList(Structure):
    _fields_ = [('nDevNum', c_uint), ('pDevInfo', POINTER(IMV_DeviceInfo))]

class IMV_FrameInfo(Structure):
    _fields_ = [
        ('blockId', c_uint64), ('status', c_uint), ('width', c_uint), ('height', c_uint),
        ('size', c_uint), ('pixelFormat', c_int), ('timeStamp', c_uint64),
        ('chunkCount', c_uint), ('paddingX', c_uint), ('paddingY', c_uint),
        ('recvFrameTime', c_uint), ('nReserved', c_uint * 19),
    ]

class IMV_Frame(Structure):
    _fields_ = [
        ('frameHandle', c_void_p), ('pData', POINTER(c_ubyte)),
        ('frameInfo', IMV_FrameInfo), ('nReserved', c_uint * 10),
    ]

class IMV_PixelConvertParam(Structure):
    _fields_ = [
        ('nWidth', c_uint), ('nHeight', c_uint), ('ePixelFormat', c_int),
        ('pSrcData', POINTER(c_ubyte)), ('nSrcDataLen', c_uint),
        ('nPaddingX', c_uint), ('nPaddingY', c_uint), ('eBayerDemosaic', c_int),
        ('eDstPixelFormat', c_int), ('pDstBuf', POINTER(c_ubyte)),
        ('nDstBufSize', c_uint), ('nDstDataLen', c_uint), ('nReserved', c_uint * 8)
    ]

class IMV_EnumEntryInfo(Structure):
    _fields_ = [('value', c_uint64), ('name', c_char * IMV_MAX_STRING_LENTH)]

class IMV_EnumEntryList(Structure):
    _fields_ = [('nEnumEntryBufferSize', c_uint), ('pEnumEntryInfo', POINTER(IMV_EnumEntryInfo))]

class IMV_ErrorList(Structure):
    _fields_ = [('nParamCnt', c_uint), ('paramNameList', IMV_String)]
