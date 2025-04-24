class SecurityKeyAlgorithm:
    """安全密钥算法计算类"""
    SECURITY_KKEY_L2 = 0x0000CDCA  # Level2算法密钥
    SECURITY_KKEY_L4 = 0x00001D5C  # Level4算法密钥

    @staticmethod
    def compute_level2(seed: int, keyk: int) -> int:
        """Level2算法实现"""
        temp_key = (seed ^ keyk) & 0xFFFFFFFF
        for _ in range(32):
            if temp_key & 0x00000001:
                temp_key = (temp_key >> 1) ^ seed
            else:
                temp_key = (temp_key >> 1) ^ keyk
            temp_key &= 0xFFFFFFFF  # 保持32位
        return temp_key

    @staticmethod
    def compute_level4(seed: int, keyk: int) -> int:
        """Level4算法实现"""
        temp_key = (seed ^ keyk) & 0xFFFFFFFF
        for _ in range(32):
            # 循环左移7位
            temp_key = ((temp_key << 7) | (temp_key >> 25)) & 0xFFFFFFFF
            temp_key ^= keyk
            temp_key &= 0xFFFFFFFF
        return temp_key

    @staticmethod
    def hex_str_to_int(hex_str: str) -> int:
        """将十六进制字符串转换为整数"""
        return int(hex_str.replace(' ', ''), 16)