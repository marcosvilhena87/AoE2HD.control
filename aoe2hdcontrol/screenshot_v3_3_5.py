"""v3.3.5 Windows-only client-area screenshot evidence (read-only).

GDI BitBlt may not capture exclusive fullscreen/DirectX content: black or stale
frames are possible; such files are evidence candidates, never validated images.
"""
from __future__ import annotations
import ctypes
import os
import struct
from ctypes import wintypes
from pathlib import Path

class RECT(ctypes.Structure):
    _fields_=[("left",ctypes.c_long),("top",ctypes.c_long),("right",ctypes.c_long),("bottom",ctypes.c_long)]
class BMIHEADER(ctypes.Structure):
    _fields_=[("size",wintypes.DWORD),("width",ctypes.c_long),("height",ctypes.c_long),
              ("planes",wintypes.WORD),("bitcount",wintypes.WORD),("compression",wintypes.DWORD),
              ("image_size",wintypes.DWORD),("xppm",ctypes.c_long),("yppm",ctypes.c_long),
              ("clr_used",wintypes.DWORD),("clr_important",wintypes.DWORD)]
class BMI(ctypes.Structure):
    _fields_=[("header",BMIHEADER),("colors",wintypes.DWORD*3)]

def screenshot_client(pid, destination):
    if os.name != "nt":
        raise OSError("Windows required for screenshot")
    u=ctypes.WinDLL("user32",use_last_error=True)
    g=ctypes.WinDLL("gdi32",use_last_error=True)
    u.GetForegroundWindow.restype=wintypes.HWND
    u.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
    u.GetWindowThreadProcessId.restype=wintypes.DWORD
    u.GetClientRect.argtypes=[wintypes.HWND,ctypes.POINTER(RECT)]
    u.GetClientRect.restype=wintypes.BOOL
    u.GetDC.argtypes=[wintypes.HWND];u.GetDC.restype=wintypes.HDC
    u.ReleaseDC.argtypes=[wintypes.HWND,wintypes.HDC]
    g.CreateCompatibleDC.argtypes=[wintypes.HDC];g.CreateCompatibleDC.restype=wintypes.HDC
    g.CreateCompatibleBitmap.argtypes=[wintypes.HDC,ctypes.c_int,ctypes.c_int];g.CreateCompatibleBitmap.restype=wintypes.HBITMAP
    g.SelectObject.argtypes=[wintypes.HDC,wintypes.HGDIOBJ];g.SelectObject.restype=wintypes.HGDIOBJ
    g.BitBlt.argtypes=[wintypes.HDC,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,wintypes.HDC,ctypes.c_int,ctypes.c_int,wintypes.DWORD]
    g.BitBlt.restype=wintypes.BOOL
    g.GetDIBits.argtypes=[wintypes.HDC,wintypes.HBITMAP,wintypes.UINT,wintypes.UINT,ctypes.c_void_p,ctypes.POINTER(BMI),wintypes.UINT]
    g.GetDIBits.restype=ctypes.c_int
    g.DeleteObject.argtypes=[wintypes.HGDIOBJ];g.DeleteDC.argtypes=[wintypes.HDC]
    hwnd=u.GetForegroundWindow();owner=wintypes.DWORD()
    if not hwnd or not u.GetWindowThreadProcessId(hwnd,ctypes.byref(owner)) or owner.value!=pid:
        raise ValueError("game is not foreground")
    rect=RECT()
    if not u.GetClientRect(hwnd,ctypes.byref(rect)):raise OSError("GetClientRect failed")
    w,h=rect.right-rect.left,rect.bottom-rect.top
    if not 1<=w<=8192 or not 1<=h<=8192:raise ValueError("invalid client size")
    source=u.GetDC(hwnd)
    if not source:raise OSError("GetDC failed")
    mem=None;bmp=None;old=None
    try:
        mem=g.CreateCompatibleDC(source)
        if not mem:raise OSError("CreateCompatibleDC failed")
        bmp=g.CreateCompatibleBitmap(source,w,h)
        if not bmp:raise OSError("CreateCompatibleBitmap failed")
        old=g.SelectObject(mem,bmp)
        if not old:raise OSError("SelectObject failed")
        if not g.BitBlt(mem,0,0,w,h,source,0,0,0x00CC0020):
            raise OSError("BitBlt failed")
        stride=((w*24+31)//32)*4
        data=ctypes.create_string_buffer(stride*h)
        info=BMI()
        info.header.size=ctypes.sizeof(BMIHEADER)
        info.header.width=w;info.header.height=h
        info.header.planes=1;info.header.bitcount=24
        # GetDIBits requires the bitmap to be deselected from its DC.
        g.SelectObject(mem,old)
        old=None
        if g.GetDIBits(source,bmp,0,h,data,ctypes.byref(info),0)!=h:
            raise OSError("GetDIBits failed")
        payload=bytes(data)
        offset=14+40
        header=b"BM"+struct.pack("<IHHI",offset+len(payload),0,0,offset)
        dib=struct.pack("<IiiHHIIiiII",40,w,h,1,24,0,len(payload),0,0,0,0)
        Path(destination).write_bytes(header+dib+payload)
        return {"path":str(destination),"width":w,"height":h,"format":"bmp",
                "method":"gdi_bitblt","content_validated":False,
                "note":"GDI frame may be black/stale in DirectX fullscreen; inspect manually."}
    finally:
        if old:g.SelectObject(mem,old)
        if bmp:g.DeleteObject(bmp)
        if mem:g.DeleteDC(mem)
        u.ReleaseDC(hwnd,source)
