import socket, os
from db import DatabaseManager

def start_file_server():
    dbm = DatabaseManager()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", 65432))
    server.listen(5)
    print("File server started...")

    while True:
        conn, addr = server.accept()
        print(f"Connected by {addr}")

        file_hash = conn.recv(64).decode().strip() 
        file_path = dbm.get_file_path_by_hash(file_hash)

        if file_path and os.path.exists(file_path):
            print(f"Sending file {file_path}")
            conn.send(b"OK")
            with open(file_path, "rb") as f:
                conn.sendfile(f)
        else:
            print(f"File {file_hash} not found!")
            conn.send(b"NOT_FOUND")

        conn.close()

def start_db_server():
    """Open server to share shared.db"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", 65432)) 
    server.listen(1)
    print("Waiting for incoming connection...")

    conn, addr = server.accept()
    print(f"Connected by {addr}, sending shared.db...")

    with open("shared.db", "rb") as f:
        conn.sendfile(f)

    conn.close()
    server.close()
    print("Database sent successfully!")

def download_shared_db(host):
    """Download shared.db"""
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((host, 65432))  

    with open("shared.db", "wb") as f:
        while chunk := client.recv(4096):
            f.write(chunk)

    client.close()
    print("Shared database downloaded!")
