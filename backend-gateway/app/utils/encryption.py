import base64
import hashlib
from cryptography.fernet import Fernet

def _derive_key(key: str) -> bytes:
    """
    Derives a 32-byte url-safe base64 key from the given string key using SHA-256.
    """
    key_hash = hashlib.sha256(key.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(key_hash)

def encrypt_data(data: str, key: str) -> str:
    """
    Encrypts cleartext data using Fernet (AES-128 in CBC mode) with a derived key.
    Returns the encrypted token as a string.
    """
    f = Fernet(_derive_key(key))
    encrypted_bytes = f.encrypt(data.encode('utf-8'))
    return encrypted_bytes.decode('utf-8')

def decrypt_data(encrypted_data_token: str, key: str) -> str:
    """
    Decrypts the Fernet token using the derived key.
    """
    f = Fernet(_derive_key(key))
    decrypted_bytes = f.decrypt(encrypted_data_token.encode('utf-8'))
    return decrypted_bytes.decode('utf-8')
