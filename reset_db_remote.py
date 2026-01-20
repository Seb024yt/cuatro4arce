import paramiko
import time

# Configuration
HOST = "72.61.47.96"
USER = "sebas024"
KEY_FILE = "vps_key"
REMOTE_PATH = "/home/sebas024/htdocs/srv1274145.hstgr.cloud"

def reset_db():
    print(f"Connecting to {HOST}...")
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Load private key
        key = paramiko.RSAKey.from_private_key_file(KEY_FILE)
        
        client.connect(HOST, username=USER, pkey=key)
        
        print("Connected. Debugging file location...")
        
        commands = [
            f"cd {REMOTE_PATH}",
            "ls -la", # List all files to find database.db
            "rm -f database.db",  # Delete the database
            "rm -f app/database.db", # Just in case it's inside app/
            "echo 'Database deletion attempted.'",
            "ls -la", # Verify deletion
            "./start.sh"          # Restart the app
        ]

        full_command = " && ".join(commands)
        stdin, stdout, stderr = client.exec_command(full_command)
        
        # Wait for start
        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        
        if output:
            print(f"OUTPUT:\n{output}")
        if error:
            print(f"ERRORS:\n{error}")
            
        print("\nReset complete. Database should be recreated on startup.")
            
        client.close()
        
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    reset_db()
