import paramiko

# Configuration
HOST = "72.61.47.96"
USER = "sebas024"
KEY_FILE = "vps_key"
REMOTE_PATH = "/home/sebas024/htdocs/srv1274145.hstgr.cloud"

def recon():
    print(f"Connecting to {HOST}...")
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        key = paramiko.RSAKey.from_private_key_file(KEY_FILE)
        client.connect(HOST, username=USER, pkey=key)
        
        commands = [
            "uname -a",
            "cat /etc/issue",
            "cat /etc/os-release",
            "ps aux | head -n 10",
            "ls -la",
            "python3 --version"
        ]
        
        for cmd in commands:
            print(f"\n--- {cmd} ---")
            stdin, stdout, stderr = client.exec_command(cmd)
            print(stdout.read().decode().strip())
            
        client.close()
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    recon()
