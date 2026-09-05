import subprocess
import time
import socket

# Start server
print("Starting server...")
server_process = subprocess.Popen([
    'd:\\code\\jiaoyixitong\\venv\\Scripts\\python.exe',
    '-c',
    '''
import sys
sys.path.insert(0, "d:/code/jiaoyixitong")
from waitress import serve
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})

serve(app, host="127.0.0.1", port=5000, threads=4)
'''
], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

# Wait for server to start
time.sleep(3)

# Check if server is still running
if server_process.poll() is not None:
    print("Server crashed!")
    output = server_process.communicate()[0]
    print("Server output:", output)
else:
    print("Server appears to be running")
    
    # Test connection
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        result = s.connect_ex(('127.0.0.1', 5000))
        if result == 0:
            print("Port 5000 is open!")
            s.close()
        else:
            print(f"Port 5000 is closed (error: {result})")
    except Exception as e:
        print(f"Connection test failed: {e}")
    
    # Clean up
    server_process.terminate()
    print("Server terminated")