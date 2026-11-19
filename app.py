# =========================================================================
# Copyright (c) 2026 NDKBVH. All rights reserved.
# Project: Hệ Thống Tra Cứu Hóa Đơn Điện Tử & Người Nộp Thuế Tự Động
# Author: NDKBVH
# =========================================================================

import os
import sys
import re
import json
import uuid
import datetime
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any

# Configure utf-8 stdout/stderr for Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn

from extractor import extract_invoices_from_file, extract_invoice, extract_xml_content
from rpa_engine import run_invoice_lookup, run_xml_lookup
from rpa_nnt import run_taxpayer_lookup
from excel_export import generate_excel_report, generate_nnt_excel_report, generate_xml_excel_report

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
UPLOADS_DIR = STATIC_DIR / "uploads"
SCREENSHOTS_DIR = STATIC_DIR / "screenshots"
DATA_DIR = BASE_DIR / "data"
HISTORY_FILE = DATA_DIR / "history.json"
NNT_HISTORY_FILE = DATA_DIR / "nnt_history.json"
XML_HISTORY_FILE = DATA_DIR / "xml_history.json"

for d in [STATIC_DIR, UPLOADS_DIR, SCREENSHOTS_DIR, DATA_DIR]:
    d.mkdir(parents=True, exist_ok=True)

if not HISTORY_FILE.exists():
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False)

if not NNT_HISTORY_FILE.exists():
    with open(NNT_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False)

if not XML_HISTORY_FILE.exists():
    with open(XML_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False)

app = FastAPI(title="Tra Cứu Hóa Đơn Điện Tử, NNT & Đọc XML RPA")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Store in-memory logs for ongoing RPA jobs
rpa_logs = {}

def get_history() -> List[dict]:
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_history(entry: dict):
    history = get_history()
    history.insert(0, entry)
    history = history[:100]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def get_nnt_history() -> List[dict]:
    try:
        with open(NNT_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_nnt_history(entry: dict):
    history = get_nnt_history()
    history.insert(0, entry)
    history = history[:100]
    with open(NNT_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def get_xml_history() -> List[dict]:
    try:
        with open(XML_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_xml_history(entry: dict):
    history = get_xml_history()
    history.insert(0, entry)
    history = history[:100]
    with open(XML_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

# Models
class LookupRequest(BaseModel):
    mst_nguoi_ban: str
    loai_hd: str = "Hóa đơn điện tử giá trị gia tăng"
    ky_hieu: str
    so_hd: str
    tong_tien_thue: Optional[str] = ""
    tong_tien: Optional[str] = ""
    headless: bool = False
    job_id: Optional[str] = None

class ExportExcelRequest(BaseModel):
    invoices: Optional[List[dict]] = None

class DownloadScreenshotsRequest(BaseModel):
    screenshots: List[str]

class TaxpayerLookupRequest(BaseModel):
    mst: str
    headless: bool = False
    job_id: Optional[str] = None

class NntExportExcelRequest(BaseModel):
    items: Optional[List[dict]] = None
    nnt_list: Optional[List[dict]] = None

class XmlLookupRequest(BaseModel):
    xml_path: str
    invoice_info: Optional[Dict[str, Any]] = None
    headless: bool = False
    job_id: Optional[str] = None

class XmlExportExcelRequest(BaseModel):
    invoices: Optional[List[dict]] = None

class XmlDownloadBatchRequest(BaseModel):
    images: Optional[List[str]] = None
    certificates: Optional[List[str]] = None

@app.get("/", response_class=HTMLResponse)
async def read_root():
    template_path = BASE_DIR / "templates" / "index.html"
    if template_path.exists():
        with open(template_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Trang chủ đang khởi tạo...</h1>")

# =========================================================================
# TAB 1: FORM SEARCH INVOICE API
# =========================================================================
@app.post("/api/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    all_extracted = []
    session_id = uuid.uuid4().hex[:8]
    upload_folder = UPLOADS_DIR / session_id
    upload_folder.mkdir(parents=True, exist_ok=True)

    for file in files:
        filename = file.filename
        ext = os.path.splitext(filename)[1].lower()
        if ext not in [".pdf", ".xml", ".zip"]:
            continue

        file_path = upload_folder / filename
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        try:
            extracted_list = extract_invoices_from_file(str(file_path), original_filename=filename)
            for item in extracted_list:
                item["id"] = f"inv_{uuid.uuid4().hex[:8]}"
                item["status"] = "pending"
                item["status_code"] = ""
                item["saved_path"] = str(file_path.relative_to(BASE_DIR)).replace("\\", "/")
                all_extracted.append(item)
        except Exception as e:
            print(f"Lỗi phân tích {filename}: {e}")
            all_extracted.append({
                "id": f"inv_{uuid.uuid4().hex[:8]}",
                "file_name": filename,
                "mst_nguoi_ban": "",
                "ky_hieu": "",
                "so_hd": "",
                "tong_tien_thue": "",
                "tong_tien": "",
                "loai_hd": "Hóa đơn điện tử giá trị gia tăng",
                "status": "error",
                "note": f"Lỗi bóc tách: {str(e)}"
            })

    if not all_extracted:
        raise HTTPException(status_code=400, detail="Không tìm thấy tệp hóa đơn hợp lệ (.pdf, .xml, .zip).")

    return JSONResponse(content={
        "success": True,
        "count": len(all_extracted),
        "invoices": all_extracted,
        "data": all_extracted[0]
    })

@app.post("/api/lookup")
async def run_lookup(req: LookupRequest):
    job_id = req.job_id or str(uuid.uuid4())
    rpa_logs[job_id] = []

    def log_collector(msg):
        if job_id in rpa_logs:
            rpa_logs[job_id].append(msg)

    invoice_data = {
        "mst_nguoi_ban": req.mst_nguoi_ban.strip(),
        "loai_hd": req.loai_hd.strip(),
        "ky_hieu": req.ky_hieu.strip().upper(),
        "so_hd": req.so_hd.strip(),
        "tong_tien_thue": (req.tong_tien_thue or "").strip(),
        "tong_tien": (req.tong_tien or "").strip(),
    }

    result = await asyncio.to_thread(
        run_invoice_lookup,
        invoice_data=invoice_data,
        headless=req.headless,
        log_callback=log_collector,
        output_dir=str(SCREENSHOTS_DIR)
    )
    result["job_id"] = job_id
    result["logs"] = rpa_logs.get(job_id, [])

    history_entry = {
        "id": job_id,
        "timestamp": result.get("timestamp", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        "mst_nguoi_ban": req.mst_nguoi_ban,
        "ky_hieu": req.ky_hieu,
        "so_hd": req.so_hd,
        "loai_hd": req.loai_hd,
        "tong_tien": req.tong_tien,
        "success": result.get("success", False),
        "status_code": result.get("status_code", ""),
        "message": result.get("message", ""),
        "details": result.get("details", []),
        "screenshot_url": result.get("screenshot_url", ""),
        "screenshot_filename": result.get("screenshot_filename", "")
    }
    save_history(history_entry)

    return JSONResponse(content=result)

@app.get("/api/logs/{job_id}")
async def get_logs(job_id: str):
    return JSONResponse(content={"logs": rpa_logs.get(job_id, [])})

@app.get("/api/history")
async def list_history():
    return JSONResponse(content={"history": get_history()})

@app.delete("/api/history")
async def clear_history():
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False)
    return JSONResponse(content={"success": True, "message": "Đã xóa lịch sử tra cứu."})

@app.post("/api/export-excel")
async def export_excel(req: ExportExcelRequest):
    invoices = req.invoices
    if not invoices:
        invoices = get_history()
    excel_stream = generate_excel_report(invoices)
    filename = f"BangKe_DoiSoat_HoaDon_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    headers = {
        'Content-Disposition': f'attachment; filename="{filename}"'
    }
    return StreamingResponse(
        excel_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers
    )

@app.post("/api/download-batch-screenshots")
async def download_batch_screenshots(req: DownloadScreenshotsRequest):
    import zipfile
    from io import BytesIO
    
    bio = BytesIO()
    with zipfile.ZipFile(bio, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for s_path in req.screenshots:
            fname = os.path.basename(s_path)
            full_path = SCREENSHOTS_DIR / fname
            if full_path.exists():
                zf.write(full_path, arcname=fname)
    
    bio.seek(0)
    filename = f"Anh_XacNhan_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    headers = {
        'Content-Disposition': f'attachment; filename="{filename}"'
    }
    return StreamingResponse(
        bio,
        media_type="application/zip",
        headers=headers
    )

@app.get("/api/download/{filename}")
async def download_screenshot(filename: str):
    file_path = SCREENSHOTS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp ảnh.")
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="image/png"
    )

# =========================================================================
# TAB 2: TAXPAYER (NNT) API
# =========================================================================
@app.post("/api/nnt/upload")
async def upload_nnt_files(files: List[UploadFile] = File(...)):
    session_id = uuid.uuid4().hex[:8]
    upload_folder = UPLOADS_DIR / f"nnt_{session_id}"
    upload_folder.mkdir(parents=True, exist_ok=True)

    mst_map = {}

    for file in files:
        filename = file.filename
        ext = os.path.splitext(filename)[1].lower()
        if ext not in [".pdf", ".xml", ".zip"]:
            continue

        file_path = upload_folder / filename
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        try:
            extracted_list = extract_invoices_from_file(str(file_path), original_filename=filename)
            for inv in extracted_list:
                raw_mst = (inv.get("mst_nguoi_ban") or "").strip()
                clean_mst = re.sub(r'[^0-9\-]', '', raw_mst)
                sub_file = inv.get("file_name", filename)
                seller_name = inv.get("ten_nguoi_ban", "")

                if clean_mst:
                    if clean_mst not in mst_map:
                        mst_map[clean_mst] = {
                            "id": f"nnt_{uuid.uuid4().hex[:8]}",
                            "mst": clean_mst,
                            "ten_nnt": seller_name,
                            "dia_chi": "",
                            "co_quan_thue": "",
                            "trang_thai_mst": "",
                            "file_sources": [sub_file],
                            "status": "pending",
                            "status_code": "",
                            "message": "",
                            "screenshot_url": "",
                            "screenshot_filename": "",
                            "timestamp": ""
                        }
                    else:
                        if sub_file not in mst_map[clean_mst]["file_sources"]:
                            mst_map[clean_mst]["file_sources"].append(sub_file)
                        if not mst_map[clean_mst]["ten_nnt"] and seller_name:
                            mst_map[clean_mst]["ten_nnt"] = seller_name
        except Exception as e:
            print(f"Lỗi phân tích hóa đơn {filename}: {e}")

    items = list(mst_map.values())
    if not items:
        raise HTTPException(status_code=400, detail="Không tìm thấy Mã số thuế người bán hợp lệ từ các tệp hóa đơn tải lên.")

    return JSONResponse(content={
        "success": True,
        "count": len(items),
        "items": items
    })

@app.post("/api/nnt/lookup")
async def lookup_nnt(req: TaxpayerLookupRequest):
    job_id = req.job_id or str(uuid.uuid4())
    rpa_logs[job_id] = []

    def log_collector(msg):
        if job_id in rpa_logs:
            rpa_logs[job_id].append(msg)

    result = await asyncio.to_thread(
        run_taxpayer_lookup,
        mst=req.mst,
        headless=req.headless,
        log_callback=log_collector,
        output_dir=str(SCREENSHOTS_DIR)
    )
    result["job_id"] = job_id
    result["logs"] = rpa_logs.get(job_id, [])

    if result.get("success"):
        save_nnt_history(result)

    return JSONResponse(content=result)

@app.get("/api/nnt/history")
async def list_nnt_history():
    return JSONResponse(content={"success": True, "history": get_nnt_history()})

@app.delete("/api/nnt/history")
async def clear_nnt_history():
    with open(NNT_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False)
    return JSONResponse(content={"success": True, "message": "Đã xóa lịch sử tra cứu NNT."})

@app.post("/api/nnt/export-excel")
async def export_nnt_excel(req: NntExportExcelRequest):
    items = req.items or req.nnt_list or []
    if not items:
        items = get_nnt_history()
    excel_stream = generate_nnt_excel_report(items)
    filename = f"DanhSach_NNT_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    headers = {
        'Content-Disposition': f'attachment; filename="{filename}"'
    }
    return StreamingResponse(
        excel_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers
    )

# =========================================================================
# TAB 3: ĐỌC HÓA ĐƠN XML & BẢN CHỤP PHẦN XÁC NHẬN API
# =========================================================================
@app.post("/api/xml/upload")
async def upload_xml_files(files: List[UploadFile] = File(...)):
    all_xml_items = []
    session_id = uuid.uuid4().hex[:8]
    upload_folder = UPLOADS_DIR / f"xml_{session_id}"
    upload_folder.mkdir(parents=True, exist_ok=True)

    for file in files:
        filename = file.filename
        ext = os.path.splitext(filename)[1].lower()
        if ext not in [".xml", ".zip"]:
            continue

        file_path = upload_folder / filename
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        try:
            extracted_list = extract_invoices_from_file(str(file_path), original_filename=filename)
            for item in extracted_list:
                # Ensure we have actual XML path
                actual_xml_path = item.get("saved_path") or str(file_path)
                if not os.path.isabs(actual_xml_path):
                    actual_xml_path = str(BASE_DIR / actual_xml_path)

                item_id = f"xml_{uuid.uuid4().hex[:8]}"
                all_xml_items.append({
                    "id": item_id,
                    "file_name": item.get("file_name", filename),
                    "xml_path": actual_xml_path,
                    "mst_nguoi_ban": item.get("mst_nguoi_ban", ""),
                    "ten_nguoi_ban": item.get("ten_nguoi_ban", ""),
                    "ky_hieu": item.get("ky_hieu", ""),
                    "so_hd": item.get("so_hd", ""),
                    "ngay_lap": item.get("ngay_lap", ""),
                    "tong_tien": item.get("tong_tien", ""),
                    "loai_hd": item.get("loai_hd", "Hóa đơn điện tử giá trị gia tăng"),
                    "status": "pending",
                    "status_code": "",
                    "message": "",
                    "details": [],
                    "screenshot_url": "",
                    "screenshot_filename": "",
                    "confirmation_crop_url": "",
                    "confirmation_crop_filename": "",
                    "timestamp": ""
                })
        except Exception as e:
            print(f"Lỗi phân tích tệp XML {filename}: {e}")
            all_xml_items.append({
                "id": f"xml_{uuid.uuid4().hex[:8]}",
                "file_name": filename,
                "xml_path": str(file_path),
                "mst_nguoi_ban": "",
                "ten_nguoi_ban": "",
                "ky_hieu": "",
                "so_hd": "",
                "ngay_lap": "",
                "tong_tien": "",
                "loai_hd": "",
                "status": "error",
                "message": f"Lỗi đọc tệp XML: {str(e)}",
                "details": [],
                "screenshot_url": "",
                "confirmation_crop_url": ""
            })

    if not all_xml_items:
        raise HTTPException(status_code=400, detail="Không tìm thấy tệp hóa đơn XML hợp lệ (.xml hoặc .zip).")

    return JSONResponse(content={
        "success": True,
        "count": len(all_xml_items),
        "invoices": all_xml_items
    })

@app.post("/api/xml/lookup")
async def lookup_xml(req: XmlLookupRequest):
    job_id = req.job_id or str(uuid.uuid4())
    rpa_logs[job_id] = []

    def log_collector(msg):
        if job_id in rpa_logs:
            rpa_logs[job_id].append(msg)

    xml_file_path = req.xml_path
    if not os.path.isabs(xml_file_path):
        xml_file_path = str(BASE_DIR / xml_file_path)

    if not os.path.exists(xml_file_path):
        raise HTTPException(status_code=404, detail=f"Không tìm thấy tệp XML trên máy chủ: {xml_file_path}")

    invoice_info = req.invoice_info
    if not invoice_info:
        try:
            invoice_info = extract_xml_content(xml_file_path)
        except Exception:
            invoice_info = {}

    result = await asyncio.to_thread(
        run_xml_lookup,
        xml_file_path=xml_file_path,
        invoice_info=invoice_info,
        headless=req.headless,
        log_callback=log_collector,
        output_dir=str(SCREENSHOTS_DIR)
    )
    result["job_id"] = job_id
    result["logs"] = rpa_logs.get(job_id, [])

    if result.get("success"):
        history_entry = {
            "id": job_id,
            "timestamp": result.get("timestamp", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            "file_name": os.path.basename(xml_file_path),
            "xml_path": str(xml_file_path),
            "mst_nguoi_ban": invoice_info.get("mst_nguoi_ban", ""),
            "ten_nguoi_ban": invoice_info.get("ten_nguoi_ban", ""),
            "ky_hieu": invoice_info.get("ky_hieu", ""),
            "so_hd": invoice_info.get("so_hd", ""),
            "ngay_lap": invoice_info.get("ngay_lap", ""),
            "tong_tien": invoice_info.get("tong_tien", ""),
            "success": True,
            "status_code": result.get("status_code", "VERIFIED"),
            "message": result.get("message", ""),
            "details": result.get("details", []),
            "screenshot_url": result.get("screenshot_url", ""),
            "screenshot_filename": result.get("screenshot_filename", ""),
            "confirmation_crop_url": result.get("confirmation_crop_url", ""),
            "confirmation_crop_filename": result.get("confirmation_crop_filename", "")
        }
        save_xml_history(history_entry)

    return JSONResponse(content=result)

@app.get("/api/xml/history")
async def list_xml_history():
    return JSONResponse(content={"success": True, "history": get_xml_history()})

@app.delete("/api/xml/history")
async def clear_xml_history():
    with open(XML_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False)
    return JSONResponse(content={"success": True, "message": "Đã xóa lịch sử tra cứu XML."})

@app.post("/api/xml/export-excel")
async def export_xml_excel(req: XmlExportExcelRequest):
    invoices = req.invoices
    if not invoices:
        invoices = get_xml_history()
    excel_stream = generate_xml_excel_report(invoices)
    filename = f"BangKe_XacThuc_XML_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    headers = {
        'Content-Disposition': f'attachment; filename="{filename}"'
    }
    return StreamingResponse(
        excel_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers
    )

@app.post("/api/xml/download-batch-certificates")
async def download_batch_certificates(req: XmlDownloadBatchRequest):
    import zipfile
    from io import BytesIO
    
    bio = BytesIO()
    img_list = req.images or req.certificates or []
    with zipfile.ZipFile(bio, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for img_url in img_list:
            fname = os.path.basename(img_url)
            full_path = SCREENSHOTS_DIR / fname
            if full_path.exists():
                zf.write(full_path, arcname=fname)
    
    bio.seek(0)
    filename = f"BanChup_XacNhan_XML_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    headers = {
        'Content-Disposition': f'attachment; filename="{filename}"'
    }
    return StreamingResponse(
        bio,
        media_type="application/zip",
        headers=headers
    )

if __name__ == "__main__":
    target_port = 8000
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        target_port = int(sys.argv[1])
    else:
        port_file = BASE_DIR / "PORT.txt"
        if port_file.exists():
            try:
                with open(port_file, "r", encoding="utf-8") as f:
                    p = f.read().strip()
                    if p.isdigit():
                        target_port = int(p)
            except Exception:
                pass
    uvicorn.run("app:app", host="127.0.0.1", port=target_port, reload=False)
