import os
import sys
import time
import socket
import urllib.request
import webbrowser
import threading
import subprocess
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent
PORT_FILE = BASE_DIR / "PORT.txt"

def get_configured_port() -> int:
    """Reads configured port from args, PORT.txt, env, or default to 8000."""
    # 1. Command-line argument: --port 8080 or start_app.py 8080
    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--port" and i + 2 <= len(sys.argv) and sys.argv[i + 2].isdigit():
            return int(sys.argv[i + 2])
        if arg.isdigit():
            return int(arg)

    # 2. Environment variable
    env_port = os.environ.get("CHECKHOADON_PORT") or os.environ.get("PORT")
    if env_port and env_port.isdigit():
        return int(env_port)

    # 3. File PORT.txt
    if PORT_FILE.exists():
        try:
            with open(PORT_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content.isdigit():
                    return int(content)
        except Exception:
            pass

    return 8000

def wait_and_open_browser(url: str, max_wait_seconds: int = 20):
    """Wait until HTTP server is responding with 200 OK, then open browser."""
    start_time = time.time()
    opened = False
    
    print(f"[ĐANG CHỜ] Đang kết nối tới máy chủ tại {url}...")
    while time.time() - start_time < max_wait_seconds:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "HealthCheck/1.0"})
            with urllib.request.urlopen(req, timeout=1.0) as response:
                if response.status == 200:
                    print(f"\n================================================================")
                    print(f" [OK] Máy chủ đã khởi động thành công!")
                    print(f" [OK] Địa chỉ truy cập: {url}")
                    print(f"================================================================\n")
                    time.sleep(0.5)
                    webbrowser.open(url)
                    opened = True
                    break
        except Exception:
            time.sleep(0.4)

    if not opened:
        print(f"[CẢNH BÁO] Chưa nhận được phản hồi từ {url} sau {max_wait_seconds}s. Vẫn tiến hành mở trình duyệt...")
        webbrowser.open(url)

def main():
    version_file = BASE_DIR / "VERSION.txt"
    version_str = f"v{version_file.read_text(encoding='utf-8').strip()}" if version_file.exists() else "v1.1"

    print("================================================================")
    print(f"   HỆ THỐNG TRA CỨU HÓA ĐƠN & NNT TỰ ĐỘNG - GDT RPA ({version_str})")
    print("================================================================")
    print()

    # Import free_port logic
    try:
        from free_port import find_available_port, release_port
    except ImportError:
        def find_available_port(p): return p
        def release_port(p): return True

    req_port = get_configured_port()
    active_port = find_available_port(req_port)

    if active_port != req_port:
        print(f"[CHÚ Ý] Cổng {req_port} đang bận/bị chặn. Tự động chuyển sang cổng khả dụng: {active_port}")
    else:
        print(f"[OK] Cổng sử dụng: {active_port}")

    # Save active port to PORT.txt
    try:
        with open(PORT_FILE, "w", encoding="utf-8") as f:
            f.write(str(active_port))
    except Exception:
        pass

    target_url = f"http://127.0.0.1:{active_port}"

    # Start browser waiter thread
    browser_thread = threading.Thread(target=wait_and_open_browser, args=(target_url,), daemon=True)
    browser_thread.start()

    # Locate Python interpreter
    py_exe = sys.executable

    # Run uvicorn
    cmd = [
        py_exe, "-m", "uvicorn", "app:app",
        "--host", "127.0.0.1",
        "--port", str(active_port),
        "--log-level", "info"
    ]

    print(f"[INFO] Đang khởi động Uvicorn Server trên cổng {active_port}...")
    print(f"[INFO] Nhấn Ctrl+C để dừng máy chủ bất cứ lúc nào.")
    print("----------------------------------------------------------------")
    
    try:
        proc = subprocess.Popen(cmd, cwd=str(BASE_DIR))
        proc.wait()
    except KeyboardInterrupt:
        print("\n[INFO] Đang tắt máy chủ...")
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            pass
        print("[OK] Đã tắt máy chủ an toàn.")

if __name__ == "__main__":
    main()
