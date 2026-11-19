import os
import datetime
from io import BytesIO
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

def generate_excel_report(invoices: list) -> BytesIO:
    """
    Generates a beautifully styled Excel workbook for the batch invoice lookup results.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "DoiSoat_HoaDon_GDT"

    ws.views.sheetView[0].showGridLines = True

    header_fill = PatternFill(start_color="991B1B", end_color="991B1B", fill_type="solid") # Dark red
    header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    
    title_font = Font(name="Arial", size=16, bold=True, color="991B1B")
    sub_font = Font(name="Arial", size=10, italic=True, color="4B5563")

    thin_border = Border(
        left=Side(style='thin', color='D1D5DB'),
        right=Side(style='thin', color='D1D5DB'),
        top=Side(style='thin', color='D1D5DB'),
        bottom=Side(style='thin', color='D1D5DB')
    )

    found_fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid") # Green
    found_font = Font(name="Arial", size=10, bold=True, color="166534")

    not_found_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid") # Red
    not_found_font = Font(name="Arial", size=10, bold=True, color="991B1B")

    pending_fill = PatternFill(start_color="F3F4F6", end_color="F3F4F6", fill_type="solid")
    pending_font = Font(name="Arial", size=10, color="6B7280")

    ws["A1"] = "BẢNG KÊ ĐỐI SOÁT HÓA ĐƠN ĐIỆN TỬ - CỔNG TỔNG CỤC THUẾ"
    ws["A1"].font = title_font
    
    now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    ws["A2"] = f"Thời gian xuất: {now_str} | Bản quyền © 2026 NDKBVH. All rights reserved. | Nguồn dữ liệu: https://hoadondientu.gdt.gov.vn | Tổng số: {len(invoices)} hóa đơn"
    ws["A2"].font = sub_font

    ws.row_dimensions[1].height = 28
    ws.row_dimensions[2].height = 18
    ws.row_dimensions[3].height = 10

    headers = [
        "STT", "Tên Tệp Hóa Đơn", "MST Người Bán", "Ký Hiệu", 
        "Số Hóa Đơn", "Loại Hóa Đơn", "Tổng Tiền Thuế", "Tổng Thanh Toán", 
        "Kết Quả Tra Cứu", "Trạng Thái Xử Lý Cục Thuế", "Chi Tiết Phản Hồi", "Ảnh Xác Nhận"
    ]

    header_row = 4
    ws.row_dimensions[header_row].height = 26

    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border

    current_row = 5
    for idx, inv in enumerate(invoices, 1):
        ws.row_dimensions[current_row].height = 22

        status_code = inv.get("status_code", "") or inv.get("status", "")
        status_text = "Hợp Lệ (Tồn tại)" if status_code == "FOUND" else ("Không Tồn Tại" if status_code == "NOT_FOUND" else "Chưa tra cứu")
        
        details = inv.get("details", [])
        detail_str = " | ".join(details) if isinstance(details, list) else str(details or "")
        message = inv.get("message", "")

        screenshot_url = inv.get("screenshot_url", "")
        screenshot_name = os.path.basename(screenshot_url) if screenshot_url else ""

        raw_tax = str(inv.get("tong_tien_thue", "")).replace(".", "").replace(",", "").strip()
        tax_val = int(raw_tax) if raw_tax.isdigit() else inv.get("tong_tien_thue", "")

        raw_total = str(inv.get("tong_tien", "")).replace(".", "").replace(",", "").strip()
        total_val = int(raw_total) if raw_total.isdigit() else inv.get("tong_tien", "")

        row_data = [
            idx,
            inv.get("file_name", inv.get("original_filename", "")),
            inv.get("mst_nguoi_ban", ""),
            inv.get("ky_hieu", ""),
            inv.get("so_hd", ""),
            inv.get("loai_hd", ""),
            tax_val,
            total_val,
            status_text,
            message,
            detail_str,
            screenshot_name
        ]

        for col_idx, val in enumerate(row_data, 1):
            cell = ws.cell(row=current_row, column=col_idx, value=val)
            cell.font = Font(name="Arial", size=10)
            cell.border = thin_border

            if col_idx in [1, 3, 4, 5]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif col_idx in [7, 8]:
                cell.alignment = Alignment(horizontal="right", vertical="center")
                if isinstance(val, (int, float)):
                    cell.number_format = '#,##0'
            elif col_idx == 9: # Status
                cell.alignment = Alignment(horizontal="center", vertical="center")
                if status_code == "FOUND":
                    cell.fill = found_fill
                    cell.font = found_font
                elif status_code == "NOT_FOUND":
                    cell.fill = not_found_fill
                    cell.font = not_found_font
                else:
                    cell.fill = pending_fill
                    cell.font = pending_font
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

        current_row += 1

    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.row in [1, 2, 3]:
                continue
            val_str = str(cell.value or "")
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    ws.column_dimensions["A"].width = 6   # STT
    ws.column_dimensions["B"].width = 28  # File name
    ws.column_dimensions["C"].width = 16  # MST
    ws.column_dimensions["D"].width = 12  # Ky hieu
    ws.column_dimensions["E"].width = 12  # So HD
    ws.column_dimensions["F"].width = 30  # Loai HD
    ws.column_dimensions["G"].width = 18  # Tien thue
    ws.column_dimensions["H"].width = 18  # Tong tien
    ws.column_dimensions["I"].width = 18  # Ket qua
    ws.column_dimensions["J"].width = 35  # Trang thai
    ws.column_dimensions["K"].width = 45  # Chi tiet
    ws.column_dimensions["L"].width = 35  # Screenshot

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output

def generate_nnt_excel_report(nnt_list: list) -> BytesIO:
    """
    Generates an Excel report for Taxpayer (NNT) lookup results.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "TraCuu_NNT_CucThue"

    ws.views.sheetView[0].showGridLines = True

    header_fill = PatternFill(start_color="1D4ED8", end_color="1D4ED8", fill_type="solid") # Blue
    header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    
    title_font = Font(name="Arial", size=16, bold=True, color="1D4ED8")
    sub_font = Font(name="Arial", size=10, italic=True, color="4B5563")

    thin_border = Border(
        left=Side(style='thin', color='D1D5DB'),
        right=Side(style='thin', color='D1D5DB'),
        top=Side(style='thin', color='D1D5DB'),
        bottom=Side(style='thin', color='D1D5DB')
    )

    active_fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid") # Green
    active_font = Font(name="Arial", size=10, bold=True, color="166534")

    inactive_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid") # Red
    inactive_font = Font(name="Arial", size=10, bold=True, color="991B1B")

    ws["A1"] = "BẢNG KÊ TRA CỨU NGƯỜI NỘP THUẾ (MST) - CỤC THUẾ (BỘ TÀI CHÍNH)"
    ws["A1"].font = title_font
    
    now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    ws["A2"] = f"Thời gian xuất: {now_str} | Bản quyền © 2026 NDKBVH. All rights reserved. | Nguồn dữ liệu: https://tracuunnt.gdt.gov.vn | Tổng số: {len(nnt_list)} NNT"
    ws["A2"].font = sub_font

    ws.row_dimensions[1].height = 28
    ws.row_dimensions[2].height = 18
    ws.row_dimensions[3].height = 10

    headers = [
        "STT", "Mã Số Thuế", "Hóa Đơn / Tệp Nguồn", "Tên Người Nộp Thuế", 
        "Địa Chỉ Trụ Sở / Kinh Doanh", "Cơ Quan Thuế Quản Lý", 
        "Trạng Thái MST", "Thời Gian Tra Cứu", "Ảnh Bằng Chứng"
    ]

    header_row = 4
    ws.row_dimensions[header_row].height = 26

    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border

    current_row = 5
    for idx, item in enumerate(nnt_list, 1):
        ws.row_dimensions[current_row].height = 22

        trang_thai = item.get("trang_thai_mst", "") or item.get("message", "")
        screenshot_url = item.get("screenshot_url", "")
        screenshot_name = os.path.basename(screenshot_url) if screenshot_url else ""
        
        file_src = ", ".join(item.get("file_sources", [])) if isinstance(item.get("file_sources"), list) else str(item.get("file_sources") or item.get("file_name") or "-")

        row_data = [
            idx,
            item.get("mst", ""),
            file_src,
            item.get("ten_nnt", ""),
            item.get("dia_chi", ""),
            item.get("co_quan_thue", ""),
            trang_thai,
            item.get("timestamp", ""),
            screenshot_name
        ]

        for col_idx, val in enumerate(row_data, 1):
            cell = ws.cell(row=current_row, column=col_idx, value=val)
            cell.font = Font(name="Arial", size=10)
            cell.border = thin_border

            if col_idx in [1, 2, 8]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif col_idx == 7: # Status
                cell.alignment = Alignment(horizontal="center", vertical="center")
                if "đang hoạt động" in str(trang_thai).lower():
                    cell.fill = active_fill
                    cell.font = active_font
                else:
                    cell.fill = inactive_fill
                    cell.font = inactive_font
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

        current_row += 1

    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.row in [1, 2, 3]:
                continue
            val_str = str(cell.value or "")
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    ws.column_dimensions["A"].width = 6   # STT
    ws.column_dimensions["B"].width = 16  # MST
    ws.column_dimensions["C"].width = 25  # Hóa Đơn Nguồn
    ws.column_dimensions["D"].width = 36  # Tên NNT
    ws.column_dimensions["E"].width = 45  # Địa chỉ
    ws.column_dimensions["F"].width = 28  # Cơ quan thuế
    ws.column_dimensions["G"].width = 22  # Trạng thái
    ws.column_dimensions["H"].width = 20  # Thời gian
    ws.column_dimensions["I"].width = 32  # Screenshot

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output

def generate_xml_excel_report(xml_invoices: list) -> BytesIO:
    """
    Generates an Excel report for XML Invoice Verification results.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "XacThuc_HoaDon_XML"

    ws.views.sheetView[0].showGridLines = True

    header_fill = PatternFill(start_color="047857", end_color="047857", fill_type="solid") # Emerald Green
    header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    
    title_font = Font(name="Arial", size=16, bold=True, color="047857")
    sub_font = Font(name="Arial", size=10, italic=True, color="4B5563")

    thin_border = Border(
        left=Side(style='thin', color='D1D5DB'),
        right=Side(style='thin', color='D1D5DB'),
        top=Side(style='thin', color='D1D5DB'),
        bottom=Side(style='thin', color='D1D5DB')
    )

    verified_fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
    verified_font = Font(name="Arial", size=10, bold=True, color="166534")

    error_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
    error_font = Font(name="Arial", size=10, bold=True, color="991B1B")

    pending_fill = PatternFill(start_color="F3F4F6", end_color="F3F4F6", fill_type="solid")
    pending_font = Font(name="Arial", size=10, color="6B7280")

    ws["A1"] = "BẢNG KÊ ĐỐI SOÁT & XÁC THỰC HÓA ĐƠN XML - TỔNG CỤC THUẾ"
    ws["A1"].font = title_font
    
    now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    ws["A2"] = f"Thời gian xuất: {now_str} | Bản quyền © 2026 NDKBVH. All rights reserved. | Nguồn dữ liệu: Tab Đọc hóa đơn XML (hoadondientu.gdt.gov.vn) | Tổng số: {len(xml_invoices)} hóa đơn"
    ws["A2"].font = sub_font

    ws.row_dimensions[1].height = 28
    ws.row_dimensions[2].height = 18
    ws.row_dimensions[3].height = 10

    headers = [
        "STT", "Tên Tệp XML", "MST Người Bán", "Tên Người Bán", "Ký Hiệu", 
        "Số Hóa Đơn", "Ngày Lập", "Tổng Thanh Toán", "Trạng Thái Cổng Thuế", 
        "Chữ Ký Số / Chi Tiết", "Bản Chụp Xác Nhận", "Ảnh Toàn Cảnh"
    ]

    header_row = 4
    ws.row_dimensions[header_row].height = 26

    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border

    current_row = 5
    for idx, inv in enumerate(xml_invoices, 1):
        ws.row_dimensions[current_row].height = 22

        info = inv.get("invoice_info", {}) or inv
        mst = info.get("mst_nguoi_ban", inv.get("mst_nguoi_ban", ""))
        seller_name = info.get("ten_nguoi_ban", inv.get("ten_nguoi_ban", ""))
        ky_hieu = info.get("ky_hieu", inv.get("ky_hieu", ""))
        so_hd = info.get("so_hd", inv.get("so_hd", ""))
        ngay_lap = info.get("ngay_lap", inv.get("ngay_lap", ""))
        tong_tien = info.get("tong_tien", inv.get("tong_tien", ""))

        raw_total = str(tong_tien).replace(".", "").replace(",", "").strip()
        total_val = int(raw_total) if raw_total.isdigit() else tong_tien

        status_code = inv.get("status_code", "") or inv.get("status", "")
        status_text = "Đã Xác Thực Hợp Lệ" if status_code in ["VERIFIED", "FOUND", "success"] else ("Lỗi Xác Thực" if status_code == "error" else "Chờ Xác Thực")
        
        details = inv.get("details", [])
        detail_str = " | ".join(details) if isinstance(details, list) else str(details or inv.get("message", ""))

        crop_url = inv.get("confirmation_crop_url", "")
        crop_name = os.path.basename(crop_url) if crop_url else ""

        screen_url = inv.get("screenshot_url", "")
        screen_name = os.path.basename(screen_url) if screen_url else ""

        row_data = [
            idx,
            inv.get("file_name", os.path.basename(inv.get("xml_path", ""))),
            mst,
            seller_name,
            ky_hieu,
            so_hd,
            ngay_lap,
            total_val,
            status_text,
            detail_str,
            crop_name,
            screen_name
        ]

        for col_idx, val in enumerate(row_data, 1):
            cell = ws.cell(row=current_row, column=col_idx, value=val)
            cell.font = Font(name="Arial", size=10)
            cell.border = thin_border

            if col_idx in [1, 3, 5, 6, 7]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif col_idx == 8: # Total amount
                cell.alignment = Alignment(horizontal="right", vertical="center")
                if isinstance(val, (int, float)):
                    cell.number_format = '#,##0'
            elif col_idx == 9: # Status
                cell.alignment = Alignment(horizontal="center", vertical="center")
                if "Hợp Lệ" in status_text:
                    cell.fill = verified_fill
                    cell.font = verified_font
                elif "Lỗi" in status_text:
                    cell.fill = error_fill
                    cell.font = error_font
                else:
                    cell.fill = pending_fill
                    cell.font = pending_font
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

        current_row += 1

    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.row in [1, 2, 3]:
                continue
            val_str = str(cell.value or "")
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    ws.column_dimensions["A"].width = 6   # STT
    ws.column_dimensions["B"].width = 28  # File XML
    ws.column_dimensions["C"].width = 16  # MST
    ws.column_dimensions["D"].width = 32  # Tên Người Bán
    ws.column_dimensions["E"].width = 12  # Ký Hiệu
    ws.column_dimensions["F"].width = 12  # Số HD
    ws.column_dimensions["G"].width = 14  # Ngày lập
    ws.column_dimensions["H"].width = 18  # Tổng tiền
    ws.column_dimensions["I"].width = 22  # Trạng thái
    ws.column_dimensions["J"].width = 40  # Chữ ký / chi tiết
    ws.column_dimensions["K"].width = 35  # Bản chụp xác nhận
    ws.column_dimensions["L"].width = 35  # Ảnh toàn cảnh

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output
