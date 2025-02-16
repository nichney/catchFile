# DataBase logic, using SQLite

import sqlite3
from pathlib import Path
import hashlib
import time
from log import Logger

logger = Logger().get_logger()

class DatabaseManager:
    def __init__(self, shared_db='shared.db', local_db='local.db'):
        self.shared_db = shared_db
        self.local_db = local_db
        self._init_shared_db()
        self._init_local_db()
        logger.info('DatabaseManager initialized successfully')

    def _init_shared_db(self):
        '''Create shared DB if not exists'''
        with sqlite3.connect(self.shared_db) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS files (
                    hash TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    size INTEGER,
                    last_modified INTEGER,
                    deleted BOOLEAN DEFAULT 0
                )
            ''')
            cursor.execute('''
                    CREATE TABLE IF NOT EXISTS devices (
                        ip TEXT PRIMARY KEY, 
                        last_seen INTEGER
                    )
            ''')
            conn.commit()
        logger.info('Shared database initialized')

    def _init_local_db(self):
        '''Create local DB if not exists'''
        with sqlite3.connect(self.local_db) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS local_files (
                    hash TEXT PRIMARY KEY,
                    path TEXT NOT NULL,
                    ignored BOOLEAN DEFAULT 0
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS directories (
                    path TEXT PRIMARY KEY
                )
            ''')
            conn.commit()
        logger.info('Local database initialized')

    def _calculate_file_hash(self, file_path, chunk_size=65536):
        # SHA-256
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(chunk_size), b''):
                hasher.update(chunk)
        return hasher.hexdigest()   

    def add_directory(self, dir_path: str):
        with sqlite3.connect(self.local_db) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO directories (path )
                VALUES (?)
            ''', (dir_path, ))
            conn.commit()
        logger.info(f'Directory {dir_path} added to local database')

    def add_file(self, file_path: str):
        '''Add file to both DB'''
        file_path = Path(file_path).resolve()
        if not file_path.exists() or not file_path.is_file():
            logger.error(f'File {file_path} does not exists')
            raise ValueError('File does not exists')
        file_size = file_path.stat().st_size
        last_modified = int(file_path.stat().st_mtime)
        file_hash =  self._calculate_file_hash(file_path)

        with sqlite3.connect(self.shared_db) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO files (hash, filename, size, last_modified, deleted)
                VALUES (?, ?, ?, ?, 0)
            ''', (file_hash, file_path.name, file_size, last_modified))
            conn.commit()
        logger.info(f'File {file_path.name} added to shared database')

        with sqlite3.connect(self.local_db) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO local_files (hash, path, ignored)
                VALUES (?, ?, 0)
            ''', (file_hash, str(file_path)))
            conn.commit()
        logger.info(f'File {file_path.name} added to local database')
    
    def get_local_directories(self):
        with sqlite3.connect(self.local_db) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT path FROM directories')
            result = cursor.fetchall()
            return [row[0] for row in result]

    def get_file_path_by_hash(self, file_hash: str):
        with sqlite3.connect(self.local_db) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT path FROM local_files WHERE hash = ?', (file_hash, ))
            result = cursor.fetchone()
            return result[0] if result else None

    def get_file_hash_by_path(self, file_path: str):
        with sqlite3.connect(self.local_db) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT hash FROM local_files WHERE path = ?', (file_path, ))
            result = cursor.fetchone()
            return result[0] if result else None

    def add_device(self, ip):
        with sqlite3.connect(self.shared_db) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO devices (ip, last_seen)
                VALUES (?, ?) ON CONFLICT(ip) DO UPDATE SET last_seen=?
            ''', (ip, int(time.time()), int(time.time())))
            conn.commit()
            logger.info(f'Device {ip} added/updated in shared database')

    def remove_file(self, file_hash: str):
        '''Mark file in DB as deleted'''
        with sqlite3.connect(self.shared_db) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE files SET deleted = 1 WHERE hash = ?', (file_hash,))
            conn.commit()
            logger.info(f'File with hash {file_hash} marked as deleted in shared database')

    def remove_directory(self, dir_path: str):
        '''Remove directory from local DB by path'''
        with sqlite3.connect(self.local_db) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM directories WHERE path = ?', (dir_path,))
            conn.commit()
        logger.info(f'Directory {dir_path} removed from local database')

    def remove_file_by_hash(self, file_hash: str):
        '''Remove file from local DB by hash'''
        with sqlite3.connect(self.local_db) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM local_files WHERE hash = ?', (file_hash,))
            conn.commit()
        logger.info(f'File with hash {file_hash} removed from local database')

    def unsync_file(self, file_path: str):
        '''Stop syncing file'''
        file_path = Path(file_path).resolve()
        if not file_path.exists() or not file_path.is_file():
            logger.error(f'File {file_path} does not exist')
            raise ValueError('File does not exist') 
        file_hash =  self._calculate_file_hash(file_path)

        with sqlite3.connect(self.local_db) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE local_files SET ignored = 1 WHERE hash LIKE ?
            ''', (file_hash,))
            conn.commit()
            logger.info(f'File {file_path} set to ignored in local database')


    def get_missing_files(self):
        '''List of missing files'''
        with sqlite3.connect(self.shared_db) as shared_conn, sqlite3.connect(self.local_db) as local_conn:
            shared_cursor = shared_conn.cursor()
            local_cursor = local_conn.cursor()

            shared_cursor.execute('SELECT hash FROM files WHERE deleted = 0')
            shared_files = {row[0] for row in shared_cursor.fetchall()}

            local_cursor.execute('SELECT hash FROM local_files WHERE ignored = 0')
            local_files = {row[0] for row in local_cursor.fetchall()}
            return list(shared_files - local_files)

    def get_local_files(self):
        '''List of local files'''
        with sqlite3.connect(self.local_db) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM local_files')
            return cursor.fetchall()

    def get_known_ips(self):
        '''Retrieve a list of known IP addresses from the devices table.'''
        with sqlite3.connect(self.shared_db) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT ip FROM devices')
            result = cursor.fetchall()
            return [row[0] for row in result]
