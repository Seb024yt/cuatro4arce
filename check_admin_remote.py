import paramiko

HOST = "72.61.47.96"
USER = "sebas024"
KEY_FILE = "vps_key"
REMOTE_PATH = "/home/hstgr-srv1274145/htdocs/srv1274145.hstgr.cloud"

def check_admin():
    print(f"Connecting to {HOST}...")
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        key = paramiko.RSAKey.from_private_key_file(KEY_FILE)
        client.connect(HOST, username=USER, pkey=key)
        
        python_code = (
            "from sqlmodel import Session, select, create_engine; "
            "from app.models import User; "
            "engine = create_engine('sqlite:///database.db'); "
            "session = Session(engine); "
            "u = session.exec(select(User).where(User.email=='admin@example.com')).first(); "
            "print(f'Admin Found: {u.email}, Is Admin: {u.is_admin}') if u else print('Admin NOT found')"
        )
        
        command = (
            f"cd {REMOTE_PATH} && "
            "export PYTHONPATH=$PYTHONPATH:/home/sebas024/.local/lib/python3.12/site-packages && "
            f"python3 -c \"{python_code}\""
        )
        
        stdin, stdout, stderr = client.exec_command(command)
        
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        
        print("OUTPUT:")
        print(output)
        if error:
            print("ERRORS:")
            print(error)
            
        client.close()
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    check_admin()
