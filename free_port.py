import os
import socket
import subprocess
import time
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def is_port_free(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a port is free to bind."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind((host, port))
        s.close()
        return True
    except OSError:
        return False

def release_port(port: int = 8000) -> bool:
    """Attempts to release the specified port if it is occupied by an old process."""
    if is_port_free(port):
        return True
    
    print(f"[INFO] Phát hiện cổng {port} đang bị chiếm dụng. Đang giải phóng...")
    try:
        res = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, errors='replace')
        target_pids = set()
        for line in res.stdout.splitlines():
            if f':{port}' in line and ('LISTENING' in line or 'ESTABLISHED' in line):
                parts = line.strip().split()
                if parts:
                    pid_str = parts[-1]
                    if pid_str.isdigit():
                        target_pids.add(int(pid_str))
        
        my_pid = os.getpid()
        my_ppid = os.getppid() if hasattr(os, 'getppid') else None

        for pid_int in target_pids:
            if pid_int != my_pid and pid_int != my_ppid and pid_int > 4:
                try:
                    subprocess.run(['taskkill', '/F', '/PID', str(pid_int)], capture_output=True)
                    print(f"[OK] Đã tắt tiến trình chiếm cổng {port} (PID: {pid_int}).")
                except Exception:
                    pass

        time.sleep(0.8)
        if is_port_free(port):
            return True
    except Exception as e:
        print(f"[CẢNH BÁO] Không thể giải phóng cổng {port}: {e}")

    return is_port_free(port)

def find_available_port(preferred_port: int = 8000, fallback_ports=None) -> int:
    """Finds an available port, attempting to free the preferred port first."""
    if fallback_ports is None:
        fallback_ports = [8000, 8080, 8888, 5000, 8001, 8002, 8005, 8081, 9000]

    # Try preferred first
    if preferred_port not in fallback_ports:
        fallback_ports.insert(0, preferred_port)

    # 1. Try to free preferred port
    if release_port(preferred_port):
        return preferred_port

    # 2. Check each fallback port
    for p in fallback_ports:
        if is_port_free(p):
            return p
        if release_port(p):
            return p

    # 3. Last resort: ask OS for an ephemeral port
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    free_port = s.getsockname()[1]
    s.close()
    return free_port

if __name__ == '__main__':
    port_to_check = 8000
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port_to_check = int(sys.argv[1])
    active_port = find_available_port(port_to_check)
    print(f"[INFO] Cổng khả dụng: {active_port}")
