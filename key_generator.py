from cryptography.fernet import Fernet


def generate_key():
    key = Fernet.generate_key()
    return key


if __name__ == "__main__":
    print(generate_key(seed="cvimalkumar21@gmai.com"))
    print(generate_key(seed="cvimalkumar21@gmai.com"))
