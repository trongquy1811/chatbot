"""
Single-command launcher for Agent Harness Chatbot.
Runs both the FastAPI Backend (port 8000) and Streamlit UI (port 8501).
Usage: python run.py
"""
import os
import subprocess
import sys
import time
import urllib.request


def wait_for_backend(url: str = "http://127.0.0.1:8000/health", timeout: int = 20) -> bool:
    print("⏳ Đang đợi Backend API khởi động...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    print("✅ Backend API đã sẵn sàng tại http://127.0.0.1:8000")
                    return True
        except Exception:
            time.sleep(0.5)
    print("⚠️ Backend API khởi động chậm hơn dự kiến, vẫn tiếp tục mở giao diện...")
    return False


def main():
    print("=" * 60)
    print("🚀 KHỞI ĐỘNG HỆ THỐNG AGENT HARNESS CHATBOT")
    print("=" * 60)

    # Set UTF-8 encoding for standard streams
    os.environ["PYTHONIOENCODING"] = "utf-8"

    api_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
    ]

    ui_cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "app.py",
        "--server.port",
        "8501",
        "--server.address",
        "127.0.0.1",
    ]

    print("▶️ Đang khởi chạy FastAPI Backend (port 8000)...")
    backend_proc = subprocess.Popen(api_cmd)

    try:
        wait_for_backend()

        print("▶️ Đang khởi chạy Streamlit UI (port 8501)...")
        print("\n" + "=" * 60)
        print("🌐 Backend API Docs : http://127.0.0.1:8000/docs")
        print("💻 Streamlit UI      : http://127.0.0.1:8501")
        print("🔑 Demo Access Token : sec_tok_0123456789abcdef0123456789")
        print("=" * 60)
        print("Nhấn CTRL+C để dừng toàn bộ hệ thống.\n")

        ui_proc = subprocess.Popen(ui_cmd)
        ui_proc.wait()

    except KeyboardInterrupt:
        print("\n🛑 Đang dừng hệ thống...")
    finally:
        try:
            backend_proc.terminate()
            backend_proc.wait(timeout=3)
        except Exception:
            backend_proc.kill()
        print("👋 Đã dừng tất cả dịch vụ thành công.")


if __name__ == "__main__":
    main()
