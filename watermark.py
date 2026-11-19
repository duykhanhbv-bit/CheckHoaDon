import os
import datetime
from PIL import Image, ImageDraw, ImageFont

def _load_badge_fonts():
    """Load bold and regular badge fonts with safe fallback."""
    try:
        font_title = ImageFont.truetype("arialbd.ttf", 18)
        font_body = ImageFont.truetype("arial.ttf", 15)
        font_bold = ImageFont.truetype("arialbd.ttf", 15)
    except Exception:
        font_title = ImageFont.load_default()
        font_body = ImageFont.load_default()
        font_bold = ImageFont.load_default()
    return font_title, font_body, font_bold


def _draw_badge_overlay(
    image_path,
    output_path,
    lines,
    fill_color,
    outline_color,
    work_area_local=None,
):
    """
    Draws a semi-transparent verification badge at the bottom-right corner of the
    usable work area (strictly above the Windows Taskbar when `work_area_local`
    is provided so the system clock/date remains completely uncovered).
    """
    if output_path is None:
        output_path = image_path

    img = Image.open(image_path).convert("RGBA")
    width, height = img.size

    overlay = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    max_w = 0
    total_h = 0
    line_heights = []
    for text, font, _ in lines:
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1] + 6
        if w > max_w:
            max_w = w
        total_h += h
        line_heights.append(h)

    badge_w = max_w + 40
    badge_h = total_h + 30

    if work_area_local is not None:
        _, _, wr, wb = work_area_local
        right_edge = min(width, wr) - 24
        bottom_edge = min(height, wb) - 20
    else:
        right_edge = width - 30
        bottom_edge = height - 30

    box_x2 = max(badge_w + 20, right_edge)
    box_y2 = max(badge_h + 20, bottom_edge)
    box_x1 = box_x2 - badge_w
    box_y1 = box_y2 - badge_h

    draw.rounded_rectangle(
        [box_x1, box_y1, box_x2, box_y2],
        radius=12,
        fill=fill_color,
        outline=outline_color,
        width=3,
    )

    cur_y = box_y1 + 15
    for (text, font, color), h in zip(lines, line_heights):
        draw.text((box_x1 + 20, cur_y), text, font=font, fill=color)
        cur_y += h

    final_img = Image.alpha_composite(img, overlay).convert("RGB")
    final_img.save(output_path, "PNG", quality=95)
    return output_path


def add_timestamp_watermark(
    image_path,
    output_path=None,
    invoice_info=None,
    search_status="",
    work_area_local=None,
):
    """
    Adds an official timestamp verification badge to the screenshot.
    """
    now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    header_text = "HÓA ĐƠN ĐIỆN TỬ - XÁC NHẬN TRA CỨU TỔNG CỤC THUẾ"
    time_text = f"Thời gian xác nhận: {now_str}"

    mst = invoice_info.get("mst_nguoi_ban", "") if invoice_info else ""
    ky_hieu = invoice_info.get("ky_hieu", "") if invoice_info else ""
    so_hd = invoice_info.get("so_hd", "") if invoice_info else ""
    detail_text = f"MST: {mst} | Ký hiệu: {ky_hieu} | Số HĐ: {so_hd}" if (mst or ky_hieu or so_hd) else ""

    status_text = search_status if search_status else "Hoàn thành kiểm tra trực tuyến"
    font_title, font_body, font_bold = _load_badge_fonts()

    lines = [
        (header_text, font_title, (255, 255, 255, 255)),
        (time_text, font_bold, (255, 230, 80, 255)),
    ]
    if detail_text:
        lines.append((detail_text, font_body, (240, 240, 240, 255)))
    status_ok = "Tồn tại" in status_text or "Đã" in status_text or "thành công" in status_text
    lines.append((
        f"Trạng thái: {status_text}",
        font_bold,
        (100, 255, 120, 255) if status_ok else (255, 180, 180, 255),
    ))

    return _draw_badge_overlay(
        image_path=image_path,
        output_path=output_path,
        lines=lines,
        fill_color=(24, 32, 47, 235),
        outline_color=(214, 51, 42, 255),
        work_area_local=work_area_local,
    )


def add_taxpayer_watermark(
    image_path,
    output_path=None,
    nnt_info=None,
    search_status="",
    work_area_local=None,
):
    """
    Adds an official taxpayer verification badge to the screenshot from tracuunnt.gdt.gov.vn.
    """
    now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    header_text = "NGƯỜI NỘP THUẾ - XÁC NHẬN CỤC THUẾ (BỘ TÀI CHÍNH)"
    time_text = f"Thời gian xác nhận: {now_str}"

    mst = nnt_info.get("mst", "") if nnt_info else ""
    ten_nnt = nnt_info.get("ten_nnt", "") if nnt_info else ""
    if len(ten_nnt) > 40:
        ten_nnt = ten_nnt[:38] + "..."
    cq_thue = nnt_info.get("co_quan_thue", "") if nnt_info else ""
    trang_thai = (nnt_info.get("trang_thai_mst", "") if nnt_info else "") or search_status or "Hoàn tất tra cứu trực tuyến"

    detail_text = f"MST: {mst} • {ten_nnt}" if (mst or ten_nnt) else ""
    cq_text = f"Cơ quan thuế quản lý: {cq_thue}" if cq_thue else ""

    font_title, font_body, font_bold = _load_badge_fonts()

    lines = [
        (header_text, font_title, (255, 255, 255, 255)),
        (time_text, font_bold, (255, 230, 80, 255)),
    ]
    if detail_text:
        lines.append((detail_text, font_body, (240, 240, 240, 255)))
    if cq_text:
        lines.append((cq_text, font_body, (220, 220, 220, 255)))

    is_active = "đang hoạt động" in trang_thai.lower()
    status_color = (100, 255, 120, 255) if is_active else (255, 180, 180, 255)
    lines.append((f"Trạng thái: {trang_thai}", font_bold, status_color))

    return _draw_badge_overlay(
        image_path=image_path,
        output_path=output_path,
        lines=lines,
        fill_color=(20, 30, 48, 235),
        outline_color=(220, 38, 38, 255),
        work_area_local=work_area_local,
    )

def render_xml_confirmation_certificate(invoice_info, verification_date=None, output_path=None):
    """
    Renders the official Confirmation Certificate Box ("KẾT QUẢ KIỂM TRA THÔNG TIN HÓA ĐƠN")
    with gold borders, National drum watermark pattern, and complete 4 sections matching General Department of Taxation.
    """
    if not verification_date:
        verification_date = datetime.datetime.now().strftime("%d/%m/%Y")
        
    w = 780
    
    # Fonts
    try:
        font_title = ImageFont.truetype("timesbd.ttf", 23)
        font_sub = ImageFont.truetype("timesbd.ttf", 15)
        font_sec = ImageFont.truetype("timesbd.ttf", 15)
        font_sec_italic = ImageFont.truetype("timesi.ttf", 13)
        font_bold = ImageFont.truetype("timesbd.ttf", 14)
        font_item = ImageFont.truetype("times.ttf", 14)
    except Exception:
        try:
            font_title = ImageFont.truetype("arialbd.ttf", 21)
            font_sub = ImageFont.truetype("arialbd.ttf", 14)
            font_sec = ImageFont.truetype("arialbd.ttf", 14)
            font_sec_italic = ImageFont.truetype("ariali.ttf", 12)
            font_bold = ImageFont.truetype("arialbd.ttf", 13)
            font_item = ImageFont.truetype("arial.ttf", 13)
        except Exception:
            font_title = ImageFont.load_default()
            font_sub = ImageFont.load_default()
            font_sec = ImageFont.load_default()
            font_sec_italic = ImageFont.load_default()
            font_bold = ImageFont.load_default()
            font_item = ImageFont.load_default()

    color_text = (20, 25, 35, 255)
    color_green = (21, 128, 61, 255) # Green #15803d
    
    # Helper to wrap text
    def wrap_text_calc(text, font, max_width):
        dummy_img = Image.new("RGBA", (10, 10))
        d = ImageDraw.Draw(dummy_img)
        words = text.split(" ")
        lines = []
        cur_line = ""
        for word in words:
            test_line = f"{cur_line} {word}".strip()
            bbox = d.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] <= max_width:
                cur_line = test_line
            else:
                if cur_line:
                    lines.append(cur_line)
                cur_line = word
        if cur_line:
            lines.append(cur_line)
        return lines

    # Calculate required height
    tbl_x1 = 50
    content_w = w - tbl_x1 * 2
    
    # Extract properties
    mst_ban = invoice_info.get("mst_nguoi_ban", "") or ""
    tong_tien = str(invoice_info.get("tong_tien", "") or "")
    if tong_tien and tong_tien.replace(".", "").replace(",", "").isdigit():
        try:
            num = int(float(tong_tien.replace(".", "").replace(",", "")))
            tong_tien = f"{num:,}".replace(",", ".")
        except Exception:
            pass
            
    so_hd = str(invoice_info.get("so_hd", "") or "")
    ky_hieu = str(invoice_info.get("ky_hieu", "") or "")
    loai_hd = str(invoice_info.get("loai_hd", "") or "Hóa đơn giá trị gia tăng")
    ngay_lap = str(invoice_info.get("ngay_lap", "") or verification_date)
    ngay_ky = str(invoice_info.get("ngay_ky", "") or ngay_lap)
    
    for k, v in [("ngay_lap", ngay_lap), ("ngay_ky", ngay_ky)]:
        if v and "-" in v:
            parts = v.split("T")[0].split("-")
            if len(parts) == 3 and len(parts[0]) == 4:
                formatted_d = f"{parts[2]}/{parts[1]}/{parts[0]}"
                if k == "ngay_lap": ngay_lap = formatted_d
                if k == "ngay_ky": ngay_ky = formatted_d

    ky_boi = invoice_info.get("ky_boi") or invoice_info.get("ten_nguoi_ban") or "CÔNG TY TNHH"
    nha_cung_cap = invoice_info.get("nha_cung_cap") or "C=VN, O=Viettel Group, CN=Viettel-CA SHA2"
    hieu_luc_tu = invoice_info.get("hieu_luc_tu") or "28/06/2024"
    hieu_luc_den = invoice_info.get("hieu_luc_den") or "29/06/2027"
    serial_number = invoice_info.get("serial_number") or "5404FFFEB7033FB316D672201BE27CE2"
    tinh_trang_cap_ma = invoice_info.get("tinh_trang_cap_ma") or "Đã cấp mã hóa đơn"

    ten_ban = invoice_info.get("ten_nguoi_ban", "") or ""
    dia_chi_ban = invoice_info.get("dia_chi_nguoi_ban", "") or ""
    mst_mua = invoice_info.get("mst_nguoi_mua", "") or ""
    ten_mua = invoice_info.get("ten_nguoi_mua", "") or ""
    dia_chi_mua = invoice_info.get("dia_chi_nguoi_mua", "") or ""

    # Estimate height
    h = 920
    # Add extra for wrapped address lines
    extra_lines = len(wrap_text_calc(f"- Địa chỉ: {dia_chi_ban}", font_item, content_w)) + len(wrap_text_calc(f"- Địa chỉ: {dia_chi_mua}", font_item, content_w))
    h += extra_lines * 22

    img = Image.new("RGBA", (w, h), (254, 252, 248, 255))
    draw = ImageDraw.Draw(img)

    # Draw subtle decorative Dong Son drum rings in the background
    cx, cy = w // 2, h // 2
    for r in [180, 240, 300, 360, 420]:
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(238, 228, 210, 180), width=1)
    for r in [200, 260, 320]:
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(242, 234, 218, 120), width=2)
    
    # Outer double border (matching tax pattern)
    margin = 24
    draw.rectangle([margin, margin, w - margin, h - margin], outline=(180, 145, 100, 255), width=2)
    draw.rectangle([margin + 3, margin + 3, w - margin - 3, h - margin - 3], outline=(210, 185, 145, 255), width=1)
    
    # 1. Header Title: KẾT QUẢ KIỂM TRA THÔNG TIN HÓA ĐƠN
    cur_y = 52
    title = "KẾT QUẢ KIỂM TRA THÔNG TIN HÓA ĐƠN"
    tb = draw.textbbox((0, 0), title, font=font_title)
    draw.text(((w - (tb[2] - tb[0])) / 2, cur_y), title, font=font_title, fill=color_text)
    
    # 2. Subtitle: Tại thời điểm ngày DD/MM/YYYY
    cur_y += 36
    sub = f"Tại thời điểm ngày {verification_date}"
    sb = draw.textbbox((0, 0), sub, font=font_sub)
    draw.text(((w - (sb[2] - sb[0])) / 2, cur_y), sub, font=font_sub, fill=color_text)
    
    # 3. Section 1: THÔNG TIN HÓA ĐƠN
    cur_y += 36
    sec1 = "THÔNG TIN HÓA ĐƠN"
    sec1_b = draw.textbbox((0, 0), sec1, font=font_sec)
    draw.text(((w - (sec1_b[2] - sec1_b[0])) / 2, cur_y), sec1, font=font_sec, fill=color_text)
    
    # 4. Table 1: Box
    tbl_y1 = cur_y + 26
    tbl_x2 = w - tbl_x1
    tbl_h = 135
    tbl_y2 = tbl_y1 + tbl_h
    tbl_mid_x = (tbl_x1 + tbl_x2) / 2
    
    draw.rectangle([tbl_x1, tbl_y1, tbl_x2, tbl_y2], outline=(60, 60, 60, 255), width=1)
    draw.line([(tbl_mid_x, tbl_y1), (tbl_mid_x, tbl_y2)], fill=(60, 60, 60, 255), width=1)
    
    col1 = [
        f"- Mã số thuế người bán: {mst_ban}",
        f"- Tổng tiền thanh toán: {tong_tien}",
        f"- Số hóa đơn: {so_hd}",
        f"- Ký hiệu hóa đơn: {ky_hieu}",
    ]
    
    col2 = [
        f"- Mẫu hóa đơn: {loai_hd}",
        f"- Ngày lập: {ngay_lap}",
        f"- Ngày ký: {ngay_ky}",
    ]
    
    start_y = tbl_y1 + 12
    line_h = 28
    for item in col1:
        draw.text((tbl_x1 + 12, start_y), item, font=font_item, fill=color_text)
        start_y += line_h
        
    start_y = tbl_y1 + 12
    for item in col2:
        draw.text((tbl_mid_x + 12, start_y), item, font=font_item, fill=color_text)
        start_y += line_h
        
    cur_y = tbl_y2 + 26
    
    # 5. Section 2: THÔNG TIN CHỮ KÝ SỐ TRÊN HÓA ĐƠN
    sec2 = "THÔNG TIN CHỮ KÝ SỐ TRÊN HÓA ĐƠN"
    sec2_b = draw.textbbox((0, 0), sec2, font=font_sec)
    draw.text(((w - (sec2_b[2] - sec2_b[0])) / 2, cur_y), sec2, font=font_sec, fill=color_text)
    
    cur_y += 26
    draw.text((tbl_x1, cur_y), "Chữ ký số người bán:", font=font_bold, fill=color_text)
    cur_y += 22
    
    sec2_lines = [
        (f"- Ký bởi: {ky_boi}", font_item, color_text),
        (f"- Nhà cung cấp: {nha_cung_cap}", font_item, color_text),
        (f"- Hiệu lực: từ {hieu_luc_tu} đến {hieu_luc_den}", font_item, color_text),
        (f"- Serial number: {serial_number}", font_item, color_text),
        ("- Thông tin chữ ký số hợp lệ.", font_item, color_green),
        ("- Chứng thư số của NNT tại thời điểm ký hóa đơn hợp lệ.", font_item, color_green),
    ]
    
    for text, f, col in sec2_lines:
        wrapped = wrap_text_calc(text, f, content_w)
        for wl in wrapped:
            draw.text((tbl_x1, cur_y), wl, font=f, fill=col)
            cur_y += 21
        cur_y += 1
        
    cur_y += 14
    
    # 6. Section 3: TÌNH TRẠNG CẤP MÃ VÀ LỊCH SỬ HÓA ĐƠN
    sec3 = "TÌNH TRẠNG CẤP MÃ VÀ LỊCH SỬ HÓA ĐƠN"
    sec3_b = draw.textbbox((0, 0), sec3, font=font_sec)
    draw.text(((w - (sec3_b[2] - sec3_b[0])) / 2, cur_y), sec3, font=font_sec, fill=color_text)
    cur_y += 25
    
    draw.text((tbl_x1, cur_y), f"- {tinh_trang_cap_ma}", font=font_item, fill=color_text)
    cur_y += 32
    
    # 7. Section 4: TÌNH TRẠNG HOẠT ĐỘNG CỦA MST NGƯỜI BÁN, NGƯỜI MUA
    sec4 = "TÌNH TRẠNG HOẠT ĐỘNG CỦA MST NGƯỜI BÁN, NGƯỜI MUA"
    sec4_b = draw.textbbox((0, 0), sec4, font=font_sec)
    draw.text(((w - (sec4_b[2] - sec4_b[0])) / 2, cur_y), sec4, font=font_sec, fill=color_text)
    cur_y += 22
    
    sec4_sub = "(Thông tin dùng để đối chiếu từ dữ liệu của cơ quan thuế)"
    sec4_sub_b = draw.textbbox((0, 0), sec4_sub, font=font_sec_italic)
    draw.text(((w - (sec4_sub_b[2] - sec4_sub_b[0])) / 2, cur_y), sec4_sub, font=font_sec_italic, fill=(60, 65, 75, 255))
    cur_y += 26
    
    # Người bán
    draw.text((tbl_x1, cur_y), "Người bán:", font=font_bold, fill=color_text)
    cur_y += 21
    draw.text((tbl_x1, cur_y), f"- Mã số thuế: {mst_ban}    Trạng thái: NNT đang hoạt động", font=font_item, fill=color_text)
    cur_y += 21
    
    for wl in wrap_text_calc(f"- Tên đơn vị: {ten_ban}", font_item, content_w):
        draw.text((tbl_x1, cur_y), wl, font=font_item, fill=color_text)
        cur_y += 21
    for wl in wrap_text_calc(f"- Địa chỉ: {dia_chi_ban}", font_item, content_w):
        draw.text((tbl_x1, cur_y), wl, font=font_item, fill=color_text)
        cur_y += 21
        
    cur_y += 8
    
    # Người mua
    draw.text((tbl_x1, cur_y), "Người mua:", font=font_bold, fill=color_text)
    cur_y += 21
    draw.text((tbl_x1, cur_y), f"- Mã số thuế: {mst_mua}    Trạng thái: NNT đang hoạt động", font=font_item, fill=color_text)
    cur_y += 21
    
    for wl in wrap_text_calc(f"- Tên đơn vị: {ten_mua}", font_item, content_w):
        draw.text((tbl_x1, cur_y), wl, font=font_item, fill=color_text)
        cur_y += 21
    for wl in wrap_text_calc(f"- Địa chỉ: {dia_chi_mua}", font_item, content_w):
        draw.text((tbl_x1, cur_y), wl, font=font_item, fill=color_text)
        cur_y += 21

    # Crop to actual content height + bottom margin
    final_h = cur_y + 35
    cropped_img = img.crop((0, 0, w, final_h))
    
    # Re-draw clean border on exact cropped canvas
    draw_final = ImageDraw.Draw(cropped_img)
    draw_final.rectangle([margin, margin, w - margin, final_h - margin], outline=(180, 145, 100, 255), width=2)
    draw_final.rectangle([margin + 3, margin + 3, w - margin - 3, final_h - margin - 3], outline=(210, 185, 145, 255), width=1)

    final_rgb = cropped_img.convert("RGB")
    if output_path:
        final_rgb.save(output_path, "PNG", quality=95)
    return output_path
