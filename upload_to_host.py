import paramiko
import os
import stat

HOST = "72.61.47.96"
USER = "sebas024"
KEY_FILE = "vps_key"
REMOTE_BASE_PATH = "/home/sebas024/htdocs/srv1274145.hstgr.cloud"

IGNORE_DIRS = {'.git', '.venv', 'venv', '__pycache__', '.idea', '.vscode'}
IGNORE_FILES = {'.DS_Store', 'vps_key', 'vps_key.pub', 'upload_to_host.py', 'clean_host.py', '.gitignore'}

def upload_files():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print(f"Connecting to {HOST}...")
        key = paramiko.RSAKey.from_private_key_file(KEY_FILE)
        client.connect(HOST, username=USER, pkey=key)
        sftp = client.open_sftp()
        print("Connected.")

        # Walk through local directory
        local_base_path = os.getcwd()
        
        for root, dirs, files in os.walk(local_base_path):
            # Filter ignored directories in place
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            
            # Calculate relative path
            rel_path = os.path.relpath(root, local_base_path)
            if rel_path == ".":
                rel_path = ""
                
            remote_path = os.path.join(REMOTE_BASE_PATH, rel_path).replace("\\", "/")
            
            # Create remote directory if it doesn't exist
            try:
                sftp.stat(remote_path)
            except FileNotFoundError:
                print(f"Creating directory: {remote_path}")
                try:
                    sftp.mkdir(remote_path)
                except Exception as e:
                    # Maybe parent doesn't exist? recursiveness usually needed but os.walk is top-down
                    # os.walk is top-down, so parents should exist already if we follow order.
                    # But just in case sftp.mkdir doesn't like deep paths if intermediates miss.
                    # Since we walk top-down, intermediates should be created in previous iterations.
                    print(f"Error creating {remote_path}: {e}")

            for file in files:
                if file in IGNORE_FILES:
                    continue
                if file.endswith(".pyc"): # Extra safety
                    continue
                    
                local_file_path = os.path.join(root, file)
                remote_file_path = os.path.join(remote_path, file).replace("\\", "/")
                
                print(f"Uploading {local_file_path} -> {remote_file_path}")
                try:
                    sftp.put(local_file_path, remote_file_path)
                except Exception as e:
                    print(f"Failed to upload {file}: {e}")

        print("Upload complete.")
        sftp.close()
        
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    upload_files()
