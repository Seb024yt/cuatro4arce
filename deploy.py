import paramiko
import time

# Configuration
HOST = "72.61.47.96"
USER = "sebas024"
KEY_FILE = "vps_key"
REMOTE_PATH = "/home/sebas024/htdocs/srv1274145.hstgr.cloud"

def deploy():
    print(f"Connecting to {HOST}...")
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Load private key
        key = paramiko.RSAKey.from_private_key_file(KEY_FILE)
        
        client.connect(HOST, username=USER, pkey=key)
        
        print("Connected. Pulling latest changes from GitHub...")
        
        # Execute git pull and install dependencies
        commands = [
            f"cd {REMOTE_PATH}",
            "git pull origin main",
            "curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py",
            "python3 get-pip.py --break-system-packages --user",
            "python3 -m pip install -r requirements.txt --break-system-packages --user",
            "pkill -f uvicorn || true",  # Kill existing process
            "nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > app.log 2>&1 &" # Start new process
        ]
        
        full_command = " && ".join(commands)
        stdin, stdout, stderr = client.exec_command(full_command)
        
        # Wait for command to finish and get exit status
        exit_status = stdout.channel.recv_exit_status()
        
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        
        if output:
            print("OUTPUT:")
            print(output)
            
        if error:
            print("ERRORS/WARNINGS:")
            print(error)
            
        if exit_status == 0:
            print("\nDeployment successful! [OK]")
        else:
            print("\nDeployment failed! [X]")
            
        client.close()
        
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    deploy()
