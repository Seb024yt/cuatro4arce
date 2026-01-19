import paramiko
import time

# Configuration
HOST = "72.61.47.96"
USER = "sebas024"
KEY_FILE = "vps_key"
REMOTE_PATH = "/home/sebas024/htdocs/srv1274145.hstgr.cloud"
REPO_URL = "https://github.com/Seb024yt/cuatro4arce.git"

def deploy():
    print(f"Connecting to {HOST}...")
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Load private key
        key = paramiko.RSAKey.from_private_key_file(KEY_FILE)
        
        client.connect(HOST, username=USER, pkey=key)
        
        print("Connected. Configuring git safety and deploying...")
        
        # Execute commands in groups to better identify failures
        command_groups = [
            # Group 1: Git and project setup
            [
                "git config --global --add safe.directory '*'",
                f"cd {REMOTE_PATH}",
                "git init",
                f"git remote remove origin || true",
                f"git remote add origin {REPO_URL}",
                "git fetch origin",
                "git reset --hard origin/main"
            ],
            # Group 2: Dependencies
            [
                f"cd {REMOTE_PATH}",
                "curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py",
                "python3 get-pip.py --break-system-packages --user",
                "python3 -m pip install -r requirements.txt --break-system-packages --user"
            ],
            # Group 3: Start Application
            [
                f"cd {REMOTE_PATH}",
                "chmod +x start.sh",
                "./start.sh"
            ]
        ]

        for i, commands in enumerate(command_groups, 1):
            print(f"\nExecuting Group {i}...")
            full_command = " && ".join(commands)
            stdin, stdout, stderr = client.exec_command(full_command)
            
            exit_status = stdout.channel.recv_exit_status()
            output = stdout.read().decode().strip()
            error = stderr.read().decode().strip()
            
            if output:
                print(f"OUTPUT Group {i}:\n{output}")
            if error:
                print(f"ERRORS/WARNINGS Group {i}:\n{error}")
                
            if exit_status != 0:
                print(f"Group {i} failed with exit status {exit_status}. Stopping.")
                return

        print("\nDeployment successful! [OK]")
            
        client.close()
        
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    deploy()
