import paramiko

# Configuration
HOST = "72.61.47.96"
USER = "sebas024"
KEY_FILE = "vps_key"
REMOTE_PATH = "/home/sebas024/htdocs/srv1274145.hstgr.cloud"

def check_final_status():
    print(f"Connecting to {HOST}...")
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        key = paramiko.RSAKey.from_private_key_file(KEY_FILE)
        client.connect(HOST, username=USER, pkey=key)
        
        print("\n--- Process List (Uvicorn) ---")
        stdin, stdout, stderr = client.exec_command("ps aux | grep uvicorn")
        print(stdout.read().decode().strip())
        
        print("\n--- app.log (Last 20 lines) ---")
        stdin, stdout, stderr = client.exec_command(f"tail -n 20 {REMOTE_PATH}/app.log")
        print(stdout.read().decode().strip())
        
        client.close()
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    check_final_status()
