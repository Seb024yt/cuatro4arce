import paramiko
import time

# Configuration
HOST = "72.61.47.96"
USER = "sebas024"
KEY_FILE = "vps_key"
REMOTE_PATH = "/home/sebas024/htdocs/srv1274145.hstgr.cloud"

def debug_remote():
    print(f"Connecting to {HOST}...")
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        key = paramiko.RSAKey.from_private_key_file(KEY_FILE)
        client.connect(HOST, username=USER, pkey=key)
        
        print("Connected. Checking app.log content...")
        stdin, stdout, stderr = client.exec_command(f"cat {REMOTE_PATH}/app.log")
        print("\nChecking file structure...")
        stdin, stdout, stderr = client.exec_command(f"find {REMOTE_PATH} -maxdepth 3 -not -path '*/.*'")
        print(stdout.read().decode().strip())

        print("\nAttempting to run uvicorn manually...")
        # Force python to add current directory to path explicitly
        cmd = f"cd {REMOTE_PATH} && export PYTHONPATH=$PYTHONPATH:. && python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
        print(f"Executing: {cmd}")
        
        stdin, stdout, stderr = client.exec_command(f"timeout 5s bash -c '{cmd}'")
        
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        
        print("\n--- STDOUT ---")
        print(out)
        print("\n--- STDERR ---")
        print(err)
            
        client.close()
        
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    debug_remote()
