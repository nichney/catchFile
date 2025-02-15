# Resolve magnet links

import base64
import json
import uuid
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
import hashlib
import socket

class MagnetLinkGenerator:
    def __init__(self, shared_db="shared.db"):
        self.shared_db = shared_db
        self.device_id = self._generate_device_id()

    def _generate_device_id(self):
        return str(uuid.uuid4())

    def _calculate_db_hash(self):
        hasher = hashlib.sha256()
        with open(self.shared_db, "rb") as f:
            hasher.update(f.read())
        return hasher.hexdigest()

    def _encrypt_data(self, data, key):
        """Encrypt data with AES-256-GCM"""
        aesgcm = AESGCM(key)
        nonce = os.urandom(12) 
        encrypted_data = aesgcm.encrypt(nonce, data.encode(), None)
        return base64.urlsafe_b64encode(nonce + encrypted_data).decode()

    def _decrypt_data(self, encrypted_data, key):
        """Decrypt data with AES-256-GCM"""
        aesgcm = AESGCM(key)
        decoded = base64.urlsafe_b64decode(encrypted_data)
        nonce, ciphertext = decoded[:12], decoded[12:]
        return aesgcm.decrypt(nonce, ciphertext, None).decode()

    def _get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip

    def generate_magnet_link(self, key):
        """Create encrypted magnet-link, including encryption key"""
        shared_db_hash = self._calculate_db_hash()
        ip_address = self._get_local_ip()
        payload = json.dumps({"device_id": self.device_id, 
                              "db_hash": shared_db_hash,
                              "ip": ip_address
                              })

        encrypted_payload = self._encrypt_data(payload, key)
        encrypted_key = base64.urlsafe_b64encode(key).decode() 

        return f"magnet:?data={encrypted_payload}&key={encrypted_key}&dn=CatchFile"

    @staticmethod
    def decode_link(magnet_link):
        """Decode magnet link"""
        try:
            query = magnet_link.split("magnet:?")[1]
            params = dict(item.split("=", 1) for item in query.split("&"))

            encrypted_data = params.get("data")
            encrypted_key = params.get("key")

            if not encrypted_data or not encrypted_key:
                raise ValueError("Invalid magnet link format")

            key = base64.urlsafe_b64decode(encrypted_key)  
            generator = MagnetLinkGenerator()
            decrypted_data = generator._decrypt_data(encrypted_data, key)

            return json.loads(decrypted_data), key  
        except Exception as e:
            raise ValueError(f"Failed to decode magnet link: {e}")

