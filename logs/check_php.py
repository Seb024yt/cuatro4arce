import paramiko

# Configuration
HOST = "72.61.47.96"
USER = "sebas024"
KEY_FILE = "vps_key"
REMOTE_PATH = "/home/sebas024/htdocs/srv1274145.hstgr.cloud"

def check_php():
    print(f"Connecting to {HOST}...")
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        key = paramiko.RSAKey.from_private_key_file(KEY_FILE)
        client.connect(HOST, username=USER, pkey=key)
        
        print("Checking PHP version...")
        client.exec_command(f"cd {REMOTE_PATH}")
        stdin, stdout, stderr = client.exec_command("php -r 'echo phpversion();'")
        print("PHP Version:", stdout.read().decode().strip())
        
        print("Checking Curl version...")
        stdin, stdout, stderr = client.exec_command("curl --version")
        print(stdout.read().decode().strip())
        
        client.close()
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    check_php()
