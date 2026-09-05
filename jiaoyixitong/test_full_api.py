import subprocess
import time
import urllib.request
import json

# Start server
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
    print("\n--- Testing /api/health ---")
    try:
        response = urllib.request.urlopen('http://127.0.0.1:5000/api/health', timeout=10)
        data = json.loads(response.read().decode('utf-8'))
        print(f"Response: {data}")
    except Exception as e:
        print(f"Failed: {e}")
    
    # Test quick API
    print("\n--- Testing /api/quick ---")
    try:
        response = urllib.request.urlopen('http://127.0.0.1:5000/api/quick', timeout=30)
        data = json.loads(response.read().decode('utf-8'))
        if 'error' in data:
            print(f"Error: {data['error']}")
        else:
            print(f"Success - Keys: {list(data.keys())}")
            if 'market_trend' in data:
                print(f"Market Trend Summary: {data['market_trend'].get('summary', 'N/A')}")
            if 'trading_signal' in data:
                print(f"Trading Signal: {data['trading_signal'].get('action', 'N/A')}")
    except Exception as e:
        print(f"Failed: {e}")
    
    # Clean up
    server_process.terminate()
    print("\nServer terminated")