import paramiko
import time

# Configuration
HOST = "72.61.47.96"
USER = "sebas024"
KEY_FILE = "vps_key"
REMOTE_PATH = "/home/sebas024/htdocs/srv1274145.hstgr.cloud"

def manual_start():
    print(f"Connecting to {HOST}...")
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        key = paramiko.RSAKey.from_private_key_file(KEY_FILE)
        client.connect(HOST, username=USER, pkey=key)
        
        print("Connected. Attempting manual start...")
        
        # Step 1: Kill existing
        print("Killing existing uvicorn...")
        client.exec_command("pkill -f uvicorn")
        time.sleep(1)
        
        # Step 2: Try to run uvicorn in foreground to catch errors
        print("Running uvicorn in foreground (timeout 15s)...")
        command = (
            f"cd {REMOTE_PATH} && "
                "export PYTHONPATH=$PYTHONPATH:/home/sebas024/.local/lib/python3.12/site-packages && "
                "export PATH=$PATH:/home/sebas024/.local/bin && "
                "python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8090"
            )
        
        stdin, stdout, stderr = client.exec_command(command, timeout=15)
        
        # Read output
        import select
        
        channel = stdout.channel
        endtime = time.time() + 15
        
        full_stderr = ""
        full_stdout = ""
        
        while not channel.exit_status_ready() and time.time() < endtime:
            if channel.recv_ready():
                chunk = channel.recv(4096).decode()
                full_stdout += chunk
                print(chunk, end="")
            if channel.recv_stderr_ready():
                chunk = channel.recv_stderr(4096).decode()
                full_stderr += chunk
                print("ERROR_CHUNK: " + chunk, end="")
            time.sleep(0.1)
            
        # Flush remaining
        if channel.recv_ready():
            print(channel.recv(4096).decode(), end="")
        if channel.recv_stderr_ready():
            print("FINAL_ERROR: " + channel.recv_stderr(4096).decode(), end="")
            
        if channel.exit_status_ready():
            print(f"\nProcess exited with status: {channel.recv_exit_status()}")
        
        client.close()
        
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    manual_start()
