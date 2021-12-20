from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
from Crypto import Random

from constants import *


def generate_keys(server=False):
    # print('a')
    prv_key = RSA.generate(RSA_MODULUS, Random.new().read)
    # print('b')
    pbl_key = prv_key.publickey()
    # print('c')
    return prv_key, pbl_key


def encrypt(msg: str, pbl_key: RSA.RsaKey):
    encryptor = PKCS1_OAEP.new(pbl_key)
    msg_bytes = bytes(msg, ENCODING)
    encrypted = encryptor.encrypt(msg_bytes)
    return encrypted


def decrypt(encrypted: bytes, prv_key: RSA.RsaKey):
    decryptor = PKCS1_OAEP.new(prv_key)
    msg_bytes = decryptor.decrypt(encrypted)
    msg = str(msg_bytes, ENCODING)
    return msg


def import_key(key_msg: bytes):
    return RSA.import_key(key_msg)
