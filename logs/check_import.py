import paramiko

# Configuration
HOST = "72.61.47.96"
USER = "sebas024"
KEY_FILE = "vps_key"
REMOTE_PATH = "/home/sebas024/htdocs/srv1274145.hstgr.cloud"

def check_import():
    print(f"Connecting to {HOST}...")
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        key = paramiko.RSAKey.from_private_key_file(KEY_FILE)
        client.connect(HOST, username=USER, pkey=key)
        
        print("Checking import WITHOUT PYTHONPATH...")
        cmd = f"cd {REMOTE_PATH} && python3 -c 'import app.main; print(\"Import success\")'"
        stdin, stdout, stderr = client.exec_command(cmd)
        print("STDOUT:", stdout.read().decode().strip())
        print("STDERR:", stderr.read().decode().strip())

        print("\nChecking import WITH PYTHONPATH...")
        cmd = f"cd {REMOTE_PATH} && export PYTHONPATH=$PYTHONPATH:. && python3 -c 'import app.main; print(\"Import success\")'"
        stdin, stdout, stderr = client.exec_command(cmd)
        print("STDOUT:", stdout.read().decode().strip())
        print("STDERR:", stderr.read().decode().strip())
        
        client.close()
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    check_import()
