import socket, os
from db import DatabaseManager

class Server:
    def __init__(self):
        self.dbm = DatabaseManager()

    def start_file_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(("0.0.0.0", 65432))
        server.listen(10)
        print("File server started...")

        while True:
            conn, addr = server.accept()
            print(f"Connected by {addr}")

            file_hash = conn.recv(64).decode().strip()
            file_path = self.dbm.get_file_path_by_hash(file_hash)

            if file_path and os.path.exists(file_path):
                print(f"Sending file {file_path}")
                conn.send(b"OK")
                with open(file_path, "rb") as f:
                    conn.sendfile(f)
            else:
                print(f"File {file_hash} not found!")
                conn.send(b"NOT_FOUND")

            conn.close()

    def start_db_server(self):
        """Open server to share shared.db"""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(("0.0.0.0", 65431))
        server.listen(10)
        print("Waiting for incoming connection...")
        while True:

            conn, addr = server.accept()
            print(f"Connected by {addr}, sending shared.db...")
            self.dbm.add_device(addr) 

            with open("shared.db", "rb") as f:
                conn.sendfile(f)

            conn.close()
            print("Database sent successfully!")

    def download_shared_db(self, host):
        """Download shared.db"""
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((host, 65431))

        with open("shared.db", "wb") as f:
            while chunk := client.recv(4096):
                f.write(chunk)

        client.close()
        print("Shared database downloaded!")


class DownloadDaemon:
    def __init__(self):
        self.dbm = DatabaseManager()
        self.myip = self.get_local_ip()
        self.s = Server()

    def get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip

    def download_file_from_peer(self, host, file_hash):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            client.connect((host, 65432))
            client.send(file_hash.encode())
            response = client.recv(2)
            if response == b'OK':
                file_path = f'synced_download/{file_hash}'
                os.makedirs('synced_download', exist_ok=True)

                with open(file_path, 'wb') as f:
                    while chunk := client .recv(4096):
                        f.write(chunk)
                client.close()
                self.dbm.add_file(file_path)
                return True
            else:
                print(f'File {file_hash} not found on {host}')
                client.close()
                return False
        except Exception as e:
            print(f'Failed to download {fila_hash} from {host}: {e}')
            return False
    
    def download_missing_files(self):
        missing_files = self.dbm.get_missing_files()
        if not missing_files:
            print('No missing files found')
            return
        shared_ips = self.dbm.get_known_ips()

        for file_hash in missing_files:
            for ip in shared_ips:
                print(f'Requesting {file_hash} from {ip}')
                if self.download_file_from_peer(ip, file_hash):
                    print(f'File {file_hash} downloaded!')
                    break
            else:
                print(f'File {file_hash} not found on any device')


    def monitoring(self):
        while True:
            # TODO: monitor shared.db for changes, and if there is an update from external devices, download new db































