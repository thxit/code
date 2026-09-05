import subprocess
import time
import urllib.request

# Start full server
print("Starting full application server...")
server_process = subprocess.Popen([
    'd:\\code\\jiaoyixitong\\venv\\Scripts\\python.exe',
    'd:\\code\\jiaoyixitong\\webapp\\serve.py'
], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

# Wait for server to start
time.sleep(5)

# Check if server crashed
if server_process.poll() is not None:
    print("Server crashed!")
    output = server_process.communicate()[0]
    print("Server output:", output)
else:
    print("Server is running")
    
    # Test health API
    try:
        response = urllib.request.urlopen('http://127.0.0.1:5000/api/health', timeout=10)
        data = response.read().decode('utf-8')
        print(f"Health API Response: {data}")
    except Exception as e:
        print(f"Health API request failed: {e}")
    
    # Clean up
    server_process.terminate()
    print("Server terminated")