#!/usr/bin/env python3
import sys
import os
import argparse
import time

sys.path.insert(0, os.path.abspath("reference_modules/python-can"))
sys.path.insert(0, os.path.abspath("reference_modules/python-can-isotp"))
sys.path.insert(0, os.path.abspath("reference_modules/python-udsoncan"))

import can
import isotp
import udsoncan
from can.interfaces.vector import canlib
from udsoncan.connections import PythonIsoTpConnection
from udsoncan.client import Client
import udsoncan.configs
from BootloaderPackFlash import FlashingProcess

class FlexRawData:
    """Flexible raw data codec for UDS data identifiers"""
    def __init__(self, length):
        self.length = length
    
    def encode(self, data):
        if isinstance(data, bytes):
            return data[:self.length]
        elif isinstance(data, str):
            return data.encode('utf-8')[:self.length]
        else:
            return bytes(data)[:self.length]
    
    def decode(self, data):
        return data

class BootloaderCLI:
    def __init__(self):
        self.can_bus = None
        self.notifier = None
        self.stack = None
        self.stack_func = None
        self.uds_client = None
        self.uds_client_func = None
        self.flash_process = None
        
    def log(self, message):
        """Print log message with timestamp"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")
        
    def connect_vector_can(self, app_name="Bootloader_CLI", channel=0):
        """Connect to Vector CAN interface"""
        try:
            # Set application name
            can.rc['app_name'] = app_name
            
            # Initialize Vector CAN
            canlib.xldriver.xlOpenDriver()
            vector_configs = canlib.get_channel_configs()
            
            if not vector_configs:
                self.log("Error: No Vector CAN devices found")
                return False
                
            # Use the first available Vector device
            config = vector_configs[0]
            self.log(f"Using Vector device: {config.name} (Serial: {config.serial_number})")
            
            # Create CAN bus
            self.can_bus = canlib.VectorBus(
                channel=channel,
                fd=False,
                bitrate=500000,
                tseg1_abr=63,
                tseg2_abr=16,
                sjw_abr=16
            )
            
            self.log(f"Vector CAN connected successfully on channel {channel}")
            return True
            
        except Exception as e:
            self.log(f"Failed to connect Vector CAN: {str(e)}")
            return False
    
    def create_isotp_layer(self, tx_id=0x736, rx_id=0x7b6, func_tx_id=0x7DF, func_rx_id=0x7DE):
        """Create ISO-TP layer"""
        try:
            if not self.can_bus:
                self.log("Error: CAN bus not initialized")
                return False
                
            # Configure ISO-TP parameters
            isotp_params = {
                'stmin': 0,
                'blocksize': 0,
                'tx_padding': 0x00,
                'override_receiver_stmin': None,
                'wftmax': 4,
                'tx_data_length': 8,
                'tx_data_min_length': 8,
                'rx_flowcontrol_timeout': 1000,
                'rx_consecutive_frame_timeout': 100,
                'can_fd': False,
                'max_frame_size': 4095,
                'bitrate_switch': False,
                'rate_limit_enable': False,
                'listen_mode': False,
                'blocking_send': False
            }
            
            # Create notifier
            self.notifier = can.Notifier(self.can_bus, [])
            
            # Create physical addressing ISO-TP stack
            tp_addr = isotp.Address(
                isotp.AddressingMode.Normal_11bits,
                txid=tx_id,
                rxid=rx_id
            )
            
            self.stack = isotp.NotifierBasedCanStack(
                bus=self.can_bus,
                notifier=self.notifier,
                address=tp_addr,
                params=isotp_params
            )
            
            # Create functional addressing ISO-TP stack
            tp_addr_func = isotp.Address(
                isotp.AddressingMode.Normal_11bits,
                txid=func_tx_id,
                rxid=func_rx_id
            )
            
            self.stack_func = isotp.NotifierBasedCanStack(
                bus=self.can_bus,
                notifier=self.notifier,
                address=tp_addr_func,
                params=isotp_params
            )
            
            self.log(f"ISO-TP layer created - Physical: TX=0x{tx_id:03X}, RX=0x{rx_id:03X}")
            self.log(f"ISO-TP layer created - Functional: TX=0x{func_tx_id:03X}, RX=0x{func_rx_id:03X}")
            return True
            
        except Exception as e:
            self.log(f"Failed to create ISO-TP layer: {str(e)}")
            return False
    
    def create_uds_client(self):
        """Create UDS client"""
        try:
            if not self.stack or not self.stack_func:
                self.log("Error: ISO-TP stack not initialized")
                return False
                
            # Create connections
            conn = PythonIsoTpConnection(self.stack)
            conn_func = PythonIsoTpConnection(self.stack_func)
            
            # Configure UDS client
            uds_config = udsoncan.configs.default_client_config.copy()
            uds_config['data_identifiers'] = {
                'default': '>H',
                0x7705: FlexRawData(30),
                0xF15A: FlexRawData(9),
                0xF184: FlexRawData(19),
                0xF0F0: FlexRawData(1),
                0x4611: FlexRawData(32),
                0x5558: FlexRawData(32),
            }
            
            # Modify timeout configuration
            uds_config['p2_timeout'] = 5
            uds_config['p2_star_timeout'] = 5
            uds_config['request_timeout'] = 5
            uds_config['session_timing'] = {
                'p2_server_max': 5,
                'p2_star_server_max': 5
            }
            
            # Create UDS clients
            self.uds_client = Client(conn, config=uds_config)
            self.uds_client_func = Client(conn_func, config=uds_config)
            
            self.log("UDS clients created successfully (Physical & Functional)")
            return True
            
        except Exception as e:
            self.log(f"Failed to create UDS client: {str(e)}")
            return False
    
    def flash_target_node(self, firmware_folder, zone_type="RZCU", cal_is_must=False):
        """Flash target node using FlashingProcess methods"""
        try:
            if not self.uds_client or not self.uds_client_func:
                self.log("Error: UDS clients not initialized")
                return False
                
            # Create FlashingProcess instance
            self.flash_process = FlashingProcess(
                uds_client=self.uds_client,
                uds_client_func=self.uds_client_func,
                trace_handler=self.log
            )
            
            # Set firmware folder
            self.flash_process.firmware_folder = firmware_folder
            
            self.log(f"Starting flash process for zone: {zone_type}")
            self.log(f"Firmware folder: {firmware_folder}")
            self.log(f"CAL is must: {cal_is_must}")
            
            # Execute flashing process with 10-second intervals
            success = self.flash_process.execute_flashing_process(
                zone_type=zone_type,
                cal_is_must=cal_is_must
            )
            
            if success:
                self.log("Flash process completed successfully!")
            else:
                self.log("Flash process failed!")
                
            return success
            
        except Exception as e:
            self.log(f"Flash process error: {str(e)}")
            return False
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            if self.notifier:
                self.notifier.stop()
            if self.can_bus:
                self.can_bus.shutdown()
            self.log("Resources cleaned up successfully")
        except Exception as e:
            self.log(f"Cleanup error: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Bootloader CLI Tool for Target Node Flashing')
    parser.add_argument('--app-name', default='Bootloader_CLI', help='Vector CAN application name')
    parser.add_argument('--channel', type=int, default=0, help='Vector CAN channel (default: 0)')
    parser.add_argument('--tx-id', type=lambda x: int(x, 0), default=0x736, help='ISO-TP TX ID (default: 0x736)')
    parser.add_argument('--rx-id', type=lambda x: int(x, 0), default=0x7b6, help='ISO-TP RX ID (default: 0x7b6)')
    parser.add_argument('--firmware-folder', required=True, help='Path to firmware folder')
    parser.add_argument('--zone-type', default='RZCU', choices=['RZCU', 'LZCU', 'FZCU'], help='Zone type (default: RZCU)')
    parser.add_argument('--cal-is-must', action='store_true', help='CAL is mandatory')
    
    args = parser.parse_args()
    
    cli = BootloaderCLI()
    
    try:
        # Step 1: Connect to Vector CAN
        cli.log("Step 1: Connecting to Vector CAN...")
        if not cli.connect_vector_can(args.app_name, args.channel):
            return 1
        time.sleep(10)  # 10-second interval
        
        # Step 2: Create ISO-TP layer
        cli.log("Step 2: Creating ISO-TP layer...")
        if not cli.create_isotp_layer(args.tx_id, args.rx_id):
            return 1
        time.sleep(10)  # 10-second interval
        
        # Step 3: Create UDS client
        cli.log("Step 3: Creating UDS client...")
        if not cli.create_uds_client():
            return 1
        time.sleep(10)  # 10-second interval
        
        # Step 4: Flash target node
        cli.log("Step 4: Starting flash process...")
        if not cli.flash_target_node(args.firmware_folder, args.zone_type, args.cal_is_must):
            return 1
            
        cli.log("All operations completed successfully!")
        return 0
        
    except KeyboardInterrupt:
        cli.log("Operation interrupted by user")
        return 1
    except Exception as e:
        cli.log(f"Unexpected error: {str(e)}")
        return 1
    finally:
        cli.cleanup()

if __name__ == "__main__":
    sys.exit(main())

