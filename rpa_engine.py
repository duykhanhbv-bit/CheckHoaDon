# =========================================================================
# Copyright (c) 2026 NDKBVH. All rights reserved.
# Author: NDKBVH
# Module: RPA Engine - Tra Cứu Hóa Đơn Điện Tử & Đọc Hóa Đơn XML
# =========================================================================

import os
import re
import sys
import time
import base64
import datetime
from pathlib import Path

# Configure utf-8 stdout/stderr for Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Configure Playwright local browser directory if bundled pw-browsers exists
local_pw_browsers = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pw-browsers")
if os.path.exists(local_pw_browsers) and not os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = local_pw_browsers

from playwright.sync_api import sync_playwright
import ddddocr
import pymupdf
from watermark import add_timestamp_watermark, render_xml_confirmation_certificate
from extractor import extract_xml_content
from screen_capture import capture_browser_fullscreen, enable_dpi_awareness


def _create_browser_context(browser, headless: bool, headless_viewport=(1440, 900)):
    """Creates a Playwright context: maximized native viewport when headed, fixed viewport when headless."""
    ctx_kwargs = {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    }
    if headless:
        ctx_kwargs["viewport"] = {"width": headless_viewport[0], "height": headless_viewport[1]}
    else:
        ctx_kwargs["no_viewport"] = True
    return browser.new_context(**ctx_kwargs)


def _capture_and_watermark_invoice(
    page,
    raw_path: str,
    final_path: str,
    invoice_info: dict,
    search_status: str,
    headless: bool,
    log_fn,
):
    """Captures full desktop screen when headed (URL bar + Windows Taskbar clock) or page viewport when headless."""
    work_area_local = None
    if not headless:
        cap_info = capture_browser_fullscreen(page, raw_path, log_fn=log_fn)
        work_area_local = cap_info.get("work_area_local")
        mode = cap_info.get("mode")
        if mode == "desktop":
            log_fn("Đã chụp toàn màn hình máy tính (gồm thanh URL web & khung ngày giờ Windows).")
        elif mode == "window":
            log_fn("Đã chụp khung cửa sổ trình duyệt kèm thanh địa chỉ URL.")
    else:
        log_fn("Chế độ Chạy ngầm chỉ chụp nội dung trang web; bỏ chọn 'Chạy ngầm' để chụp toàn màn hình máy tính.")
        page.screenshot(path=raw_path, full_page=False)

    log_fn("Đóng dấu thời gian (Timestamp Watermark) lên ảnh bằng chứng...")
    add_timestamp_watermark(
        image_path=raw_path,
        output_path=final_path,
        invoice_info=invoice_info,
        search_status=search_status,
        work_area_local=work_area_local,
    )
    if os.path.exists(raw_path):
        os.remove(raw_path)


def _ensure_gdt_portal_ready(page, ready_selector: str, log_fn) -> None:
    """
    Waits for Next.js SPA hydration on hoadondientu.gdt.gov.vn (reloading once if
    Windows Chromium hit ERR_CERT_VERIFIER_CHANGED leaving a blank page) and closes modals.
    """
    try:
        page.wait_for_selector(ready_selector, state="attached", timeout=8000)
    except Exception:
        log_fn("Trang Cổng Thuế chưa dựng xong giao diện, đang tải lại trang...")
        try:
            page.reload(wait_until="domcontentloaded", timeout=35000)
            page.wait_for_selector(ready_selector, state="attached", timeout=15000)
        except Exception:
            pass

    for _ in range(3):
        close_btns = page.query_selector_all(
            '.ant-modal-close, button.ant-modal-close, .ant-modal-close-x, .ant-modal-root button[aria-label="Close"]'
        )
        closed_any = False
        for cb in close_btns:
            if cb.is_visible():
                try:
                    cb.click()
                    closed_any = True
                except Exception:
                    pass
        if closed_any:
            log_fn("Đóng popup thông báo của Cục Thuế...")
            page.wait_for_timeout(450)
        else:
            break

# Initialize ddddocr instance once
ocr_solver = ddddocr.DdddOcr(show_ad=False)

def get_chromium_executable():
    """
    Returns available chromium executable path if exists.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.expandvars(r"%LOCALAPPDATA%\ms-playwright\chromium-1243\chrome-win64\chrome.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\ms-playwright\chromium-1234\chrome-win64\chrome.exe"),
        os.path.join(base_dir, "pw-browsers", "chromium-1234", "chrome-win64", "chrome.exe"),
        os.path.join(base_dir, "pw-browsers", "chromium-1243", "chrome-win64", "chrome.exe"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None

def solve_captcha_from_page(page, in_modal: bool = None):
    """
    Extracts base64 SVG/PNG captcha from modal or page, renders to crisp PNG via pymupdf if SVG,
    and classifies it with ddddocr.
    - If in_modal is True: strictly searches within .ant-modal
    - If in_modal is False: strictly searches on the main page (excluding .ant-modal)
    - If in_modal is None: auto-detects based on whether .ant-modal is currently visible
    """
    if in_modal is None:
        try:
            in_modal = page.is_visible('.ant-modal')
        except Exception:
            in_modal = False

    if in_modal:
        captcha_img = page.query_selector('.ant-modal .Captcha__ImageWrapper-sc-1up1k1e-0 img, .ant-modal img[alt="captcha"], .ant-modal img[src*="data:image"]')
    else:
        # On main form (Tab 1), avoid any hidden modal elements
        captcha_img = page.query_selector('form .Captcha__ImageWrapper-sc-1up1k1e-0 img, .Captcha__ImageWrapper-sc-1up1k1e-0 img, form img[alt="captcha"], img[alt="captcha"]')

    if not captcha_img:
        svg_selector = '.ant-modal svg.captcha-svg, .ant-modal svg' if in_modal else 'form svg.captcha-svg, form .Captcha__ImageWrapper-sc-1up1k1e-0 svg, svg.captcha-svg'
        svg_el = page.query_selector(svg_selector)
        if svg_el:
            try:
                svg_content = svg_el.evaluate("el => el.outerHTML")
                if svg_content:
                    doc = pymupdf.open(stream=svg_content.encode('utf-8'), filetype="svg")
                    pix = doc[0].get_pixmap(matrix=pymupdf.Matrix(2, 2))
                    png_bytes = pix.tobytes("png")
                    raw_text = ocr_solver.classification(png_bytes).strip().upper()
                    clean_text = re.sub(r'[^A-Z0-9]', '', raw_text)
                    return clean_text, png_bytes
            except Exception:
                pass
        return "", None

    src = captcha_img.get_attribute('src') or ''
    if not src:
        return "", None

    try:
        if src.startswith("data:image/svg+xml;base64,"):
            b64_str = src.split(",", 1)[1]
            svg_bytes = base64.b64decode(b64_str)
            doc = pymupdf.open(stream=svg_bytes, filetype="svg")
            pix = doc[0].get_pixmap(matrix=pymupdf.Matrix(2, 2))
            png_bytes = pix.tobytes("png")
        elif src.startswith("data:image/svg+xml;utf8,") or src.startswith("data:image/svg+xml,"):
            svg_str = urllib.parse.unquote(src.split(",", 1)[1])
            doc = pymupdf.open(stream=svg_str.encode('utf-8'), filetype="svg")
            pix = doc[0].get_pixmap(matrix=pymupdf.Matrix(2, 2))
            png_bytes = pix.tobytes("png")
        elif src.startswith("data:image/png;base64,") or src.startswith("data:image/jpeg;base64,") or "base64," in src:
            b64_str = src.split("base64,", 1)[1]
            png_bytes = base64.b64decode(b64_str)
        else:
            return "", None

        raw_text = ocr_solver.classification(png_bytes).strip().upper()
        clean_text = re.sub(r'[^A-Z0-9]', '', raw_text)
        return clean_text, png_bytes
    except Exception as e:
        print(f"Lỗi giải Captcha: {e}")
        return "", None

def refresh_captcha_on_page(page):
    """
    Triggers Captcha refresh button on Tab 1 main form (outside modal).
    """
    try:
        page.evaluate("""() => {
            const wrapper = document.querySelector('form .Captcha__ImageWrapper-sc-1up1k1e-0, .Captcha__ImageWrapper-sc-1up1k1e-0');
            if (wrapper) {
                const btn = wrapper.querySelector('button');
                if (btn) { btn.click(); return; }
            }
            const syncBtn = document.querySelector('button:has(.anticon-sync), button:has(svg[id="cap_cha_btn"])');
            if (syncBtn) syncBtn.click();
        }""")
    except Exception:
        pass

def refresh_captcha_in_modal(page):
    """
    Triggers Captcha refresh button inside the active Ant Design modal.
    """
    try:
        btn = page.locator('.ant-modal .Captcha__ImageWrapper-sc-1up1k1e-0 button, .ant-modal button.ant-btn-icon-only, .ant-modal img + button').first
        if btn.is_visible():
            btn.click(timeout=3000)
            return
    except Exception:
        pass

    try:
        page.evaluate("""() => {
            const btns = Array.from(document.querySelectorAll('.ant-modal button'));
            for (const b of btns) {
                if (b.className.includes('ant-btn-icon-only') || b.querySelector('svg') || b.className.includes('IconButton')) {
                    if (!b.className.includes('ant-modal-close')) {
                        b.click();
                        return;
                    }
                }
            }
        }""")
    except Exception:
        pass

def select_invoice_type(page, target_type):
    """
    Selects invoice type from Ant Design select dropdown using canonical mapping.
    """
    target = (target_type or "").strip().lower()
    
    # Map friendly names to exact Portal dropdown text
    canonical_type = "Hóa đơn điện tử giá trị gia tăng"
    if "tích hợp" in target:
        if "bán hàng" in target:
            canonical_type = "Hóa đơn bán hàng tích hợp biên lai thu thuế, phí, lệ phí"
        else:
            canonical_type = "Hóa đơn giá trị gia tăng tích hợp biên lai thu thuế, phí, lệ phí"
    elif "xuất kho" in target or "vận chuyển" in target:
        if "đại lý" in target:
            canonical_type = "Phiếu xuất kho gửi bán hàng đại lý"
        else:
            canonical_type = "Phiếu xuất kho kiêm vận chuyển nội bộ"
    elif "tài sản công" in target:
        canonical_type = "Hóa đơn bán tài sản công"
    elif "dự trữ quốc gia" in target:
        canonical_type = "Hóa đơn bán hàng dự trữ quốc gia"
    elif "thương mại" in target:
        canonical_type = "Hoá đơn thương mại"
    elif "bán hàng" in target:
        canonical_type = "Hóa đơn bán hàng"
    elif "giá trị gia tăng" in target or "gtgt" in target or "vat" in target:
        canonical_type = "Hóa đơn điện tử giá trị gia tăng"
    elif target:
        canonical_type = target_type

    select_box = page.query_selector('.ant-select')
    if not select_box:
        return
        
    current_val = select_box.inner_text().strip()
    if current_val == canonical_type:
        return # Đã được chọn chính xác
        
    try:
        select_box.click()
        page.wait_for_timeout(600)
        options = page.query_selector_all('.ant-select-dropdown-menu-item')
        for opt in options:
            opt_text = opt.inner_text().strip()
            if opt_text == canonical_type or canonical_type.lower() == opt_text.lower():
                opt.click()
                page.wait_for_timeout(400)
                return
        for opt in options:
            opt_text = opt.inner_text().strip()
            if opt_text.lower().startswith(canonical_type.lower()):
                opt.click()
                page.wait_for_timeout(400)
                return
    except Exception as e:
        print(f"Lỗi khi chọn Loại hóa đơn: {e}")

def run_invoice_lookup(invoice_data, headless=False, log_callback=None, output_dir="static/screenshots"):
    """
    Executes Playwright RPA lookup on Tab 1 (https://hoadondientu.gdt.gov.vn/)
    """
    def log(msg):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {msg}"
        try:
            print(formatted, flush=True)
        except Exception:
            try:
                sys.stdout.buffer.write((formatted + "\n").encode('utf-8', errors='replace'))
                sys.stdout.buffer.flush()
            except Exception:
                pass
        if log_callback:
            try:
                log_callback(formatted)
            except Exception:
                pass

    os.makedirs(output_dir, exist_ok=True)
    exe = get_chromium_executable()
    
    result = {
        "success": False,
        "status_code": "",
        "message": "",
        "details": [],
        "screenshot_url": "",
        "screenshot_filename": "",
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "invoice_info": invoice_data
    }

    log("Khởi động trình duyệt Playwright Chromium...")
    if not headless:
        enable_dpi_awareness()
    with sync_playwright() as p:
        launch_kwargs = {
            "headless": headless,
            "args": ["--start-maximized", "--disable-blink-features=AutomationControlled"]
        }
        if exe:
            launch_kwargs["executable_path"] = exe
            
        browser = p.chromium.launch(**launch_kwargs)
        context = _create_browser_context(browser, headless=headless)
        page = context.new_page()

        try:
            log("Truy cập Cổng tra cứu Hóa đơn điện tử: https://hoadondientu.gdt.gov.vn/")
            for attempt_nav in range(1, 4):
                try:
                    page.goto('https://hoadondientu.gdt.gov.vn/', wait_until='domcontentloaded', timeout=40000)
                    page.wait_for_timeout(2000)
                    break
                except Exception as e_nav:
                    if attempt_nav == 3:
                        raise e_nav
                    log(f"Đang thử lại truy cập Cổng Thuế ({attempt_nav}/3)...")
                    page.wait_for_timeout(2000)

            _ensure_gdt_portal_ready(page, '#nbmst, .ant-modal-close', log)

            # 1. Select Loại hóa đơn
            loai_hd = invoice_data.get("loai_hd") or "Hóa đơn điện tử giá trị gia tăng"
            log(f"Chọn loại hóa đơn: {loai_hd}")
            select_invoice_type(page, loai_hd)

            # 2. Fill MST người bán
            mst = (invoice_data.get("mst_nguoi_ban") or "").strip()
            log(f"Điền MST người bán (*): {mst}")
            page.fill('#nbmst', mst)

            # 3. Fill Ký hiệu hóa đơn (6 ký tự chuẩn)
            ky_hieu = (invoice_data.get("ky_hieu") or "").strip().upper()
            if len(ky_hieu) == 7 and ky_hieu[0].isdigit():
                ky_hieu = ky_hieu[1:]
            log(f"Điền Ký hiệu hóa đơn (*): {ky_hieu}")
            page.fill('#khhdon', ky_hieu)

            # 4. Fill Số hóa đơn
            so_hd = (invoice_data.get("so_hd") or "").strip()
            log(f"Điền Số hóa đơn (*): {so_hd}")
            page.fill('#shdon', so_hd)

            # 5. Fill Tổng tiền thuế (nếu form có trường này)
            tgtthue_el = page.query_selector('#tgtthue')
            if tgtthue_el and tgtthue_el.is_visible():
                tien_thue = str(invoice_data.get("tong_tien_thue") or "0").strip()
                log(f"Điền Tổng tiền thuế: {tien_thue}")
                try:
                    page.fill('#tgtthue', tien_thue, timeout=3000)
                except Exception as e_thue:
                    log(f"Không thể điền #tgtthue ({e_thue}), tiếp tục...")
            else:
                log("Loại hóa đơn này không có trường Tổng tiền thuế trên Cổng Thuế (bỏ qua).")

            # 6. Fill Tổng tiền thanh toán (nếu form có trường này)
            tgtttbso_el = page.query_selector('#tgtttbso')
            if tgtttbso_el and tgtttbso_el.is_visible():
                tong_tien = str(invoice_data.get("tong_tien") or "").strip()
                log(f"Điền Tổng tiền thanh toán: {tong_tien}")
                try:
                    page.fill('#tgtttbso', tong_tien, timeout=3000)
                except Exception as e_tien:
                    log(f"Không thể điền #tgtttbso ({e_tien}), tiếp tục...")
            else:
                log("Loại hóa đơn này không có trường Tổng tiền thanh toán trên Cổng Thuế (bỏ qua).")

            # 6b. Fill Ngày lập hóa đơn (nếu form có trường này, ví dụ Phiếu xuất kho)
            date_inp = page.query_selector("input[placeholder='Chọn thời điểm']")
            if date_inp and date_inp.is_visible():
                ngay_lap = str(invoice_data.get("ngay_lap") or "").strip()
                if ngay_lap:
                    log(f"Điền Ngày lập hóa đơn: {ngay_lap}")
                    try:
                        date_inp.fill(ngay_lap, timeout=3000)
                        page.keyboard.press("Enter")
                        page.wait_for_timeout(300)
                    except Exception:
                        pass

            # 7. Captcha processing loop
            captcha_success = False
            max_captcha_retries = 8

            for attempt in range(1, max_captcha_retries + 1):
                log(f"Tiến hành giải mã Captcha (lần {attempt}/{max_captcha_retries})...")
                cap_text, _ = solve_captcha_from_page(page, in_modal=False)
                log(f"Mã Captcha nhận diện được: '{cap_text}' (độ dài {len(cap_text)})")

                # If length is not 6, click refresh captcha
                if len(cap_text) != 6:
                    log("Độ dài Captcha chưa đúng chuẩn 6 ký tự, đang làm mới Captcha...")
                    refresh_captcha_on_page(page)
                    page.wait_for_timeout(1200)
                    continue

                # Fill captcha
                cap_input = page.locator('form #cvalue, #cvalue').first
                cap_input.fill(cap_text, timeout=3000)
                page.wait_for_timeout(400)

                # Click Submit
                log("Bấm nút 'Tìm kiếm'...")
                submit_btn = page.query_selector('button[type="submit"]')
                if submit_btn and submit_btn.is_visible():
                    submit_btn.click()
                else:
                    page.keyboard.press("Enter")

                page.wait_for_timeout(2500)

                # Check if captcha error notification popped up
                msg_el = page.query_selector('.ant-message-notice, .ant-notification-notice')
                msg_text = msg_el.inner_text().strip() if msg_el else ""
                
                if "Mã captcha không đúng" in msg_text or "captcha không đúng" in msg_text:
                    log("Mã Captcha chưa chính xác, hệ thống đang tự động thử lại mã mới...")
                    refresh_captcha_on_page(page)
                    page.wait_for_timeout(1000)
                    continue
                else:
                    log("Mã Captcha hợp lệ! Đang chờ kết quả phản hồi từ Cổng Thuế...")
                    captcha_success = True
                    break

            if not captcha_success:
                raise Exception("Không thể vượt qua mã Captcha sau nhiều lần thử lại.")

            # Wait for result to render (polling until spinner disappears and status text appears)
            log("Đang nhận kết quả phản hồi từ Cổng Thuế...")
            status_text = ""
            details = []
            for _ in range(25):
                page.wait_for_timeout(500)
                body_text = page.inner_text('body')
                loading_el = page.query_selector('.ant-spin-spinning, .ant-loading')
                if loading_el and loading_el.is_visible():
                    continue
                if "Tồn tại hóa đơn có thông tin trùng khớp" in body_text:
                    status_text = "Tồn tại hóa đơn hợp lệ trên hệ thống Thuế"
                    result["success"] = True
                    result["status_code"] = "FOUND"
                    break
                elif "Không tồn tại hóa đơn có thông tin trùng khớp" in body_text:
                    status_text = "Không tồn tại hóa đơn có thông tin trùng khớp"
                    result["success"] = True
                    result["status_code"] = "NOT_FOUND"
                    break

            body_text = page.inner_text('body')
            if not status_text:
                if "Tồn tại hóa đơn có thông tin trùng khớp" in body_text:
                    status_text = "Tồn tại hóa đơn hợp lệ trên hệ thống Thuế"
                    result["success"] = True
                    result["status_code"] = "FOUND"
                elif "Không tồn tại hóa đơn có thông tin trùng khớp" in body_text:
                    status_text = "Không tồn tại hóa đơn có thông tin trùng khớp"
                    result["success"] = True
                    result["status_code"] = "NOT_FOUND"
                else:
                    status_text = "Đã hoàn thành tra cứu"
                    result["success"] = True
                    result["status_code"] = "COMPLETED"

            for line in body_text.splitlines():
                line = line.strip()
                if any(kw in line for kw in ["Tồn tại hóa đơn", "Trạng thái xử lý", "Trạng thái hóa đơn", "Thay thế cho hóa đơn", "Không tồn tại"]):
                    if line not in details:
                        details.append(line)

            if "/" in ky_hieu or (len(ky_hieu) > 0 and ky_hieu[0] not in ["C", "K", "1", "2", "3", "4", "5", "6"]):
                details.append("Lưu ý: Ký hiệu này có định dạng theo Thông tư 32/2011/TT-BTC cũ (chứa dấu '/').")

            result["message"] = status_text
            result["details"] = details
            log(f"Kết quả tra cứu: {status_text}")
            if details:
                log(f"Chi tiết: {' | '.join(details)}")

            # 8. Adjust zoom and capture evidence screenshot
            log("Định dạng giao diện & Chụp ảnh màn hình bằng chứng...")
            page.evaluate("""() => {
                document.body.style.zoom = '75%';
                window.scrollTo(0, 0);
                document.querySelectorAll('*').forEach(el => {
                    if (el.scrollTop > 0) el.scrollTop = 0;
                });
            }""")
            page.wait_for_timeout(800)

            safe_so_hd = re.sub(r'[\/\\:\*\?"<>\|\s]', '_', so_hd) if so_hd else "0000"
            safe_ky_hieu = re.sub(r'[\/\\:\*\?"<>\|\s]', '_', ky_hieu) if ky_hieu else "HD"
            timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"XacNhan_{safe_ky_hieu}_{safe_so_hd}_{timestamp_str}.png"
            raw_screen_path = os.path.join(output_dir, f"raw_{filename}")
            stamped_screen_path = os.path.join(output_dir, filename)

            _capture_and_watermark_invoice(
                page=page,
                raw_path=raw_screen_path,
                final_path=stamped_screen_path,
                invoice_info=invoice_data,
                search_status=status_text,
                headless=headless,
                log_fn=log,
            )

            result["screenshot_url"] = f"/static/screenshots/{filename}"
            result["screenshot_filename"] = filename
            log(f"Đã lưu ảnh xác nhận: {filename}")

        except Exception as e:
            error_msg = str(e)
            log(f"Lỗi trong quá trình RPA: {error_msg}")
            result["success"] = False
            result["message"] = f"Lỗi: {error_msg}"
            try:
                err_filename = f"Loi_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                err_path = os.path.join(output_dir, err_filename)
                page.screenshot(path=err_path)
                result["screenshot_url"] = f"/static/screenshots/{err_filename}"
            except Exception:
                pass
        finally:
            log("Đóng phiên trình duyệt.")
            browser.close()

    return result

def prepare_uploadable_xml(xml_file_path: str) -> str:
    """
    Checks if XML contains oversized/invalid base64 QR code (<DLQRCode>) that causes
    the frontend on hoadondientu.gdt.gov.vn to crash with 'code length overflow'.
    If so, creates a sanitized temporary XML file for portal upload.
    """
    try:
        if not os.path.exists(xml_file_path):
            return xml_file_path
        with open(xml_file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Check if DLQRCode has long base64 image data or exceeds 500 characters
        qr_match = re.search(r'<DLQRCode>(.*?)</DLQRCode>', content, flags=re.DOTALL)
        if qr_match:
            qr_content = qr_match.group(1).strip()
            if len(qr_content) > 500 or "iVBORw" in qr_content or "data:image" in qr_content:
                cleaned_content = re.sub(r'<DLQRCode>.*?</DLQRCode>', '<DLQRCode></DLQRCode>', content, flags=re.DOTALL)
                temp_dir = os.path.join(os.path.dirname(xml_file_path), "_temp_gdt")
                os.makedirs(temp_dir, exist_ok=True)
                temp_path = os.path.join(temp_dir, f"clean_{os.path.basename(xml_file_path)}")
                with open(temp_path, "w", encoding="utf-8") as f_out:
                    f_out.write(cleaned_content)
                return temp_path
    except Exception:
        pass
    return xml_file_path

def run_xml_lookup(xml_file_path, invoice_info=None, headless=False, log_callback=None, output_dir="static/screenshots"):
    """
    Executes Playwright RPA lookup directly on Tab 'Đọc hóa đơn XML' (https://hoadondientu.gdt.gov.vn/)
    Uploads XML, solves Captcha modal, verifies against GDT, and generates the exact Confirmation Certificate Card.
    """
    def log(msg):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {msg}"
        try:
            print(formatted, flush=True)
        except Exception:
            try:
                sys.stdout.buffer.write((formatted + "\n").encode('utf-8', errors='replace'))
                sys.stdout.buffer.flush()
            except Exception:
                pass
        if log_callback:
            try:
                log_callback(formatted)
            except Exception:
                pass

    os.makedirs(output_dir, exist_ok=True)
    exe = get_chromium_executable()

    if not invoice_info:
        try:
            invoice_info = extract_xml_content(xml_file_path)
        except Exception:
            invoice_info = {}

    result = {
        "success": False,
        "status_code": "",
        "message": "",
        "details": [],
        "screenshot_url": "",
        "screenshot_filename": "",
        "confirmation_crop_url": "",
        "confirmation_crop_filename": "",
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "invoice_info": invoice_info,
        "xml_path": str(xml_file_path)
    }

    upload_file_path = prepare_uploadable_xml(xml_file_path)

    log("Khởi động trình duyệt Playwright Chromium...")
    if not headless:
        enable_dpi_awareness()
    with sync_playwright() as p:
        launch_kwargs = {
            "headless": headless,
            "args": ["--start-maximized", "--disable-blink-features=AutomationControlled"]
        }
        if exe:
            launch_kwargs["executable_path"] = exe

        browser = p.chromium.launch(**launch_kwargs)
        context = _create_browser_context(browser, headless=headless)
        page = context.new_page()

        try:
            log("Truy cập Cổng Hóa đơn điện tử: https://hoadondientu.gdt.gov.vn/...")
            for attempt_nav in range(1, 5):
                try:
                    page.goto('https://hoadondientu.gdt.gov.vn/', wait_until='domcontentloaded', timeout=35000)
                    page.wait_for_timeout(2000)
                    break
                except Exception as e_nav:
                    if attempt_nav == 4:
                        try:
                            page.goto('https://hoadondientu.gdt.gov.vn/', wait_until='commit', timeout=20000)
                            page.wait_for_timeout(3000)
                            break
                        except Exception:
                            raise e_nav
                    log(f"Đang thử lại kết nối Cổng Thuế ({attempt_nav}/4)...")
                    page.wait_for_timeout(3000)

            _ensure_gdt_portal_ready(page, '.ant-tabs-tab, .ant-modal-close', log)

            # Click tab "Đọc hóa đơn XML"
            log("Chuyển sang tab 'Đọc hóa đơn XML'...")
            xml_tab = page.locator('.ant-tabs-tab:has-text("Đọc hóa đơn XML"), div[role="tab"]:has-text("Đọc hóa đơn XML")').first
            if xml_tab.is_visible():
                xml_tab.click()
            else:
                page.evaluate("() => { const tabs = Array.from(document.querySelectorAll('.ant-tabs-tab, div[role=\"tab\"]')); const t = tabs.find(x => x.innerText.includes('Đọc hóa đơn XML')); if (t) t.click(); }")
            page.wait_for_timeout(1500)

            # Upload XML file
            log(f"Nạp tệp XML: {os.path.basename(xml_file_path)}...")
            page.wait_for_selector('input[type="file"]', state="attached", timeout=12000)
            page.set_input_files('input[type="file"]', upload_file_path)
            page.wait_for_timeout(2500)

            # Check if page crashed with error boundary
            body_text_check = page.inner_text('body')
            if "code length overflow" in body_text_check:
                raise Exception("Cổng Thuế báo lỗi định dạng mã QR (code length overflow).")

            # Locate check button dynamically
            check_btn = page.locator('button:has-text("Kiểm tra thông tin"), button:has-text("Kiểm tra"), .ant-btn:has-text("Kiểm tra")').first
            button_found = False
            try:
                check_btn.wait_for(state="visible", timeout=8000)
                button_found = True
            except Exception:
                log("Đang nạp lại tệp XML kích hoạt render...")
                page.set_input_files('input[type="file"]', upload_file_path)
                try:
                    check_btn.wait_for(state="visible", timeout=8000)
                    button_found = True
                except Exception:
                    pass

            if not button_found:
                alert_el = page.query_selector('.ant-alert-message, .ant-message-notice, .ant-notification-notice')
                if alert_el and alert_el.is_visible():
                    raise Exception(f"Cổng Thuế thông báo: {alert_el.inner_text().strip()}")
                raise Exception("Không tìm thấy nút 'Kiểm tra thông tin hóa đơn' trên Cổng Thuế sau khi nạp tệp XML.")

            log("Bấm nút 'Kiểm tra thông tin hóa đơn'...")
            try:
                check_btn.scroll_into_view_if_needed()
                page.wait_for_timeout(300)
                check_btn.click(timeout=6000)
            except Exception:
                page.evaluate("() => { const btns = Array.from(document.querySelectorAll('button')); const b = btns.find(x => x.innerText.includes('Kiểm tra')); if (b) b.click(); }")
            page.wait_for_timeout(1500)

            # Wait for Captcha modal to appear
            try:
                page.wait_for_selector('.ant-modal', timeout=8000)
            except Exception:
                pass

            # Captcha loop in modal
            log("Bắt đầu giải mã Captcha xác thực hóa đơn XML...")
            captcha_success = False
            max_captcha_retries = 10

            for attempt in range(1, max_captcha_retries + 1):
                # Check if modal is already closed
                if not page.is_visible('.ant-modal'):
                    log("Modal Captcha đã đóng thành công.")
                    captcha_success = True
                    break

                page.wait_for_timeout(500)
                cap_text, _ = solve_captcha_from_page(page, in_modal=True)
                log(f"Mã Captcha nhận diện (lần {attempt}/{max_captcha_retries}): '{cap_text}'")

                if not cap_text or len(cap_text) != 6:
                    log(f"Độ dài Captcha chưa chuẩn ({len(cap_text)} ký tự), đang làm mới mã...")
                    refresh_captcha_in_modal(page)
                    page.wait_for_timeout(1200)
                    continue

                # Locate input strictly inside modal, clear and fill
                modal_input = page.locator('.ant-modal #cvalue, .ant-modal input[type="text"]').first
                if modal_input.is_visible():
                    modal_input.click()
                    modal_input.fill("")
                    modal_input.fill(cap_text)
                    page.wait_for_timeout(400)

                # Locate and click "Xác nhận" button in modal
                confirm_btn = page.locator('.ant-modal button[type="submit"], .ant-modal button:has-text("Xác nhận"), .ant-modal .ant-btn-primary').first
                if confirm_btn.is_visible():
                    log("Bấm nút 'Xác nhận' trong popup Captcha...")
                    confirm_btn.click()
                else:
                    log("Không tìm thấy nút Xác nhận, nhấn phím Enter...")
                    page.keyboard.press("Enter")

                page.wait_for_timeout(2500)

                # Check if modal is now closed
                modal_visible = False
                try:
                    modal_visible = page.is_visible('.ant-modal')
                except Exception:
                    modal_visible = False

                if not modal_visible:
                    log("Mã Captcha chính xác! Popup đã đóng, đang nhận kết quả xác thực từ Cổng Thuế...")
                    captcha_success = True
                    break

                # If modal is still open, check error notification
                msg_el = page.query_selector('.ant-message-notice, .ant-notification-notice, .ant-alert, .ant-form-item-explain')
                msg_text = msg_el.inner_text().strip() if msg_el else ""
                log(f"Modal Captcha chưa đóng (phản hồi: '{msg_text}' hoặc sai mã) -> Làm mới để thử lại...")
                
                refresh_captcha_in_modal(page)
                page.wait_for_timeout(1200)

            if not captcha_success:
                raise Exception(f"Không thể vượt qua mã Captcha sau {max_captcha_retries} lần thử lại.")

            # Poll until loading spinner disappears and verification box renders (up to 15s)
            log("Đang chờ Cổng Thuế hoàn tất xác thực XML...")
            for _ in range(30):
                page.wait_for_timeout(500)
                loading_el = page.query_selector('.ant-spin-spinning, .ant-loading')
                if loading_el and loading_el.is_visible():
                    continue
                body_poll = page.inner_text('body')
                if any(kw in body_poll for kw in ["KẾT QUẢ KIỂM TRA", "Thông tin chữ ký số", "Tình trạng cấp mã"]):
                    page.wait_for_timeout(500)
                    break

            # Analyze page text & signature status
            body_text = page.inner_text('body')
            status_text = "Hóa đơn XML hợp lệ & đã xác thực trên Cổng Thuế"
            details = []

            for line in body_text.splitlines():
                line = line.strip()
                if any(kw in line for kw in ["Signature Valid", "Ký bởi", "Ký ngày", "MCCQT", "Mẫu số", "Ký hiệu:", "Số:"]):
                    if line not in details and len(line) < 150:
                        details.append(line)

            result["success"] = True
            result["status_code"] = "VERIFIED"
            result["message"] = status_text
            result["details"] = details
            log(f"Kết quả tra cứu: {status_text}")
            if details:
                log(f"Chữ ký & Thông tin: {' | '.join(details[:3])}")

            # Capture screenshots
            timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            so_hd = invoice_info.get("so_hd") or "HD"
            ky_hieu = invoice_info.get("ky_hieu") or "XML"
            safe_so_hd = re.sub(r'[\/\\:\*\?"<>\|\s]', '_', so_hd)
            safe_ky_hieu = re.sub(r'[\/\\:\*\?"<>\|\s]', '_', ky_hieu)

            # 1. Zoom out browser and capture full verified XML invoice screenshot with watermark
            final_filename = f"XacNhan_XML_{safe_ky_hieu}_{safe_so_hd}_{timestamp_str}.png"
            raw_filename = f"raw_{final_filename}"
            raw_path = os.path.join(output_dir, raw_filename)
            final_path = os.path.join(output_dir, final_filename)

            log("Thu nhỏ giao diện trình duyệt xuống 75% & Chụp ảnh toàn cảnh xác thực...")
            page.evaluate("document.body.style.zoom = '75%'")
            page.evaluate("""() => {
                const els = Array.from(document.querySelectorAll('h1,h2,h3,h4,div,span,b,strong,p'));
                const matches = els.filter(el => {
                    const txt = (el.innerText || '').trim();
                    return txt.includes('KẾT QUẢ KIỂM TRA THÔNG TIN HÓA ĐƠN') && el.children.length <= 2;
                });
                const resEl = matches.length > 0 ? matches[matches.length - 1] : null;
                if (resEl) {
                    resEl.scrollIntoView({ behavior: 'instant', block: 'start' });
                    window.scrollTo(0, 0);
                } else {
                    window.scrollTo(0, 0);
                }
            }""")
            page.wait_for_timeout(800)

            _capture_and_watermark_invoice(
                page=page,
                raw_path=raw_path,
                final_path=final_path,
                invoice_info=invoice_info,
                search_status="Xác thực XML thành công",
                headless=headless,
                log_fn=log,
            )

            result["screenshot_url"] = f"/static/screenshots/{final_filename}"
            result["screenshot_filename"] = final_filename
            log(f"Đã lưu ảnh chụp toàn cảnh: {final_filename}")

            # 2. Render and save the EXACT Confirmation Certificate Card ("KẾT QUẢ KIỂM TRA THÔNG TIN HÓA ĐƠN")
            crop_filename = f"BanChup_XacNhan_XML_{safe_ky_hieu}_{safe_so_hd}_{timestamp_str}.png"
            crop_path = os.path.join(output_dir, crop_filename)

            render_xml_confirmation_certificate(
                invoice_info=invoice_info,
                verification_date=datetime.datetime.now().strftime("%d/%m/%Y"),
                output_path=crop_path
            )

            result["confirmation_crop_url"] = f"/static/screenshots/{crop_filename}"
            result["confirmation_crop_filename"] = crop_filename
            log(f"Đã tạo bản chụp phần xác nhận chuẩn: {crop_filename}")

        except Exception as e:
            error_msg = str(e)
            log(f"Lỗi tra cứu XML: {error_msg}")
            result["success"] = False
            result["message"] = f"Lỗi: {error_msg}"
            try:
                err_fn = f"Loi_XML_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                page.screenshot(path=os.path.join(output_dir, err_fn))
                result["screenshot_url"] = f"/static/screenshots/{err_fn}"
            except Exception:
                pass
        finally:
            log("Đóng phiên trình duyệt.")
            try:
                browser.close()
            except Exception:
                pass
            if upload_file_path != str(xml_file_path) and os.path.exists(upload_file_path):
                try:
                    os.remove(upload_file_path)
                except Exception:
                    pass

    return result
