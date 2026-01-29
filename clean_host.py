import paramiko
import os

HOST = "72.61.47.96"
USER = "sebas024"
KEY_FILE = "vps_key"
REMOTE_PATH = "/home/sebas024/htdocs/srv1274145.hstgr.cloud"

def clean_host():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        key = paramiko.RSAKey.from_private_key_file(KEY_FILE)
        client.connect(HOST, username=USER, pkey=key)
        
        print(f"Connected to {HOST}. cleaning {REMOTE_PATH}...")
        
        # Execute command to remove all files in the remote path
        # We preserve the directory itself, but empty it.
        # Be very careful with rm -rf
        
        # Check if directory exists first
        stdin, stdout, stderr = client.exec_command(f"[ -d {REMOTE_PATH} ] && echo 'exists'")
        if stdout.read().decode().strip() == 'exists':
            print(f"Directory {REMOTE_PATH} found. Deleting contents...")
            # rm -rf /path/* (and hidden files if any, but * usually misses .files)
            # To delete all including hidden: rm -rf /path/{*,.*} but that matches . and .. which is bad.
            # Try rm -rf for more force, but be careful with path
            cmd = f"rm -rf {REMOTE_PATH}/* {REMOTE_PATH}/.* 2>/dev/null || true"
            stdin, stdout, stderr = client.exec_command(cmd)
            
            # Verify if empty
            stdin, stdout, stderr = client.exec_command(f"ls -A {REMOTE_PATH}")
            remaining = stdout.read().decode().strip()
            
            if not remaining:
                print("Remote directory cleaned successfully.")
            else:
                print(f"Warning: Some files could not be deleted:\n{remaining}")
        else:
            print(f"Remote directory {REMOTE_PATH} does not exist.")
            
    except Exception as e:
        print(f"Connection error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    clean_host()
