import sys
import os

sys.path.insert(0, os.path.abspath("reference_modules/python-can"))
sys.path.insert(0, os.path.abspath("reference_modules/python-can-isotp"))
sys.path.insert(0, os.path.abspath("reference_modules/python-udsoncan"))

import can
from can.interfaces.vector import canlib, xlclass, xldefine
import isotp
import time
import json
import threading
import logging

class CANBusFactory:
    """CAN Bus Factory class for creating different types of CAN interfaces"""
    
    def __init__(self, channel_type, is_fd,**kwargs):
        """
        Initialize CAN Bus Factory
        :param channel_type: CAN interface type ('pcan'/'vector'/'slcan'/'socketcan')
        :param kwargs: Interface specific configuration parameters
        """
        self.channel_type = channel_type
        self.config = kwargs
        self.can_bus = None
        self.notifier = None
        self.is_fd = is_fd
        
    def create_bus(self):
        """
        Create CAN bus instance based on configuration
        :return: (can_bus, notifier) tuple
        """
        if self.channel_type == 'pcan':
            self._create_pcan_bus()
        elif self.channel_type == 'vector':
            self._create_vector_bus()
        elif self.channel_type == 'virtualvector':
            self._create_virtual_vector_bus()
        elif self.channel_type == 'slcan':
            self._create_slcan_bus()
        elif self.channel_type == 'socketcan':
            self._create_socketcan_bus()
        else:
            raise ValueError(f"Unsupported CAN interface type: {self.channel_type}")
            
        self.notifier = can.Notifier(self.can_bus, [])
        return self.can_bus, self.notifier
        
    def _create_pcan_bus(self):
        """Create PCAN bus instance"""
        from can.interfaces.pcan import PcanBus
        
        # PCAN channel mapping
        pcan_channel_map = {
            0x51: "PCAN_USBBUS1",
            0x52: "PCAN_USBBUS2",
            0x53: "PCAN_USBBUS3",
            0x54: "PCAN_USBBUS4"
        }
        
        handle = self.config.get('handle', 0x51)  # Default to PCAN_USBBUS1
        if handle not in pcan_channel_map:
            raise ValueError(f"Unsupported PCAN channel handle: 0x{handle:02X}")
            
        self.can_bus = PcanBus(
            channel=pcan_channel_map[handle],
            bitrate=self.config.get('bitrate', 500000),
            fd=self.config.get('fd', False)
        )
        
    def _create_vector_bus(self):
        """Create Vector bus instance"""
        can.rc['interface'] = 'vector'
        can.rc['bustype'] = 'vector'
        can.rc['channel'] = '0'
        can.rc['app_name'] = 'Python_ISOTP_Client'
        can.rc['fd'] = False  
        can.rc['bitrate'] = 500000
        can.rc['sjw_abr'] = 16
        can.rc['tseg1_abr'] = 63
        can.rc['tseg2_abr'] = 16
    
        try:
            self.can_bus = can.Bus()
            print(f"Vector bus initialized successfully in {'CANFD' if self.is_fd else 'CAN'} mode.")
        except Exception as e:
            print(f"Failed to initialize Vector bus: {e}")
            raise
    
    def _create_virtual_vector_bus(self):
        """Create Vector bus instance"""
        try:
            if self.is_fd:
                self.can_bus = canlib.VectorBus(
                    channel = 0,
                    fd=True,
                    bitrate=500000,
                    data_bitrate=2000000,
                    tseg1_abr=63,
                    tseg2_abr=16,
                    sjw_abr=16,
                    sam_abr=1,
                    tseg1_dbr=13,
                    tseg2_dbr=6,
                    sjw_dbr=6,
                )
            else:
                self.can_bus = canlib.VectorBus(
                        channel = 0,  
                        fd=False,
                        bitrate=500000,
                        tseg1_abr=63,
                        tseg2_abr=16,
                        sjw_abr=16)
            print("[CANBUS] Default choose Virtual Channel 1")  
            print(f"[CANBUS] Virtual Vector bus initialized successfully in {'CANFD' if self.is_fd else 'CAN'} mode.")
        except Exception as e:
            print(f"Failed to initialize Vector bus: {e}")
            raise

    def _create_slcan_bus(self):
        """Create SLCAN bus instance"""
        from can.interfaces.slcan import slcanBus
        
        self.can_bus = slcanBus(
            channel=self.config.get('port', 'COM34'),
            bitrate=self.config.get('bitrate', 500000)
        )
        
    def _create_socketcan_bus(self):
        """Create SocketCAN bus instance"""
        self.can_bus = can.Bus(
            interface='socketcan',
            channel=self.config.get('channel', 'vcan0'),
            bitrate=self.config.get('bitrate', 500000),
            fd=self.config.get('fd', False)
        )

class ISOTPLayer:
    """ISOTP protocol layer wrapper"""
    def __init__(self, bus, notifier, txid, rxid, is_fd):
        """
        Initialize ISOTP layer
        :param bus: CAN bus instance
        :param notifier: CAN notifier
        :param txid: Transmission ID
        :param rxid: Reception ID
        :param is_fd: Whether to use CANFD
        """
        # 配置日志
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('isotp_layer.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        # Configure ISOTP parameters based on CAN type
        if is_fd:
            self.params = {
                'stmin': 0,
                'blocksize': 0,
                'override_receiver_stmin': None,
                'wftmax': 4,
                'tx_data_length': 64,     # 增加到64字节以支持CANFD
                'tx_data_min_length': 8,
                'tx_padding': 0x00,
                'rx_flowcontrol_timeout': 1000,
                'rx_consecutive_frame_timeout': 100,
                'can_fd': True,           # 启用CANFD
                'max_frame_size': 4095,
                'bitrate_switch': False,
                'rate_limit_enable': False,
                'listen_mode': False,
                'blocking_send': False   
            }
        else:
            self.params = {
                'stmin': 0,
                'blocksize': 0,
                'override_receiver_stmin': None,
                'wftmax': 4,
                'tx_data_length': 8,      # 标准CAN使用8字节
                'tx_data_min_length': 8,
                'tx_padding': 0x00,
                'rx_flowcontrol_timeout': 1000,
                'rx_consecutive_frame_timeout': 100,
                'can_fd': False,          # 禁用CANFD
                'max_frame_size': 4095,
                'bitrate_switch': False,
                'rate_limit_enable': False,
                'listen_mode': False,
                'blocking_send': False   
            }

        # Print ISOTP layer initialization status
        print(f"[ISOTP] Initializing {'CANFD' if is_fd else 'Standard CAN'} transport layer")
        print(f"[ISOTP] TX ID: 0x{txid:03X}, RX ID: 0x{rxid:03X}")
        print(f"[ISOTP] Parameters:")
        print(f"[ISOTP]   - Data Length: {self.params['tx_data_length']} bytes")
        print(f"[ISOTP]   - Flow Control Timeout: {self.params['rx_flowcontrol_timeout']} ms")
        print(f"[ISOTP]   - Consecutive Frame Timeout: {self.params['rx_consecutive_frame_timeout']} ms")

        self.tp_addr = isotp.Address(
            isotp.AddressingMode.Normal_11bits,
            txid=txid,
            rxid=rxid
        )

        self.layer = isotp.NotifierBasedCanStack(
            bus=bus,
            notifier=notifier,
            address=self.tp_addr,
            params=self.params
        )

    def start(self):
        """Start ISOTP layer"""
        self.layer.start()
        print("[ISOTP] Protocol stack started")

    def stop(self):
        """Stop ISOTP layer"""
        self.layer.stop()
        print("[ISOTP] Protocol stack stopped")

    def send(self, payload):
        """Send data"""
        self.layer.send(payload)

    def receive(self, timeout=1):
        """Receive data"""
        return self.layer.recv(timeout=timeout)

class Config:
    def load_case(self, config_file):
        try:
            with open(config_file, "r") as fd:
                self.config = json.load(fd)
                print(f"[Config] Successfully loaded test case file: {config_file}")  # Add success message
                return self.config
        except:
            print("test case file parse failed")
            return None
    def find_case(self, req):
        for case in self.config:
            if case["req"].upper() == req:
                return case["res"]
        return None

class UDSResponder:
    """UDS Response Handler"""
    def __init__(self, test_case_file='BDU_response.json'):
        """
        Initialize UDS responder
        :param test_case_file: Test case file
        """
        self.cfg = Config()
        if not self.cfg.load_case(test_case_file):
            raise FileNotFoundError(f"Failed to load test case file: {test_case_file}")
        self.running = False
        self.receive_thread = None
        self.isotp_layer = None
        
    def start_receiving(self, isotp_layer):
        """Start receiving thread"""
        self.isotp_layer = isotp_layer
        self.running = True
        self.receive_thread = threading.Thread(target=self._receive_loop)
        self.receive_thread.daemon = True
        self.receive_thread.start()
        
    def stop_receiving(self):
        """Stop receiving thread"""
        self.running = False
        if self.receive_thread:
            self.receive_thread.join()
            
    def _receive_loop(self):
        """Receiving loop"""
        while self.running:
            try:
                payload = self.isotp_layer.receive(timeout=0.50)
                if payload:
                    response = self.process_request(payload)
                    self.isotp_layer.send(response)
            except Exception as e:
                print(f"[UDS] Reception processing error: {e}")
            time.sleep(0.01)

    def process_request(self, payload):
        """
        Process UDS request and generate response
        :param payload: Request data
        :return: Response data
        """
        hex_req = payload.hex().upper()
        current_time = time.time()
        milliseconds = int((current_time - int(current_time)) * 1000)
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(current_time)) + f'.{milliseconds:03d}'
        print(f"[UDS] [{timestamp}] Received request: {hex_req}")
        
        if len(payload) == 516 and payload[0] == 0x31:  # Check if first byte is 0x36
            if payload[1] == 0x01: 
                if payload[2] == 0xD0 and payload[3] == 0x02:
                    return bytes([0x71,0x01,0xD0,0x02,0x00])  # Return 0x76 and sequence number
            else:
                return self._create_negative_response(0x31, 0x11)  # Return length error if no sequence number
        
        # Handle transfer data request
        if len(payload) > 0 and payload[0] == 0x36:  # Check if first byte is 0x36
            if len(payload) > 1:
                seq_number = payload[1]  # Get second byte as sequence number
                return bytes([0x76, seq_number])  # Return 0x76 and sequence number
            else:
                return self._create_negative_response(0x36, 0x13)  # Return length error if no sequence number
        
        # Handle other requests
        response_hex = self.cfg.find_case(hex_req)
        if response_hex:
            current_time = time.time()
            milliseconds = int((current_time - int(current_time)) * 1000)
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(current_time)) + f'.{milliseconds:03d}'
            print(f"[UDS] [{timestamp}] Sending response: {response_hex}")
            return bytes.fromhex(response_hex)

        # If no matching response found, return negative response
        nrc_response = self._create_negative_response(payload[0], 0x11)
        current_time = time.time()
        milliseconds = int((current_time - int(current_time)) * 1000)
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(current_time)) + f'.{milliseconds:03d}'
        print(f"[UDS] [{timestamp}] Sending negative response: {nrc_response.hex().upper()}")
        return nrc_response

    def _create_negative_response(self, sid, nrc):
        """Generate negative response"""
        return bytes([0x7F, sid, nrc])

def main():
    """Main function example"""
    try:
        # Create CAN bus instance
        # can_factory = CANBusFactory(channel_type='vector', is_fd=False)
        can_factory = CANBusFactory(channel_type='virtualvector', is_fd=True)
        # can_factory = CANBusFactory(channel_type='virtualvector', is_fd=False)
        bus, notifier = can_factory.create_bus()

        # Create ISOTP layer - Use the same FD setting as CAN bus
        isotp_layer = ISOTPLayer(
            bus=bus,
            notifier=notifier,
            txid=0x759,
            rxid=0x749,
            is_fd=can_factory.is_fd  # Use CAN bus FD setting
        )
        
        isotp_layer.start()

        # Create UDS responder and start receiving
        responder = UDSResponder()
        responder.start_receiving(isotp_layer)

        # Main loop to keep program running
        while True:
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("[System] User interrupted operation")
    finally:
        if 'responder' in locals():
            responder.stop_receiving()
        if 'isotp_layer' in locals():
            isotp_layer.stop()
        if 'bus' in locals():
            bus.shutdown()

if __name__ == "__main__":
    main()