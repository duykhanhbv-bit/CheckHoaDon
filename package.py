#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Package & Version Bump Automation for CheckHoaDon
Tự động nâng phiên bản và đóng gói trọn bộ ứng dụng thành bộ cài .exe & zip
"""

import os
import sys
import re
import shutil
import zipfile
import subprocess
from pathlib import Path

# Đảm bảo UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent
VERSION_FILE = BASE_DIR / "VERSION.txt"
ISS_FILE = BASE_DIR / "installer_setup.iss"
INDEX_HTML = BASE_DIR / "templates" / "index.html"
LAUNCHER_CS = BASE_DIR / "launcher.cs"
ICON_FILE = BASE_DIR / "app_icon.ico"
CSC_PATH = Path(r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe")

# Danh sách đường dẫn ISCC.exe khả dụng
ISCC_CANDIDATES = [
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Antigravity IDE" / "resources" / "app" / "node_modules" / "innosetup" / "bin" / "ISCC.exe",
    Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
    Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
]

def find_iscc() -> Path:
    """Tìm trình biên dịch Inno Setup (ISCC.exe)."""
    # Kiểm tra trong PATH
    which_iscc = shutil.which("iscc") or shutil.which("ISCC")
    if which_iscc:
        return Path(which_iscc)

    for cand in ISCC_CANDIDATES:
        if cand.exists():
            return cand

    raise FileNotFoundError("Không tìm thấy trình biên dịch Inno Setup (ISCC.exe) trên máy!")

def read_current_version() -> str:
    """Đọc phiên bản hiện tại từ VERSION.txt."""
    if VERSION_FILE.exists():
        v = VERSION_FILE.read_text(encoding="utf-8").strip()
        if v:
            return v
    return "1.0.0"

def bump_version(ver: str, bump_type: str = "minor") -> str:
    """
    Tăng phiên bản theo chuẩn SemVer:
    - bump_type: 'patch' (1.1.0 -> 1.1.1), 'minor' (1.0.0 -> 1.1.0), 'major' (1.0.0 -> 2.0.0)
    """
    parts = re.split(r"[\.-]", ver)
    try:
        major = int(parts[0]) if len(parts) > 0 else 1
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
    except ValueError:
        return ver

    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif bump_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        return f"{major}.{minor + 1}.0"

def get_short_version(ver: str) -> str:
    """Trả về phiên bản ngắn gọn hiển thị (ví dụ: '1.1.0' -> '1.1' hoặc '1.1.2' -> '1.1.2')."""
    parts = ver.split(".")
    if len(parts) == 3 and parts[2] == "0":
        return f"{parts[0]}.{parts[1]}"
    return ver

def update_version_files(full_ver: str, short_ver: str):
    """Cập nhật phiên bản vào tất cả các tệp cấu hình và giao diện."""
    # 1. VERSION.txt
    VERSION_FILE.write_text(full_ver + "\n", encoding="utf-8")
    print(f"  [1/4] Đã ghi {full_ver} vào VERSION.txt")

    # 2. installer_setup.iss
    if ISS_FILE.exists():
        content = ISS_FILE.read_text(encoding="utf-8")
        content = re.sub(r'#define MyAppVersion "[^"]+"', f'#define MyAppVersion "{full_ver}"', content)
        content = re.sub(r'OutputBaseFilename=CheckHoaDon_Setup_v[^\r\n]+', f'OutputBaseFilename=CheckHoaDon_Setup_v{short_ver}', content)
        
        # Đảm bảo các tệp mới luôn có mặt trong [Files]
        required_sources = [
            'Source: "VERSION.txt"; DestDir: "{app}"; Flags: ignoreversion',
            'Source: "screen_capture.py"; DestDir: "{app}"; Flags: ignoreversion',
            'Source: "start_app.py"; DestDir: "{app}"; Flags: ignoreversion',
            'Source: "doi_cong.bat"; DestDir: "{app}"; Flags: ignoreversion',
            'Source: "PORT.txt"; DestDir: "{app}"; Flags: ignoreversion',
        ]
        for src in required_sources:
            tag = src.split(';')[0].strip()
            if tag not in content:
                content = content.replace('[Files]\n', f'[Files]\n{src}\n')

        ISS_FILE.write_text(content, encoding="utf-8")
        print(f"  [2/4] Đã cập nhật installer_setup.iss (AppVersion={full_ver}, Output=CheckHoaDon_Setup_v{short_ver})")

    # 3. templates/index.html
    if INDEX_HTML.exists():
        html_content = INDEX_HTML.read_text(encoding="utf-8")
        badge_pattern = r'(<span id="appVersionBadge"[^>]*>).*?(</span>)'
        new_badge_content = rf'\1<i class="fa-solid fa-code-branch text-[10px]"></i> v{short_ver}\2'
        if re.search(badge_pattern, html_content, flags=re.DOTALL):
            html_content = re.sub(badge_pattern, new_badge_content, html_content, flags=re.DOTALL)
            INDEX_HTML.write_text(html_content, encoding="utf-8")
            print(f"  [3/4] Đã cập nhật huy hiệu phiên bản trên giao diện web: v{short_ver}")

    # 4. app.py
    app_py = BASE_DIR / "app.py"
    if app_py.exists():
        app_text = app_py.read_text(encoding="utf-8")
        if 'APP_VERSION =' in app_text:
            app_text = re.sub(r'APP_VERSION = "[^"]+"', f'APP_VERSION = "{full_ver}"', app_text)
            app_py.write_text(app_text, encoding="utf-8")
            print(f"  [4/4] Đã cập nhật APP_VERSION trong app.py")

def compile_csharp_launcher():
    """Biên dịch launcher.cs thành CheckHoaDon.exe."""
    if not CSC_PATH.exists():
        print(f"  [CẢNH BÁO] Không tìm thấy csc.exe tại {CSC_PATH}. Bỏ qua biên dịch C# launcher.")
        return

    cmd = [
        str(CSC_PATH),
        "/target:exe",
        "/out:CheckHoaDon.exe",
        f"/win32icon:{ICON_FILE.name}",
        "launcher.cs"
    ]
    print(f"  >> Đang biên dịch CheckHoaDon.exe từ launcher.cs...")
    res = subprocess.run(cmd, cwd=str(BASE_DIR), capture_output=True, text=True)
    if res.returncode != 0:
        print(f"  [LỖI] Biên dịch launcher.cs thất bại:\n{res.stderr}\n{res.stdout}")
        sys.exit(1)
    print("  [OK] Đã biên dịch thành công CheckHoaDon.exe")

def compile_inno_setup(iscc_bin: Path, short_ver: str):
    """Chạy ISCC để đóng gói bộ cài đặt."""
    temp_dir = Path(os.environ.get("TEMP", str(Path.home() / "AppData" / "Local" / "Temp"))) / "CheckHoaDon_Build_Dist"
    temp_dir.mkdir(parents=True, exist_ok=True)

    cache_dir = Path.home() / ".cache" / "CheckHoaDon_Build"
    
    # Kiểm tra đồng bộ cache python_env và pw-browsers trên ổ C: để tăng tốc 10x và tránh semaphore timeout
    if not (cache_dir / "python_env").exists() or not (cache_dir / "pw-browsers").exists():
        print("  >> Đang tạo bộ nhớ đệm (Cache) trên ổ SSD cục bộ C: để tối ưu tốc độ...")
        cache_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(["robocopy", str(BASE_DIR / "python_env"), str(cache_dir / "python_env"), "/E", "/MT:16", "/R:2", "/W:1", "/NDL", "/NFL", "/NJH", "/NJS"], shell=True)
        subprocess.run(["robocopy", str(BASE_DIR / "pw-browsers"), str(cache_dir / "pw-browsers"), "/E", "/MT:16", "/R:2", "/W:1", "/NDL", "/NFL", "/NJH", "/NJS"], shell=True)

    setup_filename = f"CheckHoaDon_Setup_v{short_ver}"
    cmd = [
        str(iscc_bin),
        f"/O{str(temp_dir)}",
        f"/F{setup_filename}",
        f"/DCacheDir={str(cache_dir)}",
        "installer_setup.iss"
    ]
    print(f"  >> Đang thực thi Inno Setup đóng gói {setup_filename}.exe qua SSD Cache (vui lòng chờ)...")
    res = subprocess.run(cmd, cwd=str(BASE_DIR))
    if res.returncode != 0:
        print(f"  [LỖI] Inno Setup thoát với mã lỗi: {res.returncode}")
        sys.exit(1)

    # Chuyển file hoàn tất vào thư mục dist
    dist_dir = BASE_DIR / "dist"
    dist_dir.mkdir(exist_ok=True)
    built_exe = temp_dir / f"{setup_filename}.exe"
    target_exe = dist_dir / f"{setup_filename}.exe"
    if built_exe.exists():
        print(f"  >> Đang sao chép {built_exe.name} từ ổ C: vào thư mục dự án dist...")
        shutil.copy2(str(built_exe), str(target_exe))
        try:
            built_exe.unlink()
        except Exception:
            pass

    print("  [OK] Inno Setup đã đóng gói thành công bộ cài!")

def organize_distribution(short_ver: str):
    """Sắp xếp tệp setup vào thư mục dist và tạo file zip phân phối."""
    dist_dir = BASE_DIR / "dist"
    dist_dir.mkdir(exist_ok=True)

    setup_exe_name = f"CheckHoaDon_Setup_v{short_ver}.exe"
    setup_exe_path = dist_dir / setup_exe_name

    if not setup_exe_path.exists():
        # Kiểm tra xem có file nào dạng CheckHoaDon_Setup_*.exe mới tạo không
        exes = sorted(dist_dir.glob("CheckHoaDon_Setup_*.exe"), key=os.path.getmtime, reverse=True)
        if exes:
            setup_exe_path = exes[0]
            setup_exe_name = setup_exe_path.name
        else:
            print(f"  [LỖI] Không tìm thấy file {setup_exe_name} trong thư mục dist!")
            sys.exit(1)

    # Thư mục gói cài đặt
    package_folder_name = f"CheckHoaDon_NhieuHoaDon_Setup_v{short_ver}"
    package_folder = dist_dir / package_folder_name
    package_folder.mkdir(exist_ok=True)

    dest_exe = package_folder / setup_exe_name
    shutil.copy2(str(setup_exe_path), str(dest_exe))
    print(f"  [OK] Đã sao chép vào thư mục phân phối: {dest_exe.relative_to(BASE_DIR)}")

    # Tạo tệp nén ZIP
    zip_name = f"{package_folder_name}.zip"
    zip_path = dist_dir / zip_name
    print(f"  >> Đang tạo tệp nén phân phối: {zip_path.relative_to(BASE_DIR)}...")

    with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(str(dest_exe), arcname=setup_exe_name)

    zip_size_mb = zip_path.stat().st_size / (1024 * 1024)
    exe_size_mb = dest_exe.stat().st_size / (1024 * 1024)
    print(f"  [OK] Đã tạo thành công file ZIP: {zip_name} ({zip_size_mb:.1f} MB)")
    print(f"  [OK] Kích thước file cài đặt: {setup_exe_name} ({exe_size_mb:.1f} MB)")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Đóng gói và nâng phiên bản ứng dụng CheckHoaDon")
    parser.add_argument("--bump", choices=["patch", "minor", "major"], default="minor",
                        help="Loại nâng phiên bản: minor (mặc định: 1.0.0 -> 1.1.0) hoặc patch (1.0.0 -> 1.0.1)")
    parser.add_argument("--set", dest="set_version", type=str, default=None,
                        help="Chỉ định phiên bản cụ thể (ví dụ: 1.1.0)")
    parser.add_argument("--no-bump", action="store_true",
                        help="Không tăng phiên bản, giữ nguyên phiên bản hiện tại")

    args = parser.parse_args()

    print("================================================================")
    print("   QUY TRINH DONG GOI VA NANG PHIEN BAN UNG DUNG CHECKHOADON    ")
    print("================================================================")

    current_ver = read_current_version()
    print(f"[INFO] Phiên bản hiện tại: {current_ver}")

    if args.set_version:
        new_ver = args.set_version
        print(f"[INFO] Nâng phiên bản theo yêu cầu chỉ định: {current_ver} -> {new_ver}")
    elif args.no_bump:
        new_ver = current_ver
        print(f"[INFO] Giữ nguyên phiên bản hiện tại: {new_ver}")
    else:
        new_ver = bump_version(current_ver, args.bump)
        print(f"[INFO] Tự động nâng phiên bản ({args.bump}): {current_ver} -> {new_ver}")

    short_ver = get_short_version(new_ver)
    print(f"[INFO] Tên hiển thị phiên bản: v{short_ver} (Chuẩn: {new_ver})")
    print("----------------------------------------------------------------")

    # 1. Tìm Inno Setup Compiler
    iscc_bin = find_iscc()
    print(f"[1/5] Trình biên dịch Inno Setup: {iscc_bin}")

    # 2. Đồng bộ hóa phiên bản
    print("[2/5] Đang đồng bộ hóa số hiệu phiên bản...")
    update_version_files(new_ver, short_ver)

    # 3. Biên dịch C# Native Launcher
    print("[3/5] Đang biên dịch Launcher CheckHoaDon.exe...")
    compile_csharp_launcher()

    # 4. Biên dịch bộ cài đặt Inno Setup
    print(f"[4/5] Đang đóng gói bộ cài CheckHoaDon_Setup_v{short_ver}.exe...")
    compile_inno_setup(iscc_bin, short_ver)

    # 5. Đóng gói phân phối vào thư mục dist & ZIP
    print("[5/5] Đang tổ chức thư mục phân phối và tạo file ZIP...")
    organize_distribution(short_ver)

    print("================================================================")
    print(f"🎉 ĐÓNG GÓI HOÀN TẤT THÀNH CÔNG CHO PHIÊN BẢN v{short_ver} ({new_ver})!")
    print(f"📁 Thư mục đầu ra:")
    print(f"   - File cài đặt: dist/CheckHoaDon_NhieuHoaDon_Setup_v{short_ver}/CheckHoaDon_Setup_v{short_ver}.exe")
    print(f"   - File nén ZIP: dist/CheckHoaDon_NhieuHoaDon_Setup_v{short_ver}.zip")
    print(f"   - File chạy gốc: CheckHoaDon.exe")
    print("================================================================")

if __name__ == "__main__":
    main()
