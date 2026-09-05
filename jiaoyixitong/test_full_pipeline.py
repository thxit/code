import subprocess
import time
import urllib.request
import json
import sys
import os

# Start server
print("Starting full application server...")
server_process = subprocess.Popen([
    'd:\\code\\jiaoyixitong\\venv\\Scripts\\python.exe',
    'd:\\code\\jiaoyixitong\\webapp\\app_simple.py'
], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd='d:\\code\\jiaoyixitong')

# Wait for server to start
print("Waiting 8 seconds for server to start...")
time.sleep(8)

# Check if server crashed
if server_process.poll() is not None:
    print("Server crashed!")
    output = server_process.communicate(timeout=30)[0]
    print("Server output:", output[:5000])
    sys.exit(1)
else:
    print("Server is running")
    
    # Test health API
    print("\n--- Testing /api/health ---")
    try:
        response = urllib.request.urlopen('http://127.0.0.1:5000/api/health', timeout=15)
        data = json.loads(response.read().decode('utf-8'))
        print(f"Response: {data}")
    except Exception as e:
        print(f"Failed: {e}")
    
    # Test quick API
    print("\n--- Testing /api/quick ---")
    try:
        print("This may take a few seconds...")
        response = urllib.request.urlopen('http://127.0.0.1:5000/api/quick', timeout=60)
        data = json.loads(response.read().decode('utf-8'))
        if 'error' in data:
            print(f"Error: {data['error']}")
            if 'traceback' in data:
                print(f"Traceback:\n{data['traceback']}")
        else:
            print(f"Success! Keys returned: {list(data.keys())}")
            if 'meta' in data:
                print(f"Analysis Time: {data['meta'].get('analysis_time', 'N/A')}")
            if 'market_trend' in data:
                print(f"Market Trend Summary: {data['market_trend'].get('summary', 'N/A')}")
            if 'trading_signal' in data:
                print(f"Trading Signal: {data['trading_signal'].get('action', 'N/A')} (Score: {data['trading_signal'].get('score', 'N/A')})")
            if 'sentiment' in data:
                print(f"Sentiment Data: {'Available' if data['sentiment'] else 'Not available'}")
            if 'capital_flow' in data:
                print(f"Capital Flow Data: {'Available' if data['capital_flow'] else 'Not available'}")
    except Exception as e:
        print(f"Failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Clean up
    server_process.terminate()
    print("\nServer terminated")