import paramiko

HOST = "72.61.47.96"
USER = "sebas024"
KEY_FILE = "vps_key"
REMOTE_PATH = "/home/sebas024/htdocs/srv1274145.hstgr.cloud"

def check_socket():
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        key = paramiko.RSAKey.from_private_key_file(KEY_FILE)
        client.connect(HOST, username=USER, pkey=key)
        
        print("Checking for app.sock...")
        stdin, stdout, stderr = client.exec_command(f"ls -l {REMOTE_PATH}/app.sock")
        print(stdout.read().decode().strip())
        print(stderr.read().decode().strip())
        
        client.close()
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    check_socket()
