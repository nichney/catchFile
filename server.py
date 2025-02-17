# Copyright (C) 2025 Kirill Osmolovsky
import socket, os, time, pathlib, hashlib, threading
from db import DatabaseManager
from log import Logger
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = Logger().get_logger()

class Server:
    def __init__(self):
        self.dbm = DatabaseManager()
        self.myip = DownloadDaemon().get_local_ip()
        self.root_dir = 'synced' # КОСТЫЛЬ!!! TODO: find out root_dir
        

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

                if addr[0] not in self.dbm.get_known_ips():
                    logger.info(f'Unauthorized request from {addr[0]}, rejecting...')
                    conn.send(b'UNAUTHORIZED')
                    conn.close()
                    continue

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
                    conn.send(b'INVALID_REQUEST')
                    conn.close()
                    continue
                file_path = self.dbm.get_file_path_by_hash(file_hash)
                relative_path = pathlib.Path(file_path).relative_to(pathlib.Path(self.root_dir)).as_posix().encode()

                if file_path and os.path.exists(file_path):
                    conn.send(len(relative_path).to_bytes(4, 'big'))
                    conn.send(relative_path)
                    logger.info(f'Sending file {file_path}')
                    with open(file_path, 'rb') as f:
                        conn.sendfile(f)
                    logger.info('File sent')
                    conn.close()
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
                if addr[0] == self.myip:
                    logger.info(f'Recieved signal from self, ignoring...')
                    continue
                logger.info(f'Connected by {addr}')
                self.dbm.add_device(str(addr[0])) 
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

            logger.info('Shared database downloaded! Recieving missing files...')
            DownloadDaemon().download_missing_files()
            DownloadDaemon().delete_marked_files()
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
        logger.info(f'MY IP IS {self.myip}')
        #self.s = Server()
        self.dbm.add_device(self.myip)
        self.db_lock = threading.Lock()
        self.observer = Observer()
        self.root_dir = 'synced' # КОСТЫЛЬ!!!

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
            response = client.recv(12)

            if response in [b'UNAUTHORIZED', b'NOT_FOUND', b'INVALID_REQUEST']:
                logger.error(f'Server response: {response.decode()}')
                return False
        
            length = int.from_bytes(response[:4], 'big')
            relative_path = client.recv(length).decode().strip()

            file_path = pathlib.Path(self.root_dir) / pathlib.Path(relative_path)
            file_path = file_path.resolve()
            os.makedirs(file_path.parent, exist_ok=True)

            with open(file_path, 'wb') as f:
                while chunk := client.recv(4096):
                    f.write(chunk)
            self.dbm.add_file(file_path)
            return True
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

    def delete_marked_files(self):
        marked_files_hashes = self.dbm.get_deleted_files()
        marked_files_paths = [self.dbm.get_file_path_by_hash(i) for i in marked_files_hashes]
        if not marked_files_paths:
            logger.info('No deleted files found')
            return
        for file in marked_files_paths:
            try:
                self.dbm.remove_file_by_hash(self.dbm.get_file_hash_by_path(file)) # too sophisticated
                os.remove(file)
            except FileNotFoundError:
                logger.info('File already deleted')
            except TypeError as e:
                logger.error(f'Error {e}')

    def notify_devices(self):
        shared_ips = self.dbm.get_known_ips()
        for ip in shared_ips:
            if ip == self.myip:
                continue
            try:
                client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client.settimeout(10)
                client.connect((ip, 65431))
                client.send(b'DB_UPDATED')
                client.close()
            except Exception as e:
                logger.error(f'Failed to notify {ip}: {e}')
            
    def monitoring(self):
        '''Uses watchdog to monitor file system changes dynamically.'''
        self.download_missing_files()
        self.delete_marked_files()
        logger.info("Starting real-time file monitoring...")

        with self.db_lock:
            directories_to_watch = self.dbm.get_local_directories()

        event_handler = FileChangeHandler(self)
        for directory in directories_to_watch:
            path = pathlib.Path(directory).resolve()
            logger.info(f"Monitoring directory: {path}")
            self.observer.schedule(event_handler, str(path), recursive=True)

        self.observer.start()

        try:
            while True:
                time.sleep(1)
                #self.download_missing_files()
        except KeyboardInterrupt:
            self.observer.stop()
            logger.info("Stopping file monitoring...")

        self.observer.join()

class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, daemon):
        self.daemon = daemon 

    def on_created(self, event):
        """Handles new file creation."""
        if event.is_directory:
            return
        file_path = pathlib.Path(event.src_path).resolve()
        logger.info(f"New file detected: {file_path}")
        try:
            with self.daemon.db_lock:
                self.daemon.dbm.add_file(str(file_path))
            self.daemon.notify_devices()
        except ValueError:
            logger.error(f'Error while adding created file {file_path}, possible temporary file')

    def on_deleted(self, event):
        """Handles file deletions."""
        if event.is_directory:
            return
        file_path = pathlib.Path(event.src_path).resolve()
        logger.info(f"File deleted: {file_path}")
        with self.daemon.db_lock:
            file_hash = self.daemon.dbm.get_file_hash_by_path(str(file_path))
            if file_hash:
                self.daemon.dbm.remove_file_by_hash(file_hash)
                self.daemon.dbm.remove_file(file_hash)
        self.daemon.notify_devices()

    def on_modified(self, event):
        """Handles file modifications (if needed)."""
        if event.is_directory:
            return
        file_path = pathlib.Path(event.src_path).resolve()
        logger.info(f"File modified: {file_path}")
        try:
            with self.daemon.db_lock:
                self.daemon.dbm.update_file_hash(str(file_path))
            #self.daemon.notify_devices()
        except FileNotFoundError:
            logger.error(f'Error while modifying hash of file {file_path}, possible temporary file')