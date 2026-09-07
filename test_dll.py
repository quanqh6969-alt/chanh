import os
import ctypes

d = r"C:\Program Files\HuarayTech\MV Viewer\Runtime\x64"
os.add_dll_directory(d)

dlls = [
    "GenApi_MD_VC120_v3_0.dll",
    "GCBase_MD_VC120_v3_0.dll",
    "GenCP_MD_VC120_v3_0.dll",
    "NodeMapData_MD_VC120_v3_0.dll",
    "XmlParser_MD_VC120_v3_0.dll",
    "TinyXmlmd.dll",
    "MVlog4cppmd.dll",
    "ImageConvert.dll",
    "ImageSave.dll",
    "iImageProcessing64.dll",
    "VideoRender.dll",
]

for name in dlls:
    path = os.path.join(d, name)

    try:
        ctypes.WinDLL(path)
        print(f"[OK]   {name}")
    except Exception as e:
        print(f"[FAIL] {name}")
        print(f"       {e}")