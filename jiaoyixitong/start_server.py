#!/usr/bin/env python
import subprocess
import sys
import time

def main():
    print("正在启动A股量化交易系统...")
    
    # Start the Flask server
    server_process = subprocess.Popen([
        sys.executable,
        'webapp/app_simple.py'
    ], cwd='d:/code/jiaoyixitong')
    
    print("服务器已启动，PID:", server_process.pid)
    print("请访问 http://127.0.0.1:5000 查看系统")
    
    # Keep the script running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在关闭服务器...")
        server_process.terminate()
        server_process.wait()
        print("服务器已关闭")

if __name__ == '__main__':
    main()