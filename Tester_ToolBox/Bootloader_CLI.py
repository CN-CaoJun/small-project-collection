import sys
import os
import argparse
import time

sys.path.insert(0, os.path.abspath("reference_modules/python-can"))
sys.path.insert(0, os.path.abspath("reference_modules/python-can-isotp"))
sys.path.insert(0, os.path.abspath("reference_modules/python-udsoncan"))

import can
from can.interface import Bus
import isotp
import udsoncan
from can.interfaces.vector import canlib
from udsoncan.connections import PythonIsoTpConnection
from udsoncan.client import Client
import udsoncan.configs
from BootloaderPackFlash import FlashingProcess
from BootloaderPack import FlexRawData
class BootloaderCLI:
    def __init__(self):
        self.can_bus = None
        self.notifier = None
        self.stack = None
        self.stack_func = None
        self.uds_client = None
        self.uds_client_func = None
        self.flash_process = None
        self.flash_config = {}
        
    def log(self, message):
        """Print log message with timestamp"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")
        
    def connect_vector_can(self, app_name:str, channel:int):
        """Connect to Vector CAN interface"""
        """Create Vector bus instance"""
        # Set application name
        can.rc['app_name'] = app_name
        can.rc['channel'] = channel - 1
        
        can.rc['interface'] = 'vector'
        can.rc['bustype'] = 'vector'
        can.rc['fd'] = True  
        can.rc['bitrate'] = 500000
        can.rc['data_bitrate'] = 2000000
        can.rc['tseg1_abr'] = 63
        can.rc['tseg2_abr'] = 16
        can.rc['sjw_abr'] = 16
        can.rc['sam_abr'] = 1
        can.rc['tseg1_dbr'] = 13
        can.rc['tseg2_dbr'] = 6
        can.rc['sjw_dbr'] = 6
                
        try:
            self.can_bus = Bus()
            return True
        except Exception as e:
            print(f"Failed to initialize Vector bus: {e}")
            return False
    
    def create_isotp_layer(self, tx_id:int, rx_id:int, func_tx_id=0x7DF, func_rx_id=0x7DE):
        """Create ISO-TP layer"""
        try:
            if not self.can_bus:
                self.log("Error: CAN bus not initialized")
                return False
                
            # Configure ISO-TP parameters
            isotp_params = {
                 'stmin': 0,
                'blocksize': 0,
                'override_receiver_stmin': None,
                'wftmax': 4,
                'tx_data_length': 64,    
                'tx_data_min_length': 8,
                'tx_padding': 0xAA,
                'rx_flowcontrol_timeout': 1000,
                'rx_consecutive_frame_timeout': 100,
                'can_fd': True,
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
    
    def flash_target_node(self, flash_config:dict, zone_type:str, cal_is_must:int):
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
            self.log(f"Starting flash process for zone: {zone_type}")
            self.log(f"CAL is must: {cal_is_must}")
            
            success = self.flash_process.execute_flashing_sequence(
                    zone_type = zone_type,
                    cal_is_must = cal_is_must,
                    flash_config = flash_config,
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
    """Main function to execute the bootloader CLI tool"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Bootloader CLI Tool for Target Node upgrade')
    parser.add_argument('--app-name', default='CANalyzer', help='Vector CAN application name')
    parser.add_argument('--channel', type=int, default=1, help='Vector CAN channel (default: 0)')
    parser.add_argument('--zone-type', default='RZCU', choices=['RZCU', 'LZCU'], help='Target Node Select')
    parser.add_argument('--sbl-file', required=True, help='Path to SBL (Secondary Bootloader) file')
    parser.add_argument('--app-file', required=True, help='Path to APP (Application) file')
    parser.add_argument('--cal1-file', default=None, help='Path to CAL 1 file')
    parser.add_argument('--cal2-file', default=None,help='Path to CAL 2 file')
    parser.add_argument('--cal-is-must', action='store_true', help='CAL is mandatory')
    
    args = parser.parse_args()
    
    # Set TX ID and RX ID based on zone type
    if args.zone_type == 'RZCU':
        tx_id = 0x736
        rx_id = 0x7B6
    elif args.zone_type == 'LZCU':
        tx_id = 0x734
        rx_id = 0x7B4
    else:
        raise ValueError(f"Unsupported zone type: {args.zone_type}")
    
    print(f"Zone Type: {args.zone_type}")
    print(f"TX ID: 0x{tx_id:03X}")
    print(f"RX ID: 0x{rx_id:03X}")
    print(f"If CAL is must: {args.cal_is_must}")
    
    # Initialize the bootloader CLI instance
    cli = BootloaderCLI()
        
    try:
        # ========================================
        # PHASE 1: HARDWARE INITIALIZATION
        # ========================================
        
        # Step 1.1: Initialize Vector CAN hardware interface
        cli.log("------------------------------------------------")
        cli.log("Phase 1: Hardware Initialization")
        cli.log("Step 1.1: Initializing Vector CAN hardware interface...")
        cli.log(f"  - {args.app_name} CAN {args.channel}")
        
        if not cli.connect_vector_can(args.app_name, args.channel):
            cli.log("ERROR: Failed to initialize Vector CAN hardware")
            return 1
        
        cli.log("SUCCESS: Vector CAN hardware initialized successfully")
        time.sleep(3)  # Allow hardware to stabilize
        
        # Step 1.2: Verify CAN bus connectivity
        cli.log("Step 1.2: Verifying CAN bus connectivity...")
        if not cli.can_bus:
            cli.log("ERROR: CAN bus object is not available")
            return 1
        
        cli.log("SUCCESS: CAN bus connectivity verified")
        time.sleep(2)  # Brief pause for stability
        
        # ========================================
        # PHASE 2: COMMUNICATION LAYER SETUP
        # ========================================
        
        # Step 2.1: Configure ISO-TP transport layer parameters
        cli.log("------------------------------------------------")
        cli.log("Phase 2: Communication Layer Setup")
        cli.log("Step 2.1: Configuring ISO-TP transport layer...")
        
        if not cli.create_isotp_layer(tx_id, rx_id):
            cli.log("ERROR: Failed to configure ISO-TP transport layer")
            return 1
        
        cli.log("SUCCESS: ISO-TP transport layer configured successfully")
        time.sleep(2)  # Allow transport layer to initialize
        
        # Step 2.2: Establish ISO-TP communication stacks
        cli.log("Step 2.2: Establishing ISO-TP communication stacks...")
        if not cli.stack or not cli.stack_func:
            cli.log("ERROR: ISO-TP stacks are not properly initialized")
            return 1
        
        cli.log("SUCCESS: ISO-TP communication stacks established")
        time.sleep(2)  # Ensure stacks are ready
        
        # ========================================
        # PHASE 3: UDS CLIENT INITIALIZATION
        # ========================================
        
        # Step 3.1: Create UDS client connections
        cli.log("------------------------------------------------")
        cli.log("Phase 3: UDS Client Initialization")
        cli.log("Step 3.1: Creating UDS client connections...")
        cli.log("  - Configuring data identifiers and timeout parameters")
        cli.log("  - Setting up physical and functional addressing clients")
        
        if not cli.create_uds_client():
            cli.log("ERROR: Failed to create UDS client connections")
            return 1
        
        cli.log("SUCCESS: UDS client connections created successfully")
        time.sleep(2)  # Allow clients to initialize
        
        # Step 3.2: Verify UDS client readiness
        cli.log("Step 3.2: Verifying UDS client readiness...")
        if not cli.uds_client or not cli.uds_client_func:
            cli.log("ERROR: UDS clients are not properly initialized")
            return 1
        
        cli.log("SUCCESS: UDS clients are ready for communication")
        time.sleep(2)  # Final preparation pause
        
        # ========================================
        # PHASE 4: FIRMWARE FLASHING PROCESS
        # ========================================
        
        # Step 4.1: Initialize flashing process
        cli.log("------------------------------------------------")
        cli.log("Phase 4: Firmware Flashing Process")
        cli.log("Step 4.1: Initializing firmware flashing process...")
        cli.log(f"  - Target Zone: {args.zone_type}")
        cli.log(f"  - CAL Mandatory: {args.cal_is_must}")
        
        # Step 4.2: Execute firmware flashing sequence
        cli.log("Step 4.2: Executing firmware flashing sequence...")
        # Prepare flash configuration with firmware files
        flash_config = {
            'sbl_hex': args.sbl_file,
            'app_hex': args.app_file
        }
        
        # Add CAL files to config if CAL is mandatory
        if args.cal_is_must:
            flash_config.update({
                'cal1_hex': args.cal1_file,
                'cal2_hex': args.cal2_file
            })
        
        # Print flash configuration details
        cli.log("Flash Fiels Details:")
        for key, value in flash_config.items():
            cli.log(f"  - {key}: {value}")
        cli.log("----------------------------------------")
        
        if not cli.flash_target_node(flash_config, args.zone_type, args.cal_is_must):
            cli.log("ERROR: Firmware flashing process failed")
            return 1
        
        # Step 4.3: Verify flashing completion
        cli.log("Step 4.3: Verifying flashing completion...")
        cli.log("SUCCESS: Firmware flashing process completed successfully")
        
        # ========================================
        # COMPLETION
        # ========================================
        
        cli.log("========================================")
        cli.log("ALL OPERATIONS COMPLETED SUCCESSFULLY!")
        cli.log("Target node has been successfully updated")
        cli.log("========================================")
        return 0
        
    except KeyboardInterrupt:
        cli.log("========================================")
        cli.log("OPERATION INTERRUPTED BY USER (Ctrl+C)")
        cli.log("Cleaning up resources...")
        cli.log("========================================")
        return 1
    except Exception as e:
        cli.log("========================================")
        cli.log(f"UNEXPECTED ERROR OCCURRED: {str(e)}")
        cli.log("Please check the error details above")
        cli.log("========================================")
        return 1
    finally:
        # Always perform cleanup regardless of success or failure
        cli.log("Performing final cleanup...")
        cli.cleanup()
        cli.log("Cleanup completed")

if __name__ == "__main__":
    sys.exit(main())

