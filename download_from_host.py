import paramiko
import os

HOST = "72.61.47.96"
USER = "sebas024"
KEY_FILE = "vps_key"
REMOTE_PATH = "/home/sebas024/htdocs/srv1274145.hstgr.cloud"

def download_changes():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        key = paramiko.RSAKey.from_private_key_file(KEY_FILE)
        client.connect(HOST, username=USER, pkey=key)
        sftp = client.open_sftp()
        
        files_to_sync = [
            "app/data_processor.py",
            "app/sii_connector.py",
            "app/email_sender.py",
            "app/main.py",
            "app/templates/portal.html",
            "app/templates/inicio.html",
            "deploy.py"
        ]
        
        for file_path in files_to_sync:
            remote_file = f"{REMOTE_PATH}/{file_path}"
            local_file = file_path
            
            try:
                # Check if remote file exists
                sftp.stat(remote_file)
                print(f"Downloading {file_path} from remote...")
                sftp.get(remote_file, local_file)
                print(f"Successfully updated {local_file}")
            except FileNotFoundError:
                print(f"Remote file {remote_file} not found. Skipping.")
            except Exception as e:
                print(f"Error downloading {file_path}: {e}")

    except Exception as e:
        print(f"Connection error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    download_changes()
