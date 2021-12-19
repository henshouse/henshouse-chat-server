from enum import Enum
from Crypto.Cipher.AES import MODE_EAX, MODE_GCM


class ANSIColorEnum(Enum):
    grey = 'grey'
    red = 'red'
    green = 'green'
    yellow = 'yellow'
    blue = 'blue'
    magenta = 'magenta'
    cyan = 'cyan'
    white = 'white'


def get_spinner_color() -> str:
    return ANSIColorEnum.yellow.value


def get_color_text() -> str:
    return ANSIColorEnum.yellow.value


def get_encoding() -> str:
    return 'UTF-8'


def get_spinner() -> str:
    return 'dots5'


def get_aes_mode() -> int:
    return MODE_GCM


def get_number_of_size_bytes() -> int:
    return 3


def get_bytesorder() -> str:
    return 'big'


def get_scrypt_salt_size() -> int:
    return 32


def get_scrypt_key_len() -> 64:
    return 64


def get_buffer_size() -> int:
    return 4096
