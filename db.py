# DataBase logic, using MongoDB

from pymongo import MongoClient
from pathlib import Path
import hashlib
import time

class DatabaseManager:
    def __init__(self, dbname="catchfile", host="localhost", port=27017):
        self.client = MongoClient(host, port)
        self.db = self.client[dbname]
        self.shared_files = self.db.shared_files
        self.devices = self.db.devices
        self.local_files = self.db.local_files
        self.directories = self.db.directories

    def _calculate_file_hash(self, file_path, chunk_size=65536):
        # SHA-256
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(chunk_size), b''):
                hasher.update(chunk)
        return hasher.hexdigest()

    def add_directory(self, dir_path: str):
        self.directories.update_one(
            {"path": dir_path},
            {"$set": {"path": dir_path}},
            upsert=True
        )

    def add_file(self, file_path: str):
        """Add file to both DB"""
        file_path = Path(file_path).resolve()
        if not file_path.exists() or not file_path.is_file():
            raise ValueError("File does not exist")
        file_size = file_path.stat().st_size
        last_modified = int(file_path.stat().st_mtime)
        file_hash = self._calculate_file_hash(file_path)

        self.shared_files.update_one(
            {"hash": file_hash},
            {"$set": {
                "hash": file_hash,
                "filename": file_path.name,
                "size": file_size,
                "last_modified": last_modified,
                "deleted": False
            }},
            upsert=True
        )

        self.local_files.update_one(
            {"hash": file_hash},
            {"$set": {
                "hash": file_hash,
                "path": str(file_path),
                "ignored": False
            }},
            upsert=True
        )

    def get_local_directories(self):
        return [d["path"] for d in self.directories.find()]

    def get_file_path_by_hash(self, file_hash: str):
        file = self.local_files.find_one({"hash": file_hash})
        return file["path"] if file else None

    def add_device(self, ip):
        self.devices.update_one(
            {"ip": ip},
            {"$set": {
                "ip": ip,
                "last_seen": int(time.time())
            }},
            upsert=True
        )

    def remove_file(self, file_hash: str):
        """Mark file in DB as deleted"""
        self.shared_files.update_one(
            {"hash": file_hash},
            {"$set": {"deleted": True}}
        )

    def unsync_file(self, file_path: str):
        """Stop syncing file"""
        file_path = Path(file_path).resolve()
        if not file_path.exists() or not file_path.is_file():
            raise ValueError("File does not exist")
        file_hash = self._calculate_file_hash(file_path)

        self.local_files.update_one(
            {"hash": file_hash},
            {"$set": {"ignored": True}}
        )

    def get_missing_files(self):
        """List of missing files"""
        shared_files = {f["hash"] for f in self.shared_files.find({"deleted": False})}
        local_files = {f["hash"] for f in self.local_files.find({"ignored": False})}
        return list(shared_files - local_files)

    def get_local_files(self):
        """List of local files"""
        return list(self.local_files.find())

    def get_known_ips(self):
        """Retrieve a list of known IP addresses from the devices table."""
        return [d["ip"] for d in self.devices.find()]