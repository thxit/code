import subprocess
import sys

if __name__ == '__main__':
    subprocess.run([
        sys.executable,
        'd:\\code\\jiaoyixitong\\webapp\\serve.py'
    ], check=True)