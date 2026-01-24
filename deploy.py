import paramiko
import time
import os

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
        
        print("Connected. Uploading files and deploying...")
        
        sftp = client.open_sftp()
        
        # Upload requirements
        sftp.put("requirements.txt", f"{REMOTE_PATH}/requirements.txt")
        print("Uploaded requirements.txt")
        
        # Upload app directory
        local_app_dir = os.path.join(os.getcwd(), "app")
        remote_app_dir = f"{REMOTE_PATH}/app"
        
        # Ensure remote app dir exists
        try:
            sftp.mkdir(remote_app_dir)
        except:
            pass
            
        # Recursive upload
        for root, dirs, files in os.walk(local_app_dir):
            relative_path = os.path.relpath(root, local_app_dir)
            if relative_path == ".":
                remote_root = remote_app_dir
            else:
                remote_root = f"{remote_app_dir}/{relative_path}".replace("\\", "/")
                try:
                    sftp.mkdir(remote_root)
                except:
                    pass
            
            for file in files:
                if file.endswith(".pyc") or file.startswith("__"):
                    continue
                local_file = os.path.join(root, file)
                remote_file = f"{remote_root}/{file}"
                print(f"Uploading {file}...")
                sftp.put(local_file, remote_file)
                
        # Upload start script
        sftp.put("start.sh", f"{REMOTE_PATH}/start.sh")
        
        # Upload test script
        try:
            sftp.put("test_sii_remote_exec.py", f"{REMOTE_PATH}/test_sii_remote_exec.py")
            print("Uploaded test_sii_remote_exec.py")
        except Exception as e:
            print(f"Warning: Could not upload test_sii_remote_exec.py: {e}")

        # Execute commands in groups
        command_groups = [
            # Group 1: Dependencies (Skip git operations now)
            [
                f"cd {REMOTE_PATH}",
                "curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py",
                "python3 get-pip.py --break-system-packages --user",
                "python3 -m pip install -r requirements.txt --break-system-packages --user"
            ],
            # Group 2: Start Application
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
