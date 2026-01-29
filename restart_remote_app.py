import paramiko
import time

HOST = "72.61.47.96"
USER = "sebas024"
KEY_FILE = "vps_key"
REMOTE_PATH = "/home/sebas024/htdocs/srv1274145.hstgr.cloud"

def restart_app():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        key = paramiko.RSAKey.from_private_key_file(KEY_FILE)
        client.connect(HOST, username=USER, pkey=key)
        
        print("--- Restarting Application ---")
        command = f"cd {REMOTE_PATH} && bash start.sh"
        
        print(f"Executing: {command}")
        stdin, stdout, stderr = client.exec_command(command)
        
        print("Output:", stdout.read().decode())
        print("Errors:", stderr.read().decode())
        
        print("--- Verifying Process ---")
        time.sleep(2)
        stdin, stdout, stderr = client.exec_command("ps aux | grep uvicorn")
        print(stdout.read().decode())

    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    restart_app()
