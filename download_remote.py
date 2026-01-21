import paramiko
import os
from stat import S_ISDIR

# Configuration
HOST = "72.61.47.96"
USER = "sebas024"
KEY_FILE = "vps_key"
REMOTE_PATH = "/home/sebas024/htdocs/srv1274145.hstgr.cloud/app"
LOCAL_PATH = "app"

def download_dir(sftp, remote_dir, local_dir):
    if not os.path.exists(local_dir):
        os.makedirs(local_dir)
        
    for entry in sftp.listdir_attr(remote_dir):
        remote_path = remote_dir + "/" + entry.filename
        local_path = os.path.join(local_dir, entry.filename)
        
        if S_ISDIR(entry.st_mode):
            if entry.filename == "__pycache__":
                continue
            download_dir(sftp, remote_path, local_path)
        else:
            # Skip database files or logs if they exist in app folder
            if entry.filename.endswith(".db") or entry.filename.endswith(".log"):
                continue
                
            print(f"Downloading {entry.filename}...")
            sftp.get(remote_path, local_path)

def main():
    print(f"Connecting to {HOST}...")
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        key = paramiko.RSAKey.from_private_key_file(KEY_FILE)
        client.connect(HOST, username=USER, pkey=key)
        
        sftp = client.open_sftp()
        
        print("Starting download...")
        download_dir(sftp, REMOTE_PATH, LOCAL_PATH)
        
        sftp.close()
        client.close()
        print("Download complete.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
