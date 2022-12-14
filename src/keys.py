from typing import Union
from typing import Tuple

from Crypto.Hash import SHA256
import pbkdf2

from Crypto.Protocol.KDF import scrypt


def and_split(bytes_: bytes) -> Tuple[bytes, bytes]:
    ba1 = bytearray()  # type: bytearray
    ba2 = bytearray()  # type: bytearray

    for byte in bytes_:
        ba1.append(byte & 0xF0)
        ba2.append(byte & 0x0F)
    return (bytes(ba1), bytes(ba2))


def xor_merge(bytes1: bytes, bytes2: bytes) -> bytes:
    if len(bytes1) != len(bytes2):
        raise ValueError("Length mismatch")

    byte_array = bytearray()  # type: bytearray
    for i in range(len(bytes1)):
        byte_array.append(bytes1[i] ^ bytes2[i])
    return bytes(byte_array)


def derive_key(salt: str, passphrase: str) -> Union[int, Tuple[int, bytes]]:
    key_length = 64  # type: int
    t1 = and_split(bytes(salt, "utf-8"))  # type: Tuple[bytes, bytes]
    salt1, salt2 = t1
    t2 = and_split(bytes(passphrase, "utf-8"))  # type: Tuple[bytes, bytes]
    pass1, pass2 = t2

    N = 1<<18 # 1<<18 # == 2**18  == 262144

    scrypt_key = scrypt(
        pass1,
        salt=salt1,
        key_len=key_length,
        N=N,
        r=8,
        p=1,
        num_keys=1,
    )

    pbkdf2_key = pbkdf2.PBKDF2(
        pass2, salt2,
        iterations=1 << 16,
        digestmodule=SHA256).read(key_length)  # type: bytes
    keypair = xor_merge(scrypt_key, pbkdf2_key)  # type: bytes
    secret_exp = int(keypair[0:32].hex(), 16)  # type: int / a number in the range [1, curve_order].
    chain_code = keypair[32:]  # type: bytes
    return secret_exp, chain_code



def main():
    email = input("Enter email: ")  # type: str
    passphrase = input("Enter passphrase: ")  # type: str
    t = derive_key(email, passphrase)  # type: Tuple[int, bytes]
    secret_exp, chain_code = t
    print("Secret exp: {}\nChain code: {}".format(secret_exp, chain_code))


if __name__ == "__main__":
    main()
