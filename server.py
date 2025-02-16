import socket, os, time, pathlib, hashlib, threading
from db import DatabaseManager
from log import Logger

logger = Logger().get_logger()

class Server:
    def __init__(self):
        self.dbm = DatabaseManager()
        

    def start_file_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(('0.0.0.0', 65432))
        server.listen(10)
        logger.info('File server started...')

        while True:
            try:
                conn, addr = server.accept()
                conn.settimeout(10)
                logger.info(f'Connected by {addr}')
            except socket.timeout:
                logger.info('Server accept timeout, continue...')
                continue
            except OSError as e:
                logger.error(f'Socket error: {e}, restarting server...')
                server.close()
                time.sleep(5)
                return self.start_file_server()  
            try:
                file_hash = conn.recv(64).decode().strip()
                if not file_hash:
                    logger.info(f'Empty message from {addr}')
                    continue
                file_path = self.dbm.get_file_path_by_hash(file_hash)

                if file_path and os.path.exists(file_path):
                    logger.info(f'Sending file {file_path}')
                    conn.send(b'OK')
                    with open(file_path, 'rb') as f:
                        conn.sendfile(f)
                else:
                    logger.info(f'File {file_hash} not found!')
                    conn.send(b'NOT_FOUND')

            except socket.timeout:
                logger.warning(f'Timeout waiting for data from {addr}, closing connection')
            except Exception as e:
                logger.error(f'Error handling request from {addr}: {e}')
            finally:
                conn.close()

    def start_db_server(self):
        '''Open server to share shared.db'''
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(('0.0.0.0', 65431))
        server.listen(10)
        logger.info('Waiting for incoming connection...')
        while True:
            try:
                conn, addr = server.accept()
                conn.settimeout(10)
                logger.info(f'Connected by {addr}')
                self.dbm.add_device(addr[0]) 
            except socket.timeout:
                logger.info('Server accept timeout, continue...')
                continue
        
            try:
                message = conn.recv(1024).decode().strip()
                if not message:
                    logger.info(f'Empty message from {addr}')
                    continue

                if message == 'DB_UPDATED':
                    logger.info(f'Received DB_UPDATED notification from {addr}, downloading new database...')
                    self.download_shared_db(addr[0])
                else:
                    logger.info(f'Sending shared.db to {addr}...')
                    with open('shared.db', 'rb') as f:
                        conn.sendfile(f)
                    logger.info('Database sent successfully!')
            except socket.timeout:
                logger.warning(f'Timeout waiting for data from {addr}, closing connection')
            except Exception as e:
                logger.error(f'Error handling request from {addr}: {e}')
            finally:
                conn.close()

    def download_shared_db(self, host):
        '''Download shared.db'''
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(10)
        try:
            client.connect((host, 65431))
            client.send(b'DB_NOT_UPDATED')

            with open('shared.db', 'wb') as f:
                while chunk := client.recv(4096):
                    f.write(chunk)

            logger.info('Shared database downloaded!')
        except socket.timeout:
            logger.info(f'Connection to {host} timed out!')
        except Exception as e:
            logger.error(f'Error downloading shared database: {e}')
        finally:
            client.close()

class DownloadDaemon:
    def __init__(self):
        self.dbm = DatabaseManager()
        self.myip = self.get_local_ip()
        self.s = Server()
        self.dbm.add_device(self.myip)
        self.db_lock = threading.Lock()

    def get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip

    def download_file_from_peer(self, host, file_hash):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(10)
        try:
            client.connect((host, 65432))
            client.send(file_hash.encode())
            response = client.recv(2)

            if response == b'OK':
                file_path = f'synced_download/{file_hash}'
                os.makedirs('synced_download', exist_ok=True)

                with open(file_path, 'wb') as f:
                    while chunk := client.recv(4096):
                        f.write(chunk)
                self.dbm.add_directory('synced_download')
                self.dbm.add_file(file_path)
                return True
            else:
                logger.info(f'File {file_hash} not found on {host}')
                return False
        except socket.timeout:
            logger.error(f'Connection to {host} timed out!')
            return False
        except Exception as e:
            logger.error(f'Failed to download {file_hash} from {host}: {e}')
            return False
        finally:
            client.close() 
    
    def download_missing_files(self):
        missing_files = self.dbm.get_missing_files()
        if not missing_files:
            logger.info('No missing files found')
            return
        shared_ips = self.dbm.get_known_ips()

        for file_hash in missing_files:
            for ip in shared_ips:
                logger.info(f'Requesting {file_hash} from {ip}')
                if self.download_file_from_peer(ip, file_hash):
                    logger.info(f'File {file_hash} downloaded!')
                    break
            else:
                logger.info(f'File {file_hash} not found on any device')

    def notify_devices(self):
        shared_ips = self.dbm.get_known_ips()
        for ip in shared_ips:
            if ip != self.myip:  # Avoid notifying self
                try:
                    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client.connect((ip, 65431))
                    client.send(b'DB_UPDATED')
                    client.close()
                except Exception as e:
                    logger.error(f'Failed to notify {ip}: {e}')
            
    def monitoring(self):
        with self.db_lock:
            last_files_paths = [row[1] for row in self.dbm.get_local_files()]
        while True:
            time.sleep(15)

            # File in base, but not in directory
            for path in last_files_paths:
                path = pathlib.Path(path).resolve()
                if not path.exists():
                    logger.info(f'{path} is missing!')
                    with self.db_lock:
                        shared_ips = self.dbm.get_known_ips()
                        file_hash = self.dbm.get_file_hash_by_path(str(path))
                    for ip in shared_ips:
                        logger.info(f'Requesting {file_hash} from {ip}')
                        if self.download_file_from_peer(ip, file_hash):
                            logger.info(f'File {file_hash} downloaded!')
                            break
                    else:
                        logger.info(f'File {file_hash} not found on any device')

            # File in directory, but not in base
            with self.db_lock:
                directories2check = self.dbm.get_local_directories()
            for path in directories2check:
                logger.info(f'Checking {path} directory for updates')
                path = pathlib.Path(path).resolve()
                for file in path.rglob('*'):
                    if file not in last_files_paths and file.is_file():
                        with self.db_lock:
                            self.dbm.add_file(str(file))  # here we add new file to DB

            with self.db_lock:
                current_files = [row[1] for row in self.dbm.get_local_files()]
            if current_files != last_files_paths:
                logger.info('shared.db has changed, notifying devices...')
                self.notify_devices()
                last_files_paths = current_files

            self.download_missing_files()
        pass