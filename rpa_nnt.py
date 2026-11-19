# =========================================================================
# Copyright (c) 2026 NDKBVH. All rights reserved.
# Author: NDKBVH
# =========================================================================

import os
import re
import sys
import time
import datetime
from pathlib import Path

# Configure utf-8 stdout/stderr for Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Configure Playwright local browser directory if bundled pw-browsers exists
local_pw_browsers = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pw-browsers")
if os.path.exists(local_pw_browsers):
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = local_pw_browsers

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import ddddocr
from watermark import add_taxpayer_watermark
from screen_capture import capture_browser_fullscreen, enable_dpi_awareness

# Initialize ddddocr instance
ocr_solver = ddddocr.DdddOcr(show_ad=False)

def log(msg, callback=None):
    now = datetime.datetime.now().strftime("%H:%M:%S")
    formatted = f"[{now}] {msg}"
    print(formatted)
    if callback:
        try:
            callback(formatted)
        except Exception:
            pass

def clean_mst(mst_raw):
    if not mst_raw:
        return ""
    # Retain digits and hyphen
    cleaned = re.sub(r'[^\d\-]', '', str(mst_raw)).strip()
    return cleaned

def run_taxpayer_lookup(mst: str, headless: bool = False, log_callback=None, output_dir=None):
    """
    RPA engine to query taxpayer info on https://tracuunnt.gdt.gov.vn/tcnnt/mstdn.jsp
    Solves captcha with ddddocr, extracts taxpayer details & status, and takes watermarked screenshot.
    """
    cleaned_mst = clean_mst(mst)
    if not cleaned_mst:
        return {
            "success": False,
            "status_code": "ERROR",
            "message": "Mã số thuế không hợp lệ hoặc để trống.",
            "mst": mst
        }

    log(f"Khởi động tra cứu Người Nộp Thuế cho MST: '{cleaned_mst}' (Headless: {headless})...", log_callback)

    if not output_dir:
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "screenshots")
    os.makedirs(output_dir, exist_ok=True)

    result_data = {
        "success": False,
        "mst": cleaned_mst,
        "status_code": "NOT_FOUND",
        "message": "Chưa có kết quả",
        "ten_nnt": "",
        "dia_chi": "",
        "co_quan_thue": "",
        "trang_thai_mst": "",
        "items": [],
        "screenshot_url": "",
        "screenshot_filename": "",
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    try:
        if not headless:
            enable_dpi_awareness()
        with sync_playwright() as p:
            log("Khởi chạy trình duyệt Chromium...", log_callback)
            browser = p.chromium.launch(
                headless=headless,
                args=["--start-maximized", "--no-sandbox", "--disable-setuid-sandbox"]
            )
            ctx_kwargs = {
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            }
            if headless:
                ctx_kwargs["viewport"] = {"width": 1280, "height": 900}
            else:
                ctx_kwargs["no_viewport"] = True
            context = browser.new_context(**ctx_kwargs)
            page = context.new_page()

            portal_url = "https://tracuunnt.gdt.gov.vn/tcnnt/mstdn.jsp"
            log(f"Truy cập Cổng Thông tin Người Nộp Thuế: {portal_url}", log_callback)
            page.goto(portal_url, timeout=35000, wait_until="domcontentloaded")
            time.sleep(1.5)

            max_retries = 5
            captcha_success = False

            for attempt in range(1, max_retries + 1):
                log(f"Thực hiện giải mã Captcha và điền thông tin (lần {attempt}/{max_retries})...", log_callback)

                # Fill MST
                mst_input = page.query_selector('input[name="mst"]')
                if mst_input:
                    mst_input.fill("")
                    mst_input.fill(cleaned_mst)
                else:
                    log("Không tìm thấy trường nhập Mã số thuế!", log_callback)
                    break

                # Locate Captcha image
                captcha_img = page.query_selector('img[src*="/tcnnt/captcha.png"]')
                if not captcha_img:
                    log("Không tìm thấy hình ảnh Captcha!", log_callback)
                    break

                captcha_bytes = captcha_img.screenshot()
                captcha_code = ocr_solver.classification(captcha_bytes).strip()
                log(f"Mã Captcha nhận diện được: '{captcha_code}'", log_callback)

                captcha_input = page.query_selector('input[name="captcha"], #captcha')
                if captcha_input:
                    captcha_input.fill("")
                    captcha_input.fill(captcha_code)
                time.sleep(0.5)

                # Click Submit button (calls search())
                log("Bấm nút 'Tra cứu'...", log_callback)
                submit_btn = page.query_selector('input[type="button"][value*="Tra cứu"], input[onclick*="search"], input.btn-action, input[value="Tra cứu"]')
                if submit_btn:
                    submit_btn.click()
                else:
                    page.evaluate("if (typeof search === 'function') search();")

                time.sleep(2.5)

                # Check if captcha failed alert or error message appeared
                content = page.content()
                if "Vui lòng nhập đúng mã xác nhận" in content or "Mã xác minh không đúng" in content:
                    log(f"Mã Captcha '{captcha_code}' chưa chính xác. Đang đổi mã mới và thử lại...", log_callback)
                    # Click captcha image to refresh
                    try:
                        captcha_img.click()
                    except Exception:
                        pass
                    time.sleep(1.5)
                    continue
                else:
                    log("Mã Captcha hợp lệ! Đang chờ bảng dữ liệu phản hồi...", log_callback)
                    captcha_success = True
                    break

            if not captcha_success:
                log("Đã thử 5 lần giải mã Captcha nhưng chưa thành công.", log_callback)

            # Wait for result table
            time.sleep(1.5)
            
            # Extract Table Content
            rows = page.query_selector_all("table.ta_border tr")
            extracted_items = []

            for r_idx, row in enumerate(rows):
                tds = row.query_selector_all("td")
                if len(tds) >= 6:
                    stt = tds[0].inner_text().strip()
                    row_mst = tds[1].inner_text().strip()
                    ten_nnt = tds[2].inner_text().strip().replace("\n", " ")
                    dia_chi = tds[3].inner_text().strip().replace("\n", " ")
                    cq_thue = tds[4].inner_text().strip().replace("\n", " ")
                    trang_thai = tds[5].inner_text().strip().replace("\n", " ")

                    if stt.isdigit() or row_mst:
                        extracted_items.append({
                            "stt": stt,
                            "mst": row_mst,
                            "ten_nnt": ten_nnt,
                            "dia_chi": dia_chi,
                            "co_quan_thue": cq_thue,
                            "trang_thai_mst": trang_thai
                        })

            full_text = page.inner_text("body")
            if "Không tìm thấy người nộp thuế nào phù hợp" in full_text or len(extracted_items) == 0:
                result_data["success"] = True
                result_data["status_code"] = "NOT_FOUND"
                result_data["message"] = "Không tìm thấy người nộp thuế nào phù hợp trên hệ thống Cục Thuế."
                log("Kết quả tra cứu: KHÔNG TÌM THẤY thông tin người nộp thuế!", log_callback)
            else:
                result_data["success"] = True
                result_data["status_code"] = "FOUND"
                result_data["items"] = extracted_items
                
                # Prioritize exact matching MST (e.g. head office without branch suffix)
                main_item = None
                for it in extracted_items:
                    if it["mst"] == cleaned_mst:
                        main_item = it
                        break
                if not main_item:
                    main_item = extracted_items[0]

                result_data["ten_nnt"] = main_item["ten_nnt"]
                result_data["dia_chi"] = main_item["dia_chi"]
                result_data["co_quan_thue"] = main_item["co_quan_thue"]
                result_data["trang_thai_mst"] = main_item["trang_thai_mst"]
                result_data["message"] = f"Tìm thấy người nộp thuế: {main_item['ten_nnt']} | Trạng thái: {main_item['trang_thai_mst']}"
                log(f"Kết quả tra cứu: THÀNH CÔNG! {main_item['ten_nnt']} - {main_item['trang_thai_mst']}", log_callback)

            # Capture timestamped confirmation screenshot
            safe_mst = re.sub(r'[^\w\-]', '_', cleaned_mst)
            timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            raw_shot_filename = f"NNT_{safe_mst}_{timestamp_str}_raw.png"
            final_shot_filename = f"XacNhan_NNT_{safe_mst}_{timestamp_str}.png"

            raw_shot_path = os.path.join(output_dir, raw_shot_filename)
            final_shot_path = os.path.join(output_dir, final_shot_filename)

            log("Định dạng giao diện & Chụp ảnh màn hình bằng chứng...", log_callback)
            work_area_local = None
            if not headless:
                page.evaluate("if (document.body.scrollHeight > window.innerHeight) document.body.style.zoom = '85%'")
                page.evaluate("window.scrollTo(0, 0)")
                time.sleep(0.5)
                cap_info = capture_browser_fullscreen(
                    page,
                    raw_shot_path,
                    log_fn=lambda m: log(m, log_callback),
                )
                work_area_local = cap_info.get("work_area_local")
                if cap_info.get("mode") == "desktop":
                    log("Đã chụp toàn màn hình máy tính (gồm thanh URL web & khung ngày giờ Windows).", log_callback)
            else:
                log("Chế độ Chạy ngầm chỉ chụp nội dung trang web; bỏ chọn 'Chạy ngầm' để chụp toàn màn hình máy tính.", log_callback)
                page.screenshot(path=raw_shot_path, full_page=True)

            log("Đóng dấu thời gian (Timestamp Watermark Badge) lên ảnh bằng chứng...", log_callback)
            add_taxpayer_watermark(
                image_path=raw_shot_path,
                output_path=final_shot_path,
                nnt_info={
                    "mst": cleaned_mst,
                    "ten_nnt": result_data["ten_nnt"],
                    "co_quan_thue": result_data["co_quan_thue"],
                    "trang_thai_mst": result_data["trang_thai_mst"]
                },
                search_status=result_data["message"],
                work_area_local=work_area_local,
            )

            # Clean raw screenshot
            if os.path.exists(raw_shot_path):
                try:
                    os.remove(raw_shot_path)
                except Exception:
                    pass

            result_data["screenshot_url"] = f"/static/screenshots/{final_shot_filename}"
            result_data["screenshot_filename"] = final_shot_filename
            log(f"Đã lưu ảnh xác nhận: {final_shot_filename}", log_callback)

            browser.close()
            log("Đóng phiên trình duyệt.", log_callback)

    except Exception as e:
        log(f"Lỗi trong quá trình tra cứu NNT: {str(e)}", log_callback)
        result_data["success"] = False
        result_data["status_code"] = "ERROR"
        result_data["message"] = f"Lỗi hệ thống: {str(e)}"

    return result_data

if __name__ == "__main__":
    test_mst = sys.argv[1] if len(sys.argv) > 1 else "0110269067"
    res = run_taxpayer_lookup(test_mst, headless=True)
    print("Test Result:", res)
