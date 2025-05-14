from cryptography.hazmat.primitives import cmac
from cryptography.hazmat.primitives.ciphers import algorithms
from cryptography.hazmat.backends import default_backend
import binascii

RZCU_SecurityAES128KEY1 = bytes([
    0x27,0xBB,0x7B,0x9F,0xAA,0x4D,0xEC,0x13,
    0x32,0x7A,0x7C,0x2F,0xF7,0xFA,0xA1,0x9A
])

RZCU_SecurityAES128KEY11 = bytes([
    0xA7,0x34,0xD1,0x55,0xA9,0x6A,0xA4,0x09,
    0xDB,0x93,0x3F,0x74,0x75,0xF9,0x35,0xE9
])

def calculate_cmac(key, seed_hex):
    seed = binascii.unhexlify(seed_hex.replace(' ', ''))
    
    c = cmac.CMAC(algorithms.AES(key), backend=default_backend())
    c.update(seed)
    cmac_result = c.finalize()
    
    return cmac_result.hex().upper()

# 示例使用
if __name__ == "__main__":
    # 输入的种子值（对应00 4F 18 B0 1E AE 78 13 0E 76 76 C1 26 27 46 6F）
    seed_hex = "004F18B01EAE78130E7676C12627466F"
    
    # 计算Level 1的CMAC
    cmac_level1 = calculate_cmac(RZCU_SecurityAES128KEY1, seed_hex)
    print(f"Level 1 CMAC: {cmac_level1}")
    
    # 计算Level 0x11的CMAC
    cmac_level11 = calculate_cmac(RZCU_SecurityAES128KEY11, seed_hex)
    print(f"Level 0x11 CMAC: {cmac_level11}")