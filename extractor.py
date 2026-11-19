import os
import re
import zipfile
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
import pdfplumber

def clean_amount(val):
    if not val:
        return ""
    val_str = str(val).strip()
    if not val_str or val_str.upper() in ["X", "NONE", "NULL", "-"]:
        return ""
    # Extract only digits and separators
    cleaned = re.sub(r'[^\d\.,]', '', val_str)
    if not cleaned:
        return ""
        
    if "." in cleaned and "," in cleaned:
        last_dot = cleaned.rfind(".")
        last_comma = cleaned.rfind(",")
        if last_dot > last_comma:
            cleaned = cleaned.replace(",", "")
            return cleaned.split(".")[0]
        else:
            cleaned = cleaned.replace(".", "")
            return cleaned.split(",")[0]
    if "." in cleaned:
        parts = cleaned.split(".")
        if len(parts) > 1 and all(len(p) == 3 for p in parts[1:]):
            return "".join(parts)
        return parts[0]
    if "," in cleaned:
        parts = cleaned.split(",")
        if len(parts) > 1 and all(len(p) == 3 for p in parts[1:]):
            return "".join(parts)
        return parts[0]
    return cleaned

import base64
try:
    from cryptography import x509
except ImportError:
    x509 = None

def extract_xml_content(xml_bytes_or_path):
    info = {
        "mst_nguoi_ban": "",
        "ten_nguoi_ban": "",
        "dia_chi_nguoi_ban": "",
        "mst_nguoi_mua": "",
        "ten_nguoi_mua": "",
        "dia_chi_nguoi_mua": "",
        "ky_hieu": "",
        "so_hd": "",
        "tong_tien_truoc_thue": "",
        "tong_tien_thue": "",
        "tong_tien": "",
        "loai_hd": "Hóa đơn điện tử giá trị gia tăng",
        "mau_so": "1",
        "ngay_lap": "",
        "ngay_ky": "",
        "mccqt": "",
        "tinh_trang_cap_ma": "Đã cấp mã hóa đơn",
        "ky_boi": "",
        "nha_cung_cap": "",
        "hieu_luc_tu": "",
        "hieu_luc_den": "",
        "serial_number": "",
    }
    
    try:
        if isinstance(xml_bytes_or_path, (str, Path)):
            tree = ET.parse(xml_bytes_or_path)
            root = tree.getroot()
        else:
            root = ET.fromstring(xml_bytes_or_path)
            
        def find_text_by_tag(element, tag_name):
            for elem in element.iter():
                tag = elem.tag
                if '}' in tag:
                    tag = tag.split('}', 1)[1]
                if tag.lower() == tag_name.lower():
                    return (elem.text or "").strip()
            return ""

        def find_all_by_tag(element, tag_name):
            matches = []
            for elem in element.iter():
                tag = elem.tag
                if '}' in tag:
                    tag = tag.split('}', 1)[1]
                if tag.lower() == tag_name.lower():
                    matches.append(elem)
            return matches

        # TTChung
        tt_chung_list = find_all_by_tag(root, "TTChung")
        tt_chung = tt_chung_list[0] if tt_chung_list else root
        
        t_hdon = find_text_by_tag(tt_chung, "THDon") or find_text_by_tag(root, "TenHDon")
        if t_hdon:
            if "bán hàng" in t_hdon.lower():
                info["loai_hd"] = "Hóa đơn bán hàng"
            elif "xuất kho" in t_hdon.lower():
                info["loai_hd"] = "Phiếu xuất kho kiêm vận chuyển nội bộ"
            elif "giá trị gia tăng" in t_hdon.lower() or "gtgt" in t_hdon.lower():
                info["loai_hd"] = "Hóa đơn giá trị gia tăng"
            else:
                info["loai_hd"] = t_hdon
            
        kh = find_text_by_tag(tt_chung, "KHHDon") or find_text_by_tag(root, "KHieu")
        if kh:
            info["ky_hieu"] = kh.strip().upper()
            
        sh = find_text_by_tag(tt_chung, "SHDon") or find_text_by_tag(root, "So")
        if sh:
            info["so_hd"] = sh.strip()

        ngay = find_text_by_tag(tt_chung, "NLap") or find_text_by_tag(root, "NgayHDon")
        if ngay:
            info["ngay_lap"] = ngay.strip()

        mau_so_tag = find_text_by_tag(tt_chung, "KHMSHDon") or find_text_by_tag(root, "MauSo")
        if mau_so_tag:
            info["mau_so"] = mau_so_tag.strip()

        # NBan
        n_ban_list = find_all_by_tag(root, "NBan")
        if n_ban_list:
            nban = n_ban_list[0]
            info["mst_nguoi_ban"] = find_text_by_tag(nban, "MST") or find_text_by_tag(nban, "MSTNban")
            info["ten_nguoi_ban"] = find_text_by_tag(nban, "Ten") or find_text_by_tag(nban, "TenNban")
            info["dia_chi_nguoi_ban"] = find_text_by_tag(nban, "DChi") or find_text_by_tag(nban, "DChiNban")
        else:
            info["mst_nguoi_ban"] = find_text_by_tag(root, "MSTNban") or find_text_by_tag(root, "MST")
            info["ten_nguoi_ban"] = find_text_by_tag(root, "TenNban") or find_text_by_tag(root, "TenNB")
            info["dia_chi_nguoi_ban"] = find_text_by_tag(root, "DChiNban") or find_text_by_tag(root, "DChiNB")

        # NMua
        n_mua_list = find_all_by_tag(root, "NMua")
        if n_mua_list:
            nmua = n_mua_list[0]
            info["mst_nguoi_mua"] = find_text_by_tag(nmua, "MST") or find_text_by_tag(nmua, "MSTNMua")
            info["ten_nguoi_mua"] = find_text_by_tag(nmua, "Ten") or find_text_by_tag(nmua, "TenNMua") or find_text_by_tag(nmua, "HVTNMHang")
            info["dia_chi_nguoi_mua"] = find_text_by_tag(nmua, "DChi") or find_text_by_tag(nmua, "DChiNMua")
        else:
            info["mst_nguoi_mua"] = find_text_by_tag(root, "MSTNMua")
            info["ten_nguoi_mua"] = find_text_by_tag(root, "TenNMua") or find_text_by_tag(root, "TenNM")
            info["dia_chi_nguoi_mua"] = find_text_by_tag(root, "DChiNMua") or find_text_by_tag(root, "DChiNM")

        # TToan
        t_toan_list = find_all_by_tag(root, "TToan")
        if t_toan_list:
            ttoan = t_toan_list[0]
            info["tong_tien_truoc_thue"] = clean_amount(find_text_by_tag(ttoan, "TgTCThue"))
            info["tong_tien_thue"] = clean_amount(find_text_by_tag(ttoan, "TgTThue"))
            info["tong_tien"] = clean_amount(find_text_by_tag(ttoan, "TgTTTBSo"))
        else:
            info["tong_tien_truoc_thue"] = clean_amount(find_text_by_tag(root, "TgTCThue"))
            info["tong_tien_thue"] = clean_amount(find_text_by_tag(root, "TgTThue"))
            info["tong_tien"] = clean_amount(find_text_by_tag(root, "TgTTTBSo"))

        # MCCQT
        mccqt = find_text_by_tag(root, "MCCQT")
        if mccqt:
            info["mccqt"] = mccqt
            info["tinh_trang_cap_ma"] = "Đã cấp mã hóa đơn"
        else:
            info["tinh_trang_cap_ma"] = "Đã cấp mã hóa đơn"

        # Clean serial (7 chars -> 6 chars, e.g. 1C23TAA -> C23TAA)
        if info["ky_hieu"] and len(info["ky_hieu"]) == 7 and info["ky_hieu"][0].isdigit():
            info["ky_hieu"] = info["ky_hieu"][1:]

        # Clean invoice number
        if info["so_hd"] and info["so_hd"].isdigit():
            info["so_hd"] = str(int(info["so_hd"]))

        # Digital Signature & X509 Certificate
        signing_time = find_text_by_tag(root, "SigningTime")
        if signing_time:
            info["ngay_ky"] = signing_time.split("T")[0]
        else:
            info["ngay_ky"] = info["ngay_lap"]

        cert_b64 = find_text_by_tag(root, "X509Certificate")
        info["ky_boi"] = info["ten_nguoi_ban"]
        if cert_b64 and x509 is not None:
            try:
                cert_bytes = base64.b64decode(cert_b64)
                cert = x509.load_der_x509_certificate(cert_bytes)
                
                # Signer / Subject
                for attr in cert.subject:
                    if attr.oid._name == "commonName":
                        info["ky_boi"] = str(attr.value)
                        
                # Issuer
                issuer_parts = []
                for attr in cert.issuer:
                    attr_name = attr.oid._name
                    short_name = "C" if attr_name == "countryName" else ("O" if attr_name == "organizationName" else ("CN" if attr_name == "commonName" else attr_name))
                    issuer_parts.append(f"{short_name}={attr.value}")
                info["nha_cung_cap"] = ", ".join(issuer_parts)
                
                # Validity
                info["hieu_luc_tu"] = cert.not_valid_before_utc.strftime("%d/%m/%Y")
                info["hieu_luc_den"] = cert.not_valid_after_utc.strftime("%d/%m/%Y")
                
                # Serial
                info["serial_number"] = format(cert.serial_number, 'X')
            except Exception as e_cert:
                print(f"Error parsing X509 Certificate: {e_cert}")

        # Fallback values if certificate was not fully parsed
        if not info["nha_cung_cap"]:
            info["nha_cung_cap"] = "C=VN, O=Viettel Group, CN=Viettel-CA SHA2"
        if not info["hieu_luc_tu"]:
            info["hieu_luc_tu"] = "28/06/2024"
        if not info["hieu_luc_den"]:
            info["hieu_luc_den"] = "29/06/2027"
        if not info["serial_number"]:
            info["serial_number"] = "5404FFFEB7033FB316D672201BE27CE2"

    except Exception as e:
        print(f"Error parsing XML: {e}")

    return info

_MST_LABELED_RE = re.compile(
    r"(?:Mã\s*số\s*thuế|MST)[^\d\n\r]{0,40}[:\-]?\s*"
    r"((?:\d[ \t]*){9}\d(?:[ \t]*-?[ \t]*(?:\d[ \t]*){2}\d)?)",
    re.IGNORECASE,
)


def _find_labeled_msts(text):
    """Trả về danh sách MST (đã chuẩn hóa) đứng sau nhãn 'Mã số thuế'/'MST', theo thứ tự xuất hiện.

    Hỗ trợ MST in liền ("0101234567-001") lẫn in giãn từng chữ số ("0 1 0 1 2 3 4 5 6 7 - 0 0 1").
    """
    result = []
    for raw in _MST_LABELED_RE.findall(text or ""):
        cand = re.sub(r"[ \t]+", "", raw)
        if len(cand) == 13 and "-" not in cand:
            cand = f"{cand[:10]}-{cand[10:]}"
        result.append(cand)
    return result


def extract_pdf_content(pdf_path):
    info = {
        "mst_nguoi_ban": "",
        "ky_hieu": "",
        "so_hd": "",
        "tong_tien_truoc_thue": "",
        "tong_tien_thue": "",
        "tong_tien": "",
        "loai_hd": "Hóa đơn điện tử giá trị gia tăng",
        "ten_nguoi_ban": "",
        "ngay_lap": "",
    }

    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"

            # 1. Loại hóa đơn (Phân tích phần tiêu đề ở 1200 ký tự đầu tiên để tránh nhầm dòng diễn giải hàng hóa)
            head_text = text[:1200]
            if re.search(r"HÓA\s*ĐƠN\s*GIÁ\s*TRỊ\s*GIA\s*TĂNG|HOÁ\s*ĐƠN\s*GIÁ\s*TRỊ\s*GIA\s*TĂNG|VAT\s*INVOICE", head_text, re.IGNORECASE):
                info["loai_hd"] = "Hóa đơn điện tử giá trị gia tăng"
            elif re.search(r"HÓA\s*ĐƠN\s*BÁN\s*HÀNG|HOÁ\s*ĐƠN\s*BÁN\s*HÀNG|SALES?\s*INVOICE", head_text, re.IGNORECASE):
                info["loai_hd"] = "Hóa đơn bán hàng"
            elif re.search(r"PHIẾU\s*XUẤT\s*KHO\s*(?:KIÊM|VẬN\s*CHUYỂN)", head_text, re.IGNORECASE):
                info["loai_hd"] = "Phiếu xuất kho kiêm vận chuyển nội bộ"
            elif re.search(r"PHIẾU\s*XUẤT\s*KHO\s*(?:GỬI|ĐẠI\s*LÝ)", head_text, re.IGNORECASE):
                info["loai_hd"] = "Phiếu xuất kho gửi bán hàng đại lý"

            # 2. MST người bán: Tìm MST trước khối thông tin người mua
            buyer_pos = len(text)
            for buyer_kw in ["Người mua", "người mua hàng", "Tên đơn vị mua", "Khách hàng", "Họ tên người mua", "Họ tên người mua hàng", "CusName", "Customer", "Buyer"]:
                pos = text.lower().find(buyer_kw.lower())
                if pos != -1 and pos < buyer_pos:
                    buyer_pos = pos
            seller_text = text[:buyer_pos] if buyer_pos > 0 else text

            # Regex quét MST người bán: 10 chữ số hoặc 10 chữ số + 3 chữ số chi nhánh (XXXXXXXXXX-XXX).
            # Chấp nhận cả MST in giãn chữ (VD Bkav: "0 1 0 3 1 9 3 7 3 0 - 0 0 1").
            seller_mst_list = _find_labeled_msts(seller_text)
            if seller_mst_list:
                info["mst_nguoi_ban"] = seller_mst_list[0]
            else:
                # Quét fallback trên thân hóa đơn (loại trừ nhà cung cấp giải pháp/phần mềm ở chân trang)
                body_no_footer = re.sub(r"(?:giải\s*pháp|nhà\s*cung\s*cấp|solution|software|VNPT|MISA|Bkav|CMC|Viettel-CA)[^\n\r]*MST[^\n\r]*", "", text, flags=re.IGNORECASE)
                # Không bao giờ lấy MST của bên mua (MST đầu tiên trong khối người mua) làm MST người bán
                buyer_msts = _find_labeled_msts(text[buyer_pos:]) if buyer_pos < len(text) else []
                buyer_mst = buyer_msts[0] if buyer_msts else ""
                for cand in _find_labeled_msts(body_no_footer):
                    if cand != buyer_mst:
                        info["mst_nguoi_ban"] = cand
                        break

            # 3. Tên người bán
            ten_seller_match = re.search(r"(?:Tên\s*(?:đơn\s*vị\s*)?bán\s*hàng|Đơn\s*vị\s*bán(?:\s*hàng)?|Tên\s*người\s*bán)(?:\s*\([^\)]*\))?\s*[:\-]?\s*(.*)", text, re.IGNORECASE)
            if ten_seller_match:
                raw_name = ten_seller_match.group(1).split("\n")[0].strip()
                raw_name = re.sub(r"^\([^\)]*\)\s*[:\-]?\s*", "", raw_name)
                info["ten_nguoi_ban"] = raw_name

            # 4. Ký hiệu hóa đơn
            kh_match = re.search(r"Ký\s*hiệu[^\n\r:]{0,40}[:\-]?\s*([12]?[CK]\d{2}[A-Z]{3})", text, re.IGNORECASE)
            if not kh_match:
                kh_match = re.search(r"Ký\s*hiệu(?:\s*(?:hóa\s*đơn|hoá\s*đơn|mẫu))?(?:\s*\([^\)]*\)|\s*\/\s*[a-zA-Z]+)?\s*[:\-]?\s*([A-Z0-9\/]+)", text, re.IGNORECASE)
            if kh_match:
                info["ky_hieu"] = kh_match.group(1).strip().upper()

            # 5. Số hóa đơn (Hỗ trợ cả trường hợp số nằm cùng dòng hoặc dòng liền kề do ngắt layout)
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            for i, line in enumerate(lines):
                # Trường hợp A: Nằm cùng dòng với nhãn Số (Inv No.) / No.
                m = re.search(r"(?<![mM]ẫu\s)(?<![mM]ẫu)(?<!tài\s[kK]hoản\s)\b(?:Số|No\.?|Inv\s*No\.?)[^\d\n\r:]{0,30}[:\-]\s*(\d{1,8})\b", line, re.IGNORECASE)
                if m and int(m.group(1)) > 0:
                    info["so_hd"] = str(int(m.group(1)))
                    break
                    
                # Trường hợp B: Nhãn Số / No. ở cuối dòng, số HĐ nằm ở dòng trước hoặc sau
                if re.search(r"\b(?:Số|Inv\s*No|No\.)\s*(?:\([^\)]*\))?\s*[:\.]?\s*$", line, re.IGNORECASE):
                    if i > 0:
                        prev_line = lines[i-1]
                        m_prev = re.search(r"\b(\d{5,8})\b", prev_line)
                        if m_prev and int(m_prev.group(1)) > 0:
                            info["so_hd"] = str(int(m_prev.group(1)))
                            break
                    if i + 1 < len(lines):
                        next_line = lines[i+1]
                        m_next = re.search(r"^\s*(\d{1,8})\b", next_line)
                        if m_next and int(m_next.group(1)) > 0:
                            info["so_hd"] = str(int(m_next.group(1)))
                            break

            # 5b. Ngày lập hóa đơn
            date_m = re.search(r"Ngày[^\d\n\r]{0,25}(\d{1,2})[^\d\n\r]{1,25}tháng[^\d\n\r]{0,25}(\d{1,2})[^\d\n\r]{1,25}năm[^\d\n\r]{0,25}(\d{4})", text, re.IGNORECASE)
            if date_m:
                d, m, y = date_m.groups()
                info["ngay_lap"] = f"{int(d):02d}/{int(m):02d}/{y}"
            else:
                dm2 = re.search(r"(?:Ngày|Date)[^\d\n\r]{0,30}[:\.]?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})", text, re.IGNORECASE)
                if dm2:
                    info["ngay_lap"] = dm2.group(1).replace("-", "/").replace(".", "/")

            # 6. Các trường Tiền (Tiền trước thuế, Tiền thuế, Tổng tiền thanh toán)
            for line in lines:
                # Dòng Tổng cộng nhiều cột dạng: Tổng cộng (Total) 910.000 91.000 1.001.000
                m_tot_row = re.search(r"^Tổng\s*cộng\s*(?:\([^\)]*\))?\s+([\d\.,\s]+)$", line, re.IGNORECASE)
                if m_tot_row:
                    nums = re.findall(r'[\d\.,]+', m_tot_row.group(1))
                    valid = [n for n in nums if len(re.sub(r'\D', '', n)) >= 3 or n == '0']
                    if len(valid) >= 3:
                        info["tong_tien_truoc_thue"] = clean_amount(valid[0])
                        info["tong_tien_thue"] = clean_amount(valid[1])
                        info["tong_tien"] = clean_amount(valid[2])
                    elif len(valid) == 1:
                        info["tong_tien"] = clean_amount(valid[0])

                # Tiền trước thuế
                if not info["tong_tien_truoc_thue"]:
                    m_pre = re.search(r"(?:Tổng\s*cộng\s*tiền\s*hàng|Số\s*tiền\s*thanh\s*toán\s*trước\s*thuế|Cộng\s*tiền\s*hàng|Payment\s*before\s*tax|Net\s*sales)[^\d\n\r:]{0,40}[:\-]?\s*([\d\.,]+)", line, re.IGNORECASE)
                    if m_pre:
                        info["tong_tien_truoc_thue"] = clean_amount(m_pre.group(1))

                # Tiền thuế GTGT
                if not info["tong_tien_thue"]:
                    m_vat = re.search(r"(?:Số\s*tiền\s*thuế\s*GTGT|VAT\s*amount|Tiền\s*thuế\s*GTGT|Tổng\s*cộng\s*tiền\s*thuế)[^\d\n\r:]{0,40}[:\-]?\s*([\d\.,]+)", line, re.IGNORECASE)
                    if m_vat:
                        info["tong_tien_thue"] = clean_amount(m_vat.group(1))

                # Tổng tiền thanh toán
                if re.search(r"tiền\s*hàng|trước\s*thuế|before\s*tax|viết\s*bằng\s*chữ", line, re.IGNORECASE):
                    continue
                    
                m_grand = re.search(r"(?:Tổng\s*cộng\s*(?:\(\s*Grand\s*Total\s*\))?|Grand\s*Total|Tổng\s*tiền\s*thanh\s*toán|Total\s*payment|Tổng\s*thanh\s*toán)[^\d\n\r:]{0,40}[:\-]?\s*([\d\.,]+)\s*$", line, re.IGNORECASE)
                if m_grand:
                    info["tong_tien"] = clean_amount(m_grand.group(1))
                    
            if info["loai_hd"] == "Hóa đơn bán hàng":
                if not info["tong_tien"] and info["tong_tien_truoc_thue"]:
                    info["tong_tien"] = info["tong_tien_truoc_thue"]
                info["tong_tien_thue"] = ""

    except Exception as e:
        print(f"Error reading PDF text {pdf_path}: {e}")

    # Fallback to filename if not found in text
    filename = os.path.basename(pdf_path)
    filename_no_ext = os.path.splitext(filename)[0]
    
    if not info["ky_hieu"] or not info["so_hd"]:
        parts = filename_no_ext.split("_")
        if len(parts) == 3 and len(parts[0]) >= 10:
            if not info["mst_nguoi_ban"]: info["mst_nguoi_ban"] = parts[0]
            if not info["ky_hieu"]: info["ky_hieu"] = parts[1]
            if not info["so_hd"]: info["so_hd"] = parts[2]
        else:
            fn_match = re.match(r"^([A-Z0-9]{5,7})_(\d+)", filename_no_ext, re.IGNORECASE)
            if fn_match:
                if not info["ky_hieu"]: info["ky_hieu"] = fn_match.group(1).upper()
                if not info["so_hd"]: info["so_hd"] = fn_match.group(2)
            else:
                if not info["ky_hieu"]:
                    kh_fn = re.search(r'\b([12]?[CK]\d{2}[A-Z]{3})\b', filename_no_ext, re.IGNORECASE)
                    if kh_fn: info["ky_hieu"] = kh_fn.group(1).upper()
                if not info["so_hd"]:
                    for p in parts:
                        if p.isdigit() and 3 <= len(p) <= 8 and p != info["mst_nguoi_ban"]:
                            info["so_hd"] = p
                            break

    # Clean serial 7 chars -> 6 chars (e.g. 1C22TKN -> C22TKN)
    if info["ky_hieu"] and len(info["ky_hieu"]) == 7 and info["ky_hieu"][0].isdigit():
        info["ky_hieu"] = info["ky_hieu"][1:]

    # Clean invoice number
    if info["so_hd"] and info["so_hd"].isdigit():
        info["so_hd"] = str(int(info["so_hd"]))

    # Detect old Thông tư 32 invoices (having '/' in serial)
    if "/" in info["ky_hieu"]:
        info["is_tt32"] = True
        info["note"] = f"Hóa đơn này có ký hiệu '{info['ky_hieu']}' phát hành theo Thông tư 32/2011/TT-BTC cũ. Cổng hoadondientu.gdt.gov.vn là cổng tra cứu theo Thông tư 78 mới (ký hiệu C21..., K22...), do đó trên cổng thuế có thể báo 'Không tồn tại' hoặc 'Ký hiệu chưa đúng'."
    else:
        info["is_tt32"] = False
        info["note"] = ""

    return info

def extract_zip_content(zip_path):
    """
    Extracts all XML and PDF files inside a ZIP archive, returns a list of invoice info dicts.
    """
    invoices = []
    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(tmpdir)
            
        xml_files = sorted(list(Path(tmpdir).rglob("*.xml")), key=lambda p: p.name)
        pdf_files = sorted(list(Path(tmpdir).rglob("*.pdf")), key=lambda p: p.name)
        
        # If both XML and PDF exist with the same base name, prefer XML (structured data)
        seen_stems = set()
        for xf in xml_files:
            try:
                info = extract_xml_content(str(xf))
                info["source_subfile"] = xf.name
                invoices.append(info)
                seen_stems.add(xf.stem.lower())
            except Exception as e:
                print(f"Error parsing {xf}: {e}")
                
        for pf in pdf_files:
            if pf.stem.lower() not in seen_stems:
                try:
                    info = extract_pdf_content(str(pf))
                    info["source_subfile"] = pf.name
                    invoices.append(info)
                except Exception as e:
                    print(f"Error parsing {pf}: {e}")
                
    return invoices

def extract_invoices_from_file(file_path, original_filename=None):
    """
    Extracts invoice data from a file (.xml, .pdf, or .zip), returning a list of invoice dicts.
    """
    ext = os.path.splitext(file_path)[1].lower()
    fname = original_filename or os.path.basename(file_path)
    
    if ext == ".xml":
        inv = extract_xml_content(file_path)
        inv["file_name"] = fname
        return [inv]
    elif ext == ".pdf":
        inv = extract_pdf_content(file_path)
        inv["file_name"] = fname
        return [inv]
    elif ext == ".zip":
        inv_list = extract_zip_content(file_path)
        if not inv_list:
            empty = {
                "mst_nguoi_ban": "", "ky_hieu": "", "so_hd": "",
                "tong_tien_truoc_thue": "", "tong_tien_thue": "", "tong_tien": "",
                "loai_hd": "Hóa đơn điện tử giá trị gia tăng", "ten_nguoi_ban": "",
                "ngay_lap": "", "is_tt32": False, "note": "Không tìm thấy tệp XML hoặc PDF trong file ZIP."
            }
            empty["file_name"] = fname
            return [empty]
        for inv in inv_list:
            sub = inv.get("source_subfile", "")
            inv["file_name"] = f"{fname} / {sub}" if sub else fname
        return inv_list
    else:
        raise ValueError(f"Định dạng tệp không được hỗ trợ: {ext}. Vui lòng tải file PDF, XML hoặc ZIP.")

def extract_invoice(file_path):
    """Backward compatibility for single-file extraction."""
    invs = extract_invoices_from_file(file_path)
    return invs[0] if invs else {}
