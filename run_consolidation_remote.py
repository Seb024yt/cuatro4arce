import paramiko
import time
import os

HOST = "72.61.47.96"
USER = "sebas024"
KEY_FILE = "vps_key"
REMOTE_PATH = "/home/sebas024/htdocs/srv1274145.hstgr.cloud"

def run():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        key = paramiko.RSAKey.from_private_key_file(KEY_FILE)
        client.connect(HOST, username=USER, pkey=key)
        
        # Upload app/data_processor.py
        sftp = client.open_sftp()
        print("Uploading app/data_processor.py...")
        sftp.put("app/data_processor.py", f"{REMOTE_PATH}/app/data_processor.py")

        # Upload app/sii_connector.py
        print("Uploading app/sii_connector.py...")
        sftp.put("app/sii_connector.py", f"{REMOTE_PATH}/app/sii_connector.py")
        
        # Upload examples image
        try:
            try:
                sftp.stat(f"{REMOTE_PATH}/ejemplos")
            except FileNotFoundError:
                sftp.mkdir(f"{REMOTE_PATH}/ejemplos")
            
            images_to_upload = ["3 RCV COMPRA.png", "7 COMPRAS.png", "8 VENTAS.png", "9 BH.png", "10 IMPUESTO UNICO.png", "11 DIN.png", "13 COMPRAS ANALISIS.png", "15 VENTAS ANALISIS.png"]
            for img_name in images_to_upload:
                local_img = f"ejemplos/{img_name}"
                if os.path.exists(local_img):
                    print(f"Uploading {img_name}...")
                    sftp.put(local_img, f"{REMOTE_PATH}/ejemplos/{img_name}")
        except Exception as e:
            print(f"Error uploading image: {e}")

        # Create a small script on remote to run consolidation
        remote_script = """
import sys
import os
sys.path.append(os.getcwd())
from app.data_processor import consolidate_data

job_id = "test_job_manual_047"
base_dir = "sii_data"
download_dir = os.path.join(base_dir, "descargados", job_id)
output_dir = os.path.join(base_dir, "generados")
output_file = os.path.join(output_dir, f"Planilla_{job_id}.xlsx")

print(f"Consolidating {download_dir} to {output_file}...")
try:
    consolidate_data(download_dir, output_file)
    print("Consolidation complete.")
except Exception as e:
    print(f"Error: {e}")
"""
        with open("temp_consolidate.py", "w") as f:
            f.write(remote_script)
            
        print("Uploading temp_consolidate.py...")
        sftp.put("temp_consolidate.py", f"{REMOTE_PATH}/temp_consolidate.py")
        
        # Ensure 047 data exists by copying from 046
        print("Ensuring test data exists for 047...")
        client.exec_command(f"cp -r {REMOTE_PATH}/sii_data/descargados/test_job_manual_046 {REMOTE_PATH}/sii_data/descargados/test_job_manual_047")
        
        print("Running consolidation...")
        stdin, stdout, stderr = client.exec_command(f"cd {REMOTE_PATH} && python3 temp_consolidate.py")
        print(stdout.read().decode())
        print(stderr.read().decode())
        
        print("\n--- Syncing result back ---")
        # Tar relevant folders to ensure we get everything (descargados for this job, and generados)
        # We'll just tar the whole sii_data to be safe and simple, or specific folders
        print("Creating remote archive...")
        # Tar only the specific job folder and generados to avoid huge download
        cmd_tar = f"cd {REMOTE_PATH} && tar -czf sii_data_sync.tar.gz sii_data/generados sii_data/descargados/test_job_manual_047"
        stdin, stdout, stderr = client.exec_command(cmd_tar)
        exit_code = stdout.channel.recv_exit_status()
        
        if exit_code == 0:
            print("Downloading sii_data_sync.tar.gz...")
            sftp.get(f"{REMOTE_PATH}/sii_data_sync.tar.gz", "sii_data_sync.tar.gz")
            
            import tarfile
            if os.path.exists("sii_data_sync.tar.gz") and os.path.getsize("sii_data_sync.tar.gz") > 0:
                print("Extracting locally...")
                with tarfile.open("sii_data_sync.tar.gz", "r:gz") as tar:
                    tar.extractall(path=".")
                print("Sync complete.")
            else:
                print("Error: Downloaded archive is empty or missing.")
        else:
            print(f"Error creating remote archive: {stderr.read().decode()}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()
        if os.path.exists("temp_consolidate.py"):
            os.remove("temp_consolidate.py")

if __name__ == "__main__":
    run()
