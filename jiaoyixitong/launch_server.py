import subprocess
import sys

# Launch server in a new console window
print("启动A股量化交易系统...")
print("服务器将在新窗口中运行")

subprocess.Popen([
    sys.executable,
    'webapp/app_simple.py'
], cwd='d:/code/jiaoyixitong', creationflags=subprocess.CREATE_NEW_CONSOLE)

print("\n服务器已启动，请等待几秒后访问:")
print("http://127.0.0.1:5000")