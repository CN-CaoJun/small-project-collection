import json
import os

DEFAULT_ECU_MAP = {
    'None': {'RXID': 0x759, 'TXID': 0x749}
}

READ_ECU_MAP = {
    
}

class ECUMapReader:
    def __init__(self, config_file='DiagnosticPack_EcuMap.json'):
        self.config_file = config_file
        self.load_ecu_map()
    
    def load_ecu_map(self):
        """从JSON文件加载ECU映射配置到READ_ECU_MAP"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                    # 清空现有的READ_ECU_MAP
                    READ_ECU_MAP.clear()
                    # 更新READ_ECU_MAP
                    READ_ECU_MAP.update(config_data)
                    return True
            return False
        except Exception as e:
            print(f"读取ECU映射配置失败: {str(e)}")
            return False
    
    def get_read_ecu_map(self):
        """获取当前READ_ECU_MAP"""
        return READ_ECU_MAP
    
    def get_ecu_ids(self, ecu_name):
        """获取指定ECU的ID配置"""
        return READ_ECU_MAP.get(ecu_name, None)