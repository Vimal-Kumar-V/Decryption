from cryptography.fernet import Fernet

from key_generator import generate_key


def encrypt_file(file_content):
    key = generate_key()
    encryptor = Fernet(key)
    return encryptor.encrypt(file_content), key

def decrypt_file(file, key):
    decryptor = Fernet(key)
    return decryptor.decrypt(file)
