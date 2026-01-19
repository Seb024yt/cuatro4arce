import paramiko
import time

HOST = "72.61.47.96"
USER = "sebas024"
KEY_FILE = "vps_key"
REMOTE_PATH = "/home/sebas024/htdocs/srv1274145.hstgr.cloud"

def clean_and_deploy():
    print(f"Connecting to {HOST}...")
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        key = paramiko.RSAKey.from_private_key_file(KEY_FILE)
        client.connect(HOST, username=USER, pkey=key)
        
        print("Connected.")
        
        # 1. Check hidden files
        print("Checking hidden files...")
        stdin, stdout, stderr = client.exec_command(f"ls -la {REMOTE_PATH}")
        print(stdout.read().decode().strip())
        
        # 2. Cleanup unwanted files
        print("Cleaning up WordPress files and logs...")
        # Note: Added sudo if necessary or using find for more control
        remove_cmd = f"cd {REMOTE_PATH} && rm -rf wp-admin wp-content wp-includes index.php wp-*.php xmlrpc.php readme.html license.txt deploy_log*.txt"
        print(f"Executing: {remove_cmd}")
        stdin, stdout, stderr = client.exec_command(remove_cmd)
        print("Cleanup output:", stdout.read().decode().strip())
        print("Cleanup errors:", stderr.read().decode().strip())
        
        # 3. Git Reset and Pull (Force sync)
        print("Syncing with GitHub (Force)...")
        sync_cmds = [
            f"cd {REMOTE_PATH}",
            "git fetch origin main",
            "git reset --hard origin/main", # Force match remote
            #"git clean -fd", # Remove untracked files (careful!) - maybe skip this if we want to keep some
            "git pull origin main"
        ]
        
        # Using git clean might delete database.db if not tracked. 
        # I'll stick to git reset --hard which resets tracked files.
        # I already manually deleted WP files.
        
        full_sync_cmd = " && ".join(sync_cmds)
        stdin, stdout, stderr = client.exec_command(full_sync_cmd)
        print("Sync output:", stdout.read().decode().strip())
        print("Sync errors:", stderr.read().decode().strip())
        
        # 4. Restart App
        print("Restarting Application...")
        restart_cmds = [
            f"cd {REMOTE_PATH}",
            "pkill -f uvicorn || true",
            "nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > app.log 2>&1 &"
        ]
        full_restart_cmd = " && ".join(restart_cmds)
        client.exec_command(full_restart_cmd)
        
        print("Deployment triggered. Waiting 5s...")
        time.sleep(5)
        
        # Check logs
        stdin, stdout, stderr = client.exec_command(f"cat {REMOTE_PATH}/app.log")
        print("App Logs:")
        print(stdout.read().decode().strip())
        
        # Final file check
        print("Final file check:")
        stdin, stdout, stderr = client.exec_command(f"ls -F {REMOTE_PATH}")
        print(stdout.read().decode().strip())
        
        client.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    clean_and_deploy()
