# DataBase logic, using PostgreSQL

import psycopg2
from psycopg2 import sql
from pathlib import Path
import hashlib
import time

class DatabaseManager:
    def __init__(self, dbname="yourdbname", user="yourusername", password="yourpassword", host="localhost", port="5432"):
        self.conn = psycopg2.connect(dbname=dbname, user=user, password=password, host=host, port=port)
        self._init_shared_db()
        self._init_local_db()

    def _init_shared_db(self):
        """Create shared DB if not exists"""
        with self.conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    hash TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    size INTEGER,
                    last_modified INTEGER,
                    deleted BOOLEAN DEFAULT FALSE
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    ip TEXT PRIMARY KEY, 
                    last_seen INTEGER
                )
            """)
            self.conn.commit()

    def _init_local_db(self):
        """Create local DB if not exists"""
        with self.conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS local_files (
                    hash TEXT PRIMARY KEY,
                    path TEXT NOT NULL,
                    ignored BOOLEAN DEFAULT FALSE
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS directories (
                    path TEXT PRIMARY KEY
                )
            """)
            self.conn.commit()

    def _calculate_file_hash(self, file_path, chunk_size=65536):
        # SHA-256
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(chunk_size), b''):
                hasher.update(chunk)
        return hasher.hexdigest()

    def add_directory(self, dir_path: str):
        with self.conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO directories (path)
                VALUES (%s) ON CONFLICT (path) DO NOTHING
            """, (dir_path,))
            self.conn.commit()

    def add_file(self, file_path: str):
        """Add file to both DB"""
        file_path = Path(file_path).resolve()
        if not file_path.exists() or not file_path.is_file():
            raise ValueError("File does not exist")
        file_size = file_path.stat().st_size
        last_modified = int(file_path.stat().st_mtime)
        file_hash = self._calculate_file_hash(file_path)

        with self.conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO files (hash, filename, size, last_modified, deleted)
                VALUES (%s, %s, %s, %s, FALSE)
                ON CONFLICT (hash) DO UPDATE SET 
                    filename = EXCLUDED.filename,
                    size = EXCLUDED.size,
                    last_modified = EXCLUDED.last_modified,
                    deleted = EXCLUDED.deleted
            """, (file_hash, file_path.name, file_size, last_modified))
            self.conn.commit()

            cursor.execute("""
                INSERT INTO local_files (hash, path, ignored)
                VALUES (%s, %s, FALSE)
                ON CONFLICT (hash) DO UPDATE SET 
                    path = EXCLUDED.path,
                    ignored = EXCLUDED.ignored
            """, (file_hash, str(file_path)))
            self.conn.commit()

    def get_local_directories(self):
        with self.conn.cursor() as cursor:
            cursor.execute('SELECT path FROM directories')
            result = cursor.fetchall()
            return [row[0] for row in result]

    def get_file_path_by_hash(self, file_hash: str):
        with self.conn.cursor() as cursor:
            cursor.execute('SELECT path FROM local_files WHERE hash = %s', (file_hash,))
            result = cursor.fetchone()
            return result[0] if result else None

    def add_device(self, ip):
        current_time = int(time.time())
        with self.conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO devices (ip, last_seen)
                VALUES (%s, %s) ON CONFLICT(ip) DO UPDATE SET last_seen=%s
            """, (ip, current_time, current_time))
            self.conn.commit()

    def remove_file(self, file_hash: str):
        """Mark file in DB as deleted"""
        with self.conn.cursor() as cursor:
            cursor.execute("UPDATE files SET deleted = TRUE WHERE hash = %s", (file_hash,))
            self.conn.commit()

    def unsync_file(self, file_path: str):
        """Stop syncing file"""
        file_path = Path(file_path).resolve()
        if not file_path.exists() or not file_path.is_file():
            raise ValueError("File does not exist")
        file_hash = self._calculate_file_hash(file_path)

        with self.conn.cursor() as cursor:
            cursor.execute("""
                UPDATE local_files SET ignored = TRUE WHERE hash = %s
            """, (file_hash,))
            self.conn.commit()

    def get_missing_files(self):
        """List of missing files"""
        with self.conn.cursor() as cursor:
            cursor.execute("SELECT hash FROM files WHERE deleted = FALSE")
            shared_files = {row[0] for row in cursor.fetchall()}

            cursor.execute("SELECT hash FROM local_files WHERE ignored = FALSE")
            local_files = {row[0] for row in cursor.fetchall()}

            return list(shared_files - local_files)

    def get_local_files(self):
        """List of local files"""
        with self.conn.cursor() as cursor:
            cursor.execute("SELECT * FROM local_files")
            return cursor.fetchall()

    def get_known_ips(self):
        """Retrieve a list of known IP addresses from the devices table."""
        with self.conn.cursor() as cursor:
            cursor.execute("SELECT ip FROM devices")
            result = cursor.fetchall()
            return [row[0] for row in result]