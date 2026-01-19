import paramiko
import time

# Configuration
HOST = "72.61.47.96"
USER = "sebas024"
KEY_FILE = "vps_key"
REMOTE_PATH = "/home/sebas024/htdocs/srv1274145.hstgr.cloud"

def check_status():
    print(f"Connecting to {HOST}...")
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        key = paramiko.RSAKey.from_private_key_file(KEY_FILE)
        client.connect(HOST, username=USER, pkey=key)
        
        print("Connected. Checking application status...")
        
        commands = [
            f"cd {REMOTE_PATH}",
            "echo '--- Process Status ---'",
            "ps aux | grep uvicorn",
            "echo '--- Port 8090 Status ---'",
            "netstat -tuln | grep 8090 || echo 'Port 8090 not open'",
            "echo '--- Last 50 lines of app.log ---'",
            "tail -n 50 app.log",
            "echo '--- Test Local Connection ---'",
            "curl -v http://127.0.0.1:8090/login || echo 'Failed to connect locally'"
        ]
        
        full_command = " && ".join(commands)
        stdin, stdout, stderr = client.exec_command(full_command)
        
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        
        print("\n=== DIAGNOSTIC OUTPUT ===")
        print(output)
        
        if error:
            print("\n=== ERRORS ===")
            print(error)
            
        client.close()
        
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    check_status()
