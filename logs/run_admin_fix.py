import paramiko
import time

# Configuration
HOST = "72.61.47.96"
USER = "sebas024"
KEY_FILE = "vps_key"
REMOTE_PATH = "/home/sebas024/htdocs/srv1274145.hstgr.cloud"

def run_fix():
    print(f"Connecting to {HOST}...")
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        key = paramiko.RSAKey.from_private_key_file(KEY_FILE)
        client.connect(HOST, username=USER, pkey=key)
        
        print("Running fix_admin_remote.py...")
        cmd = f"cd {REMOTE_PATH} && export PYTHONPATH=$PYTHONPATH:. && python3 fix_admin_remote.py"
        stdin, stdout, stderr = client.exec_command(cmd)
        
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
    run_fix()
