# =========================================================================
# Copyright (c) 2026 NDKBVH. All rights reserved.
# Module: Full-Screen Desktop Capture & Browser Window Focus (Windows)
# =========================================================================

import ctypes
import ctypes.wintypes
import sys
import time
import uuid
from typing import Callable, Optional, Tuple

from PIL import Image, ImageGrab

_DPI_INITIALIZED = False


def enable_dpi_awareness() -> None:
    """Enable per-monitor DPI awareness on Windows so captures match physical pixels."""
    global _DPI_INITIALIZED
    if _DPI_INITIALIZED or sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    _DPI_INITIALIZED = True


class _MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.wintypes.DWORD),
        ("rcMonitor", ctypes.wintypes.RECT),
        ("rcWork", ctypes.wintypes.RECT),
        ("dwFlags", ctypes.wintypes.DWORD),
    ]


class _BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", ctypes.wintypes.DWORD),
        ("biWidth", ctypes.wintypes.LONG),
        ("biHeight", ctypes.wintypes.LONG),
        ("biPlanes", ctypes.wintypes.WORD),
        ("biBitCount", ctypes.wintypes.WORD),
        ("biCompression", ctypes.wintypes.DWORD),
        ("biSizeImage", ctypes.wintypes.DWORD),
        ("biXPelsPerMeter", ctypes.wintypes.LONG),
        ("biYPelsPerMeter", ctypes.wintypes.LONG),
        ("biClrUsed", ctypes.wintypes.DWORD),
        ("biClrImportant", ctypes.wintypes.DWORD),
    ]


def _rect_to_tuple(rect: ctypes.wintypes.RECT) -> Tuple[int, int, int, int]:
    return (int(rect.left), int(rect.top), int(rect.right), int(rect.bottom))


def get_monitor_rects(
    hwnd: Optional[int] = None,
) -> Tuple[Tuple[int, int, int, int], Tuple[int, int, int, int]]:
    """
    Returns (monitor_rect, work_rect) in physical screen pixels for the monitor
    hosting `hwnd` (or primary monitor if `hwnd` is None).
    `work_rect` excludes the Windows Taskbar so overlays avoid covering the clock.
    """
    enable_dpi_awareness()
    user32 = ctypes.windll.user32

    if hwnd:
        hmon = user32.MonitorFromWindow(hwnd, 2)  # MONITOR_DEFAULTTONEAREST
        if hmon:
            mi = _MONITORINFO()
            mi.cbSize = ctypes.sizeof(_MONITORINFO)
            if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
                return _rect_to_tuple(mi.rcMonitor), _rect_to_tuple(mi.rcWork)

    sw = int(user32.GetSystemMetrics(0))
    sh = int(user32.GetSystemMetrics(1))
    mon_rect = (0, 0, sw, sh)

    work = ctypes.wintypes.RECT()
    if user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(work), 0):  # SPI_GETWORKAREA
        return mon_rect, _rect_to_tuple(work)
    return mon_rect, mon_rect


def find_window_by_title_substring(tag: str) -> Optional[int]:
    """Find the visible top-level window HWND whose title contains `tag`."""
    if sys.platform != "win32" or not tag:
        return None

    user32 = ctypes.windll.user32
    found_hwnd = []

    EnumWindowsProc = ctypes.WINFUNCTYPE(
        ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM
    )

    def _callback(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        if tag in buf.value:
            found_hwnd.append(int(hwnd))
            return False
        return True

    user32.EnumWindows(EnumWindowsProc(_callback), 0)
    return found_hwnd[0] if found_hwnd else None


def focus_and_maximize_window(hwnd: int) -> None:
    """
    Maximize the target window (keeping Windows Taskbar visible) and raise it
    to the foreground across Windows foreground-lock restrictions.
    """
    if sys.platform != "win32" or not hwnd:
        return

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    SW_SHOWMAXIMIZED = 3
    SW_RESTORE = 9
    HWND_TOPMOST = -1
    HWND_NOTOPMOST = -2
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    SWP_SHOWWINDOW = 0x0040

    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
    user32.ShowWindow(hwnd, SW_SHOWMAXIMIZED)

    fg_hwnd = user32.GetForegroundWindow()
    curr_tid = kernel32.GetCurrentThreadId()
    fg_tid = user32.GetWindowThreadProcessId(fg_hwnd, None) if fg_hwnd else 0

    attached = False
    if fg_tid and fg_tid != curr_tid:
        attached = bool(user32.AttachThreadInput(curr_tid, fg_tid, True))

    try:
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        if user32.GetForegroundWindow() != hwnd:
            user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
            user32.SetWindowPos(
                hwnd,
                HWND_NOTOPMOST,
                0,
                0,
                0,
                0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW,
            )
            user32.SetForegroundWindow(hwnd)
    finally:
        if attached:
            user32.AttachThreadInput(curr_tid, fg_tid, False)


def _is_solid_black(img: Image.Image) -> bool:
    """Detect completely black captures returned when a desktop session is locked."""
    extrema = img.convert("RGB").getextrema()
    return all(lo == 0 and hi == 0 for lo, hi in extrema)


def _extract_dc_bitmap(memdc, bmp, width: int, height: int) -> Image.Image:
    gdi32 = ctypes.windll.gdi32
    bmi = _BITMAPINFOHEADER()
    bmi.biSize = ctypes.sizeof(_BITMAPINFOHEADER)
    bmi.biWidth = width
    bmi.biHeight = -height  # top-down DIB
    bmi.biPlanes = 1
    bmi.biBitCount = 32
    bmi.biCompression = 0  # BI_RGB

    buf = ctypes.create_string_buffer(width * height * 4)
    gdi32.GetDIBits(memdc, bmp, 0, height, buf, ctypes.byref(bmi), 0)
    return Image.frombuffer("RGBA", (width, height), buf, "raw", "BGRA", 0, 1).convert("RGB")


def _grab_monitor_imagegrab(mon_rect: Tuple[int, int, int, int]) -> Optional[Image.Image]:
    try:
        img = ImageGrab.grab(bbox=mon_rect, all_screens=True).convert("RGB")
        if img.width > 0 and img.height > 0 and not _is_solid_black(img):
            return img
    except Exception:
        pass
    return None


def _grab_monitor_bitblt(mon_rect: Tuple[int, int, int, int]) -> Optional[Image.Image]:
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    left, top, right, bottom = mon_rect
    width = right - left
    height = bottom - top
    if width <= 0 or height <= 0:
        return None

    SRCCOPY = 0x00CC0020
    CAPTUREBLT = 0x40000000

    hdc = user32.GetDC(0)
    if not hdc:
        return None
    memdc = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, width, height)
    old = gdi32.SelectObject(memdc, bmp) if memdc and bmp else None
    try:
        if not memdc or not bmp:
            return None
        ok = gdi32.BitBlt(memdc, 0, 0, width, height, hdc, left, top, SRCCOPY | CAPTUREBLT)
        if not ok:
            return None
        img = _extract_dc_bitmap(memdc, bmp, width, height)
        return None if _is_solid_black(img) else img
    except Exception:
        return None
    finally:
        if old:
            gdi32.SelectObject(memdc, old)
        if bmp:
            gdi32.DeleteObject(bmp)
        if memdc:
            gdi32.DeleteDC(memdc)
        user32.ReleaseDC(0, hdc)


def _grab_window_printwindow(
    hwnd: int, mon_rect: Optional[Tuple[int, int, int, int]] = None
) -> Optional[Image.Image]:
    """
    Fallback window capture via Win32 PrintWindow (preserves the Chromium title bar
    and URL address bar even when desktop BitBlt is blocked in a locked/isolated session).
    """
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    rect = ctypes.wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None

    w = rect.right - rect.left
    h = rect.bottom - rect.top
    if w <= 0 or h <= 0:
        return None

    hdc = user32.GetWindowDC(hwnd)
    if not hdc:
        return None
    memdc = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    old = gdi32.SelectObject(memdc, bmp) if memdc and bmp else None
    try:
        if not memdc or not bmp:
            return None
        PW_RENDERFULLCONTENT = 2
        ok = user32.PrintWindow(hwnd, memdc, PW_RENDERFULLCONTENT)
        if not ok:
            ok = user32.PrintWindow(hwnd, memdc, 0)
        if not ok:
            return None

        img = _extract_dc_bitmap(memdc, bmp, w, h)
        if _is_solid_black(img):
            return None

        # Trim Windows invisible resize border outside monitor bounds
        if mon_rect:
            ml, mt, mr, mb = mon_rect
            crop_l = max(0, ml - rect.left)
            crop_t = max(0, mt - rect.top)
            crop_r = min(w, mr - rect.left)
            crop_b = min(h, mb - rect.top)
            if crop_r > crop_l and crop_b > crop_t:
                img = img.crop((crop_l, crop_t, crop_r, crop_b))
        return img
    except Exception:
        return None
    finally:
        if old:
            gdi32.SelectObject(memdc, old)
        if bmp:
            gdi32.DeleteObject(bmp)
        if memdc:
            gdi32.DeleteDC(memdc)
        user32.ReleaseDC(hwnd, hdc)


def _locate_page_hwnd(page) -> Optional[int]:
    """Identify the exact OS window handle owning `page` via a transient title tag."""
    tag = f"[__CHK_{uuid.uuid4().hex[:8]}__]"
    tagged = False
    try:
        page.evaluate(
            """(tag) => {
                window.__orig_chk_title = document.title;
                document.title = (document.title || "TraCuu") + " " + tag;
            }""",
            tag,
        )
        tagged = True
        for _ in range(30):
            hwnd = find_window_by_title_substring(tag)
            if hwnd:
                return hwnd
            time.sleep(0.05)
        return None
    except Exception:
        return None
    finally:
        if tagged:
            try:
                page.evaluate(
                    """() => {
                        if (window.__orig_chk_title !== undefined) {
                            document.title = window.__orig_chk_title;
                            delete window.__orig_chk_title;
                        }
                    }"""
                )
                time.sleep(0.1)
            except Exception:
                pass


def capture_browser_fullscreen(
    page,
    output_path: str,
    log_fn: Optional[Callable[[str], None]] = None,
) -> dict:
    """
    Focuses and maximizes the Playwright browser window, then captures the full
    Windows desktop screen (preserving browser URL bar + Windows Taskbar date/time).
    Falls back gracefully to PrintWindow or page.screenshot if desktop capture is blocked.

    Returns dict: {"mode": "desktop" | "window" | "page", "work_area_local": tuple | None}.
    """
    def _log(msg: str):
        if log_fn:
            try:
                log_fn(msg)
            except Exception:
                pass

    if sys.platform != "win32":
        page.screenshot(path=output_path, full_page=False)
        return {"mode": "page", "work_area_local": None}

    enable_dpi_awareness()
    hwnd = _locate_page_hwnd(page)
    if hwnd:
        focus_and_maximize_window(hwnd)
        time.sleep(0.45)

    mon_rect, work_rect = get_monitor_rects(hwnd)
    ml, mt, _, _ = mon_rect
    work_area_local = (
        work_rect[0] - ml,
        work_rect[1] - mt,
        work_rect[2] - ml,
        work_rect[3] - mt,
    )

    img = _grab_monitor_imagegrab(mon_rect) or _grab_monitor_bitblt(mon_rect)
    if img is not None:
        img.save(output_path, "PNG", quality=95)
        return {"mode": "desktop", "work_area_local": work_area_local}

    _log(
        "Cảnh báo: Không thể chụp trực tiếp màn hình desktop Windows "
        "(màn hình đang khóa hoặc phiên tách biệt), chuyển sang chụp khung cửa sổ trình duyệt..."
    )
    if hwnd:
        win_img = _grab_window_printwindow(hwnd, mon_rect)
        if win_img is not None:
            win_img.save(output_path, "PNG", quality=95)
            return {"mode": "window", "work_area_local": None}

    page.screenshot(path=output_path, full_page=False)
    return {"mode": "page", "work_area_local": None}
