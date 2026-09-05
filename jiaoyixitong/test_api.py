import subprocess
import time
import urllib.request

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

# Test API
try:
    response = urllib.request.urlopen('http://127.0.0.1:5000/api/health', timeout=5)
    data = response.read().decode('utf-8')
    print(f"API Response: {data}")
except Exception as e:
    print(f"API request failed: {e}")

# Clean up
server_process.terminate()
print("Server terminated")