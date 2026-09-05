import subprocess
import sys

# Start the server
subprocess.run([
    sys.executable,
    'webapp/serve.py'
], cwd='d:/code/jiaoyixitong', check=True)