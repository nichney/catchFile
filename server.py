import socket

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
