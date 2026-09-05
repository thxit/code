import subprocess
import time
import sys

print("Starting server...")
process = subprocess.Popen([
    'd:\\code\\jiaoyixitong\\venv\\Scripts\\python.exe',
    'd:\\code\\jiaoyixitong\\webapp\\serve.py'
], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

time.sleep(3)

if process.poll() is not None:
    print("Server crashed!")
    stdout, stderr = process.communicate()
    print("STDOUT:", stdout)
    print("STDERR:", stderr)
else:
    print("Server is running")
    process.terminate()
    print("Server terminated")