import paramiko
import time

# Configuration
HOST = "72.61.47.96"
USER = "sebas024"
KEY_FILE = "vps_key"
REMOTE_PATH = "/home/sebas024/htdocs/srv1274145.hstgr.cloud"

def debug_socket():
    print(f"Connecting to {HOST}...")
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        key = paramiko.RSAKey.from_private_key_file(KEY_FILE)
        client.connect(HOST, username=USER, pkey=key)
        
        print("Attempting to run uvicorn with socket manually (timeout 10s)...")
        # Ensure we clean up socket first
        client.exec_command(f"rm {REMOTE_PATH}/app.sock")
        
        cmd = f"cd {REMOTE_PATH} && export PYTHONPATH=$PYTHONPATH:. && python3 -m uvicorn app.main:app --uds app.sock"
        print(f"Executing: {cmd}")
        
        stdin, stdout, stderr = client.exec_command(f"timeout 10s bash -c '{cmd}'")
        
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
    debug_socket()
