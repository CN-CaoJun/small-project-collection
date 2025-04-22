import json
import os

# 默认的ECU ID映射配置
DEFAULT_ECU_MAP = {
    'IMS': {'RXID': 0x759, 'TXID': 0x749}, 
    'SMLS': {'RXID': 0x739, 'TXID': 0x731}, 
    'HCML': {'RXID': 0x748, 'TXID': 0x740}, 
    'HCMR': {'RXID': 0x749, 'TXID': 0x741}, 
    'RCM':  {'RXID': 0x74A, 'TXID': 0x742}, 
    'BMS':  {'RXID': 0x7EA, 'TXID': 0x7E2}, 
    'PWR':  {'RXID': 0x7EB, 'TXID': 0x7E3}, 
    'OCDC': {'RXID': 0x7ED, 'TXID': 0x7E5}, 
    'TMM':  {'RXID': 0x7EE, 'TXID': 0x7E6}, 
    'HCU':  {'RXID': 0x7EF, 'TXID': 0x7E7}, 
    'IBRS': {'RXID': 0x718, 'TXID': 0x710}, 
    'VCU':  {'RXID': 0x7E9, 'TXID': 0x7E1}
}

class ECUConfig:
    def __init__(self, config_file='ecu_config.json'):
        self.config_file = config_file
        self.ecu_map = self.load_config()
    
    def load_config(self):
        """从JSON文件加载配置，如果文件不存在则使用默认配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            return DEFAULT_ECU_MAP
        except Exception as e:
            print(f"加载配置文件失败: {str(e)}")
            return DEFAULT_ECU_MAP
    
    def save_config(self, config=None):
        """保存配置到JSON文件"""
        try:
            if config is None:
                config = self.ecu_map
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
            return True
        except Exception as e:
            print(f"保存配置文件失败: {str(e)}")
            return False
    
    def get_ecu_map(self):
        """获取ECU映射表"""
        return self.ecu_map
    
    def update_ecu_map(self, new_map):
        """更新ECU映射表并保存"""
        self.ecu_map = new_map
        return self.save_config()