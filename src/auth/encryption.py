import os
import base64
import secrets
import logging
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from src.config import settings

logger = logging.getLogger(__name__)


class EncryptionService:
    _instance = None
    _fernet = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EncryptionService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialize_fernet()
        self._initialized = True

    def _initialize_fernet(self) -> None:
        key = settings.app.encryption_key

        if not key:
            key = self._generate_key()
            logger.warning("No encryption key found. Generated new key - add to .env file")
            print(f"\nGenerated ENCRYPTION_KEY={key}")
            print("Add this to your .env file\n")

        try:
            self._fernet = Fernet(key.encode() if isinstance(key, str) else key)
        except Exception as e:
            logger.error(f"Invalid encryption key format: {e}")
            raise ValueError("Invalid encryption key. Must be 32 url-safe base64-encoded bytes")

    @staticmethod
    def _generate_key() -> str:
        return Fernet.generate_key().decode()

    @staticmethod
    def generate_key_from_password(password: str, salt: Optional[bytes] = None) -> tuple:
        if salt is None:
            salt = secrets.token_bytes(16)

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )

        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key.decode(), base64.b64encode(salt).decode()

    def encrypt(self, plaintext: str) -> str:
        if not plaintext:
            return ""

        try:
            encrypted = self._fernet.encrypt(plaintext.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    def decrypt(self, ciphertext: str) -> str:
        if not ciphertext:
            return ""

        try:
            decrypted = self._fernet.decrypt(ciphertext.encode())
            return decrypted.decode()
        except InvalidToken:
            logger.error("Decryption failed: Invalid token or corrupted data")
            raise ValueError("Failed to decrypt: Invalid or corrupted data")
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise

    def is_valid_encrypted(self, ciphertext: str) -> bool:
        if not ciphertext:
            return False

        try:
            self._fernet.decrypt(ciphertext.encode())
            return True
        except Exception:
            return False

    def rotate_encryption(self, ciphertext: str, new_key: str) -> str:
        plaintext = self.decrypt(ciphertext)
        new_fernet = Fernet(new_key.encode())
        return new_fernet.encrypt(plaintext.encode()).decode()


_encryption_service = None


def get_encryption_service() -> EncryptionService:
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


def encrypt(plaintext: str) -> str:
    return get_encryption_service().encrypt(plaintext)


def decrypt(ciphertext: str) -> str:
    return get_encryption_service().decrypt(ciphertext)


def generate_new_key() -> str:
    return EncryptionService._generate_key()
