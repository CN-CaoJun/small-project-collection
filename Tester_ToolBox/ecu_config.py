import json
import os

READ_ECU_MAP = {
    'BDU-CLient': 
    {
        'RXID': '0x738',
        'TXID': '0x730'
    }
}

class ECUMapReader:
    def __init__(self, config_file='DiagnosticPack_EcuMap.json'):
        self.config_file = config_file
        self.load_ecu_map()
    
    def load_ecu_map(self):
        """Load ECU mapping configuration from JSON file to READ_ECU_MAP"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                    # Clear existing READ_ECU_MAP
                    READ_ECU_MAP.clear()
                    # Update READ_ECU_MAP
                    READ_ECU_MAP.update(config_data)
                    return True
            return False
        except Exception as e:
            print(f"Failed to read ECU mapping configuration: {str(e)}")
            return False
    
    def get_read_ecu_map(self):
        """Get current READ_ECU_MAP"""
        return READ_ECU_MAP
    
    def get_ecu_ids(self, ecu_name):
        """
        Get ID configuration for specified ECU
        :param ecu_name: ECU name
        :return: ID configuration dictionary or None
        """
        return READ_ECU_MAP.get(ecu_name, None)