from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import os

def enc_file(file, shared_key):
    nonce = os.urandom(12)
    cipher = Cipher(algorithms.AES(shared_key), modes.GCM(nonce))
    encryptor = cipher.encryptor()
    with open(file, 'rb') as f:
        plain = f.read()
    ciphertext = encryptor.update(plain) + encryptor.finalize()
    return nonce + ciphertext + encryptor.tag

def dec_file(enc_data, shared_key):
    nonce = enc_data[:12]
    ciphertext = enc_data[12:-16]
    tag = enc_data[-16:]

    cipher = Cipher(algorithms.AES(shared_key), modes.GCM(nonce, tag))
    decryptor = cipher.decryptor()
    return decryptor.update(ciphertext) + decryptor.finalize()