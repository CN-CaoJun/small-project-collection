import os
from tracemalloc import start
import intelhex

import time

from udsoncan.connections import PythonIsoTpConnection
from udsoncan.client import Client
import udsoncan.configs
from typing import Optional, List, Union, Tuple
from udsoncan import Response
from udsoncan import MemoryLocation

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.hazmat.primitives import cmac
from cryptography.hazmat.primitives.ciphers import algorithms
from cryptography.hazmat.backends import default_backend
import binascii
import json

class FlashingProcess:
    def __init__(self, uds_client: Client, uds_client_func: Client,trace_handler=None):
        self.client = uds_client
        self.client_func = uds_client_func
        
        self.trace_handler = trace_handler
        self.firmware_folder = None
        
        self.cal1_sig_data = None
        self.cal1_data = None
        self.cal1_start_addr = None
        self.cal1_data_length = None
        
        self.cal2_sig_data = None
        self.cal2_data = None
        self.cal2_start_addr = None
        self.cal2_data_length = None
        
        self.sbl_sig_data = None
        self.sbl_data = None
        self.sbl_start_addr = None
        self.sbl_data_length = None
        
        self.app_sig_data = None
        self.app_data = None
        self.app_start_addr = None 
        self.app_data_length = None
        
        self.max_block_size = 0
    def log(self, message: str):
        if self.trace_handler:
            self.trace_handler(message)
    def read_signature_file(self, file_path: str) -> Optional[bytes]:
        try:
            if not os.path.exists(file_path):
                self.log(f"Error: Signature file does not exist: {file_path}")
                return None
                
            with open(file_path, 'r') as f:
                content = f.read()
            
            hex_values = content.replace('0x', '').replace(',', '').replace(' ', '').strip()
            
            try:
                data = bytes.fromhex(hex_values)
            except ValueError as e:
                self.log(f"Error: Invalid hex format: {str(e)}")
                return None
                
            if len(data) != 512:
                self.log(f"Error: Invalid signature file size - Expected 512 bytes, got {len(data)} bytes")
                return None
                
            self.log(f"Successfully read signature file: {os.path.basename(file_path)}")
            self.log(f"File size: {len(data)} bytes")
            self.log(f"Signature content (first 16 bytes): {data[:16].hex().upper()}")
            return data
                
        except Exception as e:
            self.log(f"Read signature file exception: {str(e)}")
            return None
    def read_hex_file(self, hex_file_path: str) -> Tuple[Optional[bytes], Optional[int], Optional[int]]:
        try:
            if not os.path.exists(hex_file_path):
                self.log(f"Error: HEX file does not exist: {hex_file_path}")
                return None, None, None
                
            ih = intelhex.IntelHex(hex_file_path)
            start_addr = ih.minaddr()
            end_addr = ih.maxaddr()
            total_length = end_addr - start_addr + 1
            complete_data = ih.tobinarray(start=start_addr, size=total_length)
            
            self.log(f"Successfully read HEX file. Start address: 0x{start_addr:04X}, Length: {total_length} bytes")
            return bytes(complete_data), start_addr, total_length
                
        except Exception as e:
            self.log(f"Error reading HEX file: {str(e)}")
            return None, None, None
    def program_request_only(self, data: bytes) -> bool:

        try:
            with self.client as client:
                client.conn.send(data)
                self.log(f"Send Phy Request data: {data.hex().upper()}")
                return True
            
        except Exception as e:
            self.log(f"Send request exception: {str(e)}")
    def program_request_only_func(self, data: bytes) -> bool:
        try:
            with self.client_func as client:
                client.conn.send(data)
                self.log(f"Send Func Request data: {data.hex().upper()}")
                return True
            
        except Exception as e:
            self.log(f"Send request exception: {str(e)}")
    def change_session(self, session_type: int) -> bool:
        """Step 1 and 3: Change diagnostic session"""
        self.log(f"Step: Switch to session type 0x{session_type:02X}")
        try:
            with self.client as client:
                response = client.change_session(session_type)
                if response:
                    self.log(f"Session switch successful, response: {response.data.hex().upper()}")
                    return True
                else:
                    self.log("Session switch failed")
                    return False
        except Exception as e:
            self.log(f"Session switch exception: {str(e)}")
            return False
    
    def enter_extended_session(self) -> bool:
        """Step 2: Enter extended session"""
        self.log("Step: Enter extended session")
        try:
            with self.client as client:
                response = client.routine_control(routine_id=0x0203, control_type=0x01)
                self.log(f"Response content: {response.data.hex().upper() if response else 'None'}")
                if response.positive:
                    self.log("Extended session  31 01 02 03 successful")
                    return True
                else:
                    self.log(f"Extended session failed, response: {response.data.hex().upper() if response else 'None'}")
                    return False
        except Exception as e:
            self.log(f"Extended session exception: {str(e)}")
            return False
    
    def enable_check_bypass(self, routainid :int, data:bytes ) -> bool:
        try:
            with self.client as client:
                response = client.routine_control(routine_id = routainid, control_type=0x01,data=data)
                self.log(f"Response content: {response.data.hex().upper() if response else 'None'}")
                if response.positive:
                    self.log(f"Extended session {routainid} successfully")
                    return True
                else:
                    self.log(f"Extended session failed, response: {response.data.hex().upper() if response else 'None'}")
                    return False
        except Exception as e:
            self.log(f"Extended session exception: {str(e)}")
            return False
            
    def security_access(self, zone:str) -> bool:
        self.log("Step: Execute security access")
        try:
            with self.client as client:
                # Request seed (Step 4)
                response = client.request_seed(level=0x11)
                if not response:
                    self.log("Failed to get seed")
                    return False
                    
                self.log(f"seed: {response.data.hex().upper()}")
                seed_recv = response.data[1:17]
                
                Calculate27 = SecurityKeyAlgorithm_Chery
                
                computed_key = Calculate27.calculate_security_key(Calculate27, zcu_type = zone, level= 0x11, seed = seed_recv)
                self.log(f"Key: 0x{computed_key}")

                response = client.send_key(level=0x12, key=bytes.fromhex(computed_key))
                if response:
                    self.log("Security access successful")
                    return True
                else:
                    self.log("Security access failed")
                    return False
        except Exception as e:
            self.log(f"Security access exception: {str(e)}")
            return False
            
    def read_f0f0_identifier(self) -> bool:
        self.log("Step: Read F0F0 identifier")
        try:
            with self.client as client:
                response = client.write_data_by_identifier(did=0xF184, value=data)
                
                if response and response.positive:
                    self.log("Has successfully written F184 identifier")
                    return True
                else:
                    return False
        except Exception as e:
            self.log(f"Write F15A identifier exception: {str(e)}")
            return False
    def write_f184_identifier(self) -> bool:
        self.log("Step: Write F184 identifier")
        try:
            with self.client as client:
                data = bytes.fromhex('19050E4F544130303120202020202020202020')
                response = client.write_data_by_identifier(did=0xF184, value=data)
                
                if response and response.positive:
                    self.log("Has successfully written F184 identifier")
                    return True
                else:
                    return False
        except Exception as e:
            self.log(f"Write F184 identifier exception: {str(e)}")
            return False
            
    def request_download(self, download_type: str = 'sbl') -> bool:
        self.log(f"Step: Request {download_type.upper()} download")
        try:
            with self.client as client:
                if download_type.lower() == 'sbl':
                    addr = self.sbl_start_addr
                    size = self.sbl_data_length
                elif download_type.lower() == 'app':
                    addr = self.app_start_addr
                    size = self.app_data_length
                elif download_type.lower() == 'cal1':
                    addr = self.cal1_start_addr
                    size = self.cal1_data_length
                elif download_type.lower() == 'cal2':
                    addr = self.cal2_start_addr
                    size = self.cal2_data_length
                else:
                    self.log(f"Invalid download type: {download_type}")
                    return False

                memory_location = MemoryLocation(
                    address=addr,
                    memorysize=size,
                    address_format=32,
                    memorysize_format=32
                )
                
                response = client.request_download(
                    memory_location=memory_location
                )
                
                if response and response.positive:
                    response_data = response.get_payload()
                    if len(response_data) >= 3:
                        max_block_length = int.from_bytes(response_data[2:], byteorder='big')
                        self.max_block_size = max_block_length - 2  
                        self.log(f"{download_type.upper()} download request successful, max block size: {self.max_block_size}, response: {response_data.hex().upper()}")
                    else:
                        self = 0xFFA - 2
                        self.log(f"{download_type.upper()} download request successful, using default block size: {self.max_block_size}")
                    return True
                else:
                    self.log(f"{download_type.upper()} download request failed, response: {response.get_payload().hex().upper() if response else 'None'}")
                    return False
        except Exception as e:
            self.log(f"{download_type.upper()} download request exception: {str(e)}")
            return False
            
    def transfer_hex_data(self, data_type: str = 'sbl') -> bool:
        USE_UDS_TRANSFER = True
        self.log(f"Step: Transfer {data_type.upper()} data")
        try:
            if data_type.lower() == 'sbl':
                hex_data = self.sbl_data
                start_addr = self.sbl_start_addr
                data_length = self.sbl_data_length
            elif data_type.lower() == 'app':
                hex_data = self.app_data
                start_addr = self.app_start_addr
                data_length = self.app_data_length
            elif data_type.lower() == 'cal1':
                hex_data = self.cal1_data
                start_addr = self.cal1_start_addr
                data_length = self.cal1_data_length
            elif data_type.lower() == 'cal2':
                hex_data = self.cal2_data
                start_addr = self.cal2_start_addr
                data_length = self.cal2_data_length
            else:
                self.log(f"Invalid data type: {data_type}")
                return False
            
            self.log(f"Data transfer info - Type: {data_type.upper()}, Start address=0x{start_addr:04X}, Length=0x{data_length:04X} bytes")
            
            with self.client as client:
                if USE_UDS_TRANSFER:
                    try:
                        if not self.max_block_size:
                            self.log("Warning: Max block size not obtained, using default value 0x0FF8")
                            self.max_block_size = 4088
                        
                        # Calculate total packets with ceiling division to ensure all data is transmitted
                        total_packets = (data_length + self.max_block_size - 1) // self.max_block_size
                        if total_packets == 0:
                            total_packets = 1  
                            
                        self.log(f"Data transfer info - Total length: 0x{data_length:04X} bytes, Packets: {total_packets}, Max block size: 0x{self.max_block_size:04X} bytes")
                        
                        # Initialize sequence number to 0x01
                        sequence_number = 0x01
                        for packet_index in range(total_packets):
                            start_offset = packet_index * self.max_block_size
                            end_offset = min(start_offset + self.max_block_size, data_length)
                            current_block = hex_data[start_offset:end_offset]
                            
                            # Only log every 100 packets
                            if (packet_index + 1) % 128 == 0 or packet_index == 0 or packet_index == total_packets - 1:
                                progress = f"[{packet_index + 1}/{total_packets}]"
                                self.log(f"{progress} Transferring data - Sequence: 0x{sequence_number:02X}, Length: 0x{len(current_block):04X}")
                            
                            response = client.transfer_data(sequence_number=sequence_number, data=current_block)
                            
                            if not response.positive:
                                self.log(f"Data block transfer failed, Sequence: 0x{sequence_number:02X}, Response code: 0x{response.code:02X}")
                                return False
                            
                            # Update sequence number: after 0xFF it should wrap to 0x00
                            sequence_number = (sequence_number + 1) % 0x100
                        
                        self.log(f"Data transfer completed, Total packets transferred: {total_packets}")
                        return True
                                
                    except Exception as e:
                        self.log(f"UDS transfer exception: {str(e)}")
                        return False
                    
        except Exception as e:
            self.log(f"Data transfer exception: {str(e)}")
            return False
        
    def exit_transfer(self) -> bool:
        self.log("Step: Request transfer exit")
        try:
            with self.client as client:
                # Use client's built-in transfer_exit method instead of raw send
                response = client.request_transfer_exit(data=None)
                
                if response and response.positive:
                    self.log("Transfer exit successful")
                    return True
                else:
                    self.log(f"Transfer exit failed, response: {response.get_payload().hex().upper() if response else 'None'}")
                    return False
        except Exception as e:
            self.log(f"Transfer exit exception: {str(e)}")
            return False
            
    def transfer_signature(self, data_type: str = 'sbl') -> bool:
        self.log(f"Step: Transfer {data_type.upper()} signature")
        try:
            if data_type.lower() == 'sbl':
                if not self.sbl_sig_data:
                    self.log("Error: SBL signature data not initialized")
                    return False
                sig_data = self.sbl_sig_data
            elif data_type.lower() == 'app':
                if not self.app_sig_data:
                    self.log("Error: APP signature data not initialized")
                    return False
                sig_data = self.app_sig_data
            elif data_type.lower() == 'cal1':
                if not self.cal1_sig_data:
                    self.log("Error: APP signature data not initialized")
                    return False
                sig_data = self.cal1_sig_data
            elif data_type.lower() == 'cal2':
                if not self.cal2_sig_data:
                    self.log("Error: APP signature data not initialized")
                    return False
                sig_data = self.cal2_sig_data
            else:
                self.log(f"Error: Invalid signature type: {data_type}")
                return False
                
            complete_data = sig_data
            
            with self.client as client:
                response = client.routine_control(
                    routine_id=0xDD02,
                    control_type=0x01,
                    data=complete_data
                )
                
                if not response:
                    self.log("No response received")
                    return False
                    
                if response.positive:
                    self.log(f"{data_type.upper()} signature verification successful")
                    return True
                    
                self.log(f"Unexpected response received: {response.get_payload().hex().upper()}")
                return False
                
        except Exception as e:
            self.log(f"{data_type.upper()} signature transfer exception: {str(e)}")
            return False
            
    def erase_memory(self, partaion_type:str) -> bool:
        """Step 11: Erase APP address using routine control service"""
        self.log(f"Step: Erase {partaion_type} address")
        
        if partaion_type == "app":
            start_address = self.app_start_addr
            length=self.app_data_length
        elif partaion_type == "cal1":
            start_address = self.cal1_start_addr
            length=self.cal1_data_length
        elif partaion_type == "cal2":
            start_address = self.cal2_start_addr
            length=self.cal2_data_length
        else:
            self.log("Invalid partition type")
            return False
        
        try:
            with self.client as client:

                response = client.routine_control(
                    routine_id=0xFF00,
                    control_type=0x01,
                    data=bytes([0x44]) + start_address.to_bytes(4, 'big') + length.to_bytes(4, 'big')
                )
                
                if not response:
                    self.log("No response received")
                    return False
                    
                if response.positive:
                    self.log(f"Earse response is {response.data.hex().upper()}")
                    if response.data.hex().upper().startswith('01FF0001'):
                        self.log("Memory erase failed - received 7101FF0001")
                        return False
                    self.log("Memory erase successful")
                    return True
                    
                if response.code == 0x78:
                    self.log("Received pending response (0x78), waiting for final response...")
                    final_response = client.wait_for_response(timeout=5)
                    if final_response and final_response.positive and final_response.data.hex().upper().startswith('01FF0000'):
                        self.log("Memory erase successful")
                        return True
                    else:
                        self.log(f"Memory erase failed, response: {final_response.get_payload().hex().upper() if final_response else 'None'}")
                        return False
                
                self.log(f"Unexpected response received: {response.get_payload().hex().upper()}")
                return False
                
        except Exception as e:
            self.log(f"Memory erase exception: {str(e)}")
            return False

    def complete_flash_process(self) -> bool:
        self.log("Step: Complete flash process")
        try:
            with self.client as client:
                # Use routine control service with routine ID 0xFF01
                response = client.routine_control(
                    routine_id=0xFF01,
                    control_type=0x01
                )
                
                if not response:
                    self.log("No response received")
                    return False
                    
                # Check for positive response
                if response.positive:
                    self.log("Complete flash process successful")
                    return True
                    
                self.log(f"Unexpected response received: {response.get_payload().hex().upper()}")
                return False
                
        except Exception as e:
            self.log(f"Complete flash process exception: {str(e)}")
            return False

    def reset_ecu(self) -> bool:
        """Step 17: Reset ECU
        
        Performs an ECU reset using UDS service 0x11 (ECU Reset)
        with reset type 0x03 (soft reset).
        
        Returns:
            bool: True if reset successful, False otherwise
        """
        self.log("Step: Reset ECU")
        try:
            with self.client as client:
                # Use UDS client's ecu_reset method instead of raw request
                response = client.ecu_reset(reset_type=0x01) 
                
                if response and response.positive:
                    self.log("ECU reset successful")
                    return True
                else:
                    self.log(f"ECU reset failed, response: {response.get_payload().hex().upper() if response else 'None'}")
                    return False
        except Exception as e:
            self.log(f"ECU reset exception: {str(e)}")
            return False
    def program_testerpresent(self) -> bool:
        """Step 18: Program tester present"""
        self.log("Step: Program tester present")
        try:
            with self.client as client:
                
                response = client.tester_present()
                if response and response.positive:
                    self.log("Tester present programming successful")
                    return True
                else:
                    self.log(f"Tester present programming failed, response: {response.get_payload().hex().upper() if response else 'None'}")
                    return False

        except Exception as e:
            self.log(f"Tester present programming exception: {str(e)}")
            return False
    def check_programming_status(self) -> bool:
        """Step 18: Check programming status"""
        self.log("Step: Check programming status")
        try:
            with self.client as client:
                response = client.read_data_by_identifier(0xF0F0)
                
                if response and response.positive:  
                    self.log("Version check successful")
                    return True
                else:
                    self.log(f"Version check failed")
                    return False
        except Exception as e:
            self.log(f"Programming status check exception: {str(e)}")
            return False

    def fault_memory_clear(self) -> bool:
        """Clear fault memory using UDS service 0x14
        
        Returns:
            bool: True if clear successful, False otherwise
        """
        self.log("Step: Clear fault memory")
        try:
            with self.client as client:
                # Send clear DTC command (0x14 FF FF FF)
                response = client.clear_dtc(group = 0xFFFFFF)
                
                if response and response.positive:
                    self.log("Fault memory clear successful")
                    return True
                else:
                    self.log(f"Fault memory clear failed, response: {response.get_payload().hex().upper() if response else 'None'}")
                    return False
                    
        except Exception as e:
            self.log(f"Fault memory clear exception: {str(e)}")
            return False
    def execute_flashing_sequence(self, zone_type: str, cal_is_must: bool, flash_config: dict) -> bool:

        self.log("Start executing flashing sequence...")
        self.log(f"Zone type: {zone_type}")
        self.log(f"Calibration is must: {cal_is_must}")
        self.log(f"Flash config details:\n{json.dumps(flash_config, indent=2, default=str)}")
        
        if cal_is_must:
            self.log("Checking calibration...")
            cal1_hex_path = flash_config.get('cal1_hex')
            if not cal1_hex_path:
                self.log("Error: CAL1 HEX path not found in flash config")
                return False 
        
            cal1_sig_path = cal1_hex_path.rsplit('.', 1)[0] + '.rsa'
            if not os.path.exists(cal1_sig_path):
                self.log(f"Warning: Signature file not found: {cal1_sig_path}")
                self.cal1_sig_data = bytes([0xAA] * 512)
            else:
                self.cal1_sig_data = self.read_signature_file(cal1_sig_path)
                if not self.cal1_sig_data:
                    self.log("Failed to read SBL signature file")
                    return False

            self.cal1_data, self.cal1_start_addr, self.cal1_data_length = self.read_hex_file(cal1_hex_path)
            if not self.cal1_data:
                self.log("Failed to read CAL1 HEX file") 
                return False
        
            cal2_hex_path = flash_config.get('cal2_hex')
            if not cal1_hex_path:
                self.log("Error: CAL1 HEX path not found in flash config")
                return False 
        
            cal2_sig_path = cal2_hex_path.rsplit('.', 1)[0] + '.rsa'
            if not os.path.exists(cal2_sig_path):
                self.log(f"Warning: Signature file not found: {cal2_sig_path}")
                self.cal2_sig_data = bytes([0xAA] * 512)
            else:
                self.cal2_sig_data = self.read_signature_file(cal2_hex_path)
                if not self.cal2_sig_data:
                    self.log("Failed to read SBL signature file")
                    return False

            self.cal2_data, self.cal2_start_addr, self.cal2_data_length = self.read_hex_file(cal2_hex_path)
            if not self.cal2_data:
                self.log("Failed to read CAL2 HEX file") 
                return False
                
        sbl_hex_path = flash_config.get('sbl_hex')
        if not sbl_hex_path:
            self.log("Error: SBL HEX path not found in flash config")
            return False
    
        sbl_sig_path = sbl_hex_path.rsplit('.', 1)[0] + '.rsa'
        if not os.path.exists(sbl_sig_path):
            self.log(f"Warning: Signature file not found: {sbl_sig_path}")
            self.sbl_sig_data = bytes([0xAA] * 512)
        else:
            self.sbl_sig_data = self.read_signature_file(sbl_sig_path)
            if not self.sbl_sig_data:
                self.log("Failed to read SBL signature file")
                return False

        self.sbl_data, self.sbl_start_addr, self.sbl_data_length = self.read_hex_file(sbl_hex_path)
        if not self.sbl_data:
            self.log("Failed to read SBL HEX file") 
            return False

        app_hex_path = flash_config.get('app_hex')
        if not app_hex_path:
            self.log("Error: APP HEX path not found in flash config")
            return False
        
        app_sig_path = app_hex_path.rsplit('.', 1)[0] + '.rsa'
        if not os.path.exists(app_sig_path):
            self.log(f"Warning: Signature file not found: {app_sig_path}")
            self.app_sig_data = bytes([0xAA] * 512)
        else:
            self.app_sig_data = self.read_signature_file(app_sig_path)
            if not self.app_sig_data:
                self.log("Failed to read APP signature file")
                return False
        
        self.app_data, self.app_start_addr, self.app_data_length = self.read_hex_file(app_hex_path) 
        if not self.app_data:
            self.log("Failed to read APP HEX file")
            return False
        
        try:
            if not cal_is_must:
                steps = [
                    lambda: self.change_session(0x01),                                
                    lambda: self.program_request_only_func(bytes.fromhex('1083')),
                    self.enter_extended_session,        
                    lambda: self.program_request_only_func(bytes.fromhex('8582')),
                    lambda: self.program_request_only_func(bytes.fromhex('288303')),
                    lambda: self.change_session(0x70),  
                    lambda: self.enable_check_bypass(routainid = 0x55B0, data=bytes.fromhex('00')),                             
                    lambda: self.enable_check_bypass(routainid = 0x55B1, data=bytes.fromhex('01')),                             
                    lambda: self.security_access(zone_type),       
                    self.check_programming_status,                                   
                    self.write_f184_identifier,                                       
                    lambda:self.request_download(download_type = 'sbl'),           
                    lambda:self.transfer_hex_data(data_type = 'sbl'),           
                    lambda:self.exit_transfer(),                                          
                    lambda:self.transfer_signature(data_type = 'sbl'),                 
                    lambda:self.erase_memory('app'),                                             
                    lambda:self.request_download(download_type = 'app'),                            
                    lambda:self.transfer_hex_data(data_type = 'app'),                                         
                    lambda:self.exit_transfer(),                                            
                    lambda:self.transfer_signature(data_type = 'app'), 
                    self.complete_flash_process,               #3101FF01                     
                    lambda: self.program_request_only_func(bytes.fromhex('288003')),
                    self.reset_ecu,       
                    lambda: self.change_session(0x03),                                
                    self.fault_memory_clear,        
                    lambda: self.program_request_only_func(bytes.fromhex('8581')),
                    lambda: self.program_request_only(bytes.fromhex('1081')),
                ]
            else:
                steps = [
                    lambda: self.change_session(0x01),                                
                    lambda: self.program_request_only_func(bytes.fromhex('1083')),
                    self.enter_extended_session,        
                    lambda: self.program_request_only_func(bytes.fromhex('8582')),
                    lambda: self.program_request_only_func(bytes.fromhex('288303')),
                    lambda: self.change_session(0x70),  
                    lambda: self.enable_check_bypass(routainid = 0x55B0, data=bytes.fromhex('00')),                             
                    lambda: self.enable_check_bypass(routainid = 0x55B1, data=bytes.fromhex('01')),                             
                    lambda: self.security_access(zone_type),       
                    self.check_programming_status,                                   
                    self.write_f184_identifier,                                       
                    lambda:self.request_download(download_type = 'sbl'),           
                    lambda:self.transfer_hex_data(data_type = 'sbl'),           
                    lambda:self.exit_transfer(),                                          
                    lambda:self.transfer_signature(data_type = 'sbl'),
                    lambda:self.erase_memory('cal1'),                                             
                    lambda:self.request_download(download_type = 'cal1'),                            
                    lambda:self.transfer_hex_data(data_type = 'cal1'),                                         
                    lambda:self.exit_transfer(),                                            
                    lambda:self.transfer_signature(data_type = 'cal1'),
                    lambda:self.erase_memory('cal2'),                                             
                    lambda:self.request_download(download_type = 'cal2'),                            
                    lambda:self.transfer_hex_data(data_type = 'cal2'),                                         
                    lambda:self.exit_transfer(),                                            
                    lambda:self.transfer_signature(data_type = 'cal2'),           
                    lambda:self.erase_memory('app'),                                             
                    lambda:self.request_download(download_type = 'app'),                            
                    lambda:self.transfer_hex_data(data_type = 'app'),                                         
                    lambda:self.exit_transfer(),                                            
                    lambda:self.transfer_signature(data_type = 'app'), 
                    self.complete_flash_process,           
                    lambda: self.program_request_only_func(bytes.fromhex('288003')),
                    self.reset_ecu,       
                    lambda: self.change_session(0x03),                                
                    self.fault_memory_clear,        
                    lambda: self.program_request_only_func(bytes.fromhex('8581')),
                    lambda: self.program_request_only(bytes.fromhex('1081')),
                ]
            
            for i, step in enumerate(steps, 1):
                self.log(f"Executing step {i}/{len(steps)}")
                if not step():
                    self.log(f"Step {i} failed, terminating flashing sequence")
                    return False
                if step == self.reset_ecu:
                    self.log("Waiting 3 seconds after ECU reset...")
                    time.sleep(3)
                    
            self.log("Flashing sequence completed")
            return True
            
        except Exception as e:
            self.log(f"Flashing sequence exception terminated: {str(e)}")
    
class SecurityKeyAlgorithm:
    SECURITY_KKEY_L2 = 0x0000CDCA  
    SECURITY_KKEY_L4 = 0x00001D5C  

    @staticmethod
    def compute_level2(seed: int, keyk: int) -> int:
        temp_key = (seed ^ keyk) & 0xFFFFFFFF
        for _ in range(32):
            if temp_key & 0x00000001:
                temp_key = (temp_key >> 1) ^ seed
            else:
                temp_key = (temp_key >> 1) ^ keyk
            temp_key &= 0xFFFFFFFF 
        return temp_key

    @staticmethod
    def compute_level4(seed: int, keyk: int) -> int:
        temp_key = (seed ^ keyk) & 0xFFFFFFFF
        for _ in range(32):
            temp_key = ((temp_key << 7) | (temp_key >> 25)) & 0xFFFFFFFF
            temp_key ^= keyk
            temp_key &= 0xFFFFFFFF
        return temp_key

class SecurityKeyAlgorithm_Chery:
    def calculate_security_key(self, zcu_type: str, level: int, seed: bytes) -> bytes:
        RZCU_SecurityAES128KEY1 = bytes([
            0x27, 0xBB, 0x7B, 0x9F, 0xAA, 0x4D, 0xEC, 0x13,
            0x32, 0x7A, 0x7C, 0x2F, 0xF7, 0xFA, 0xA1, 0x9A
        ])

        RZCU_SecurityAES128KEY11 = bytes([
            0xA7, 0x34, 0xD1, 0x55, 0xA9, 0x6A, 0xA4, 0x09,
            0xDB, 0x93, 0x3F, 0x74, 0x75, 0xF9, 0x35, 0xE9
        ])

        LZCU_SecurityAES128KEY1 = bytes([
            0x96, 0xCB, 0x1B, 0xBF, 0x02, 0xDF, 0x05, 0x10,
            0xF5, 0x21, 0x9C, 0xCE, 0x67, 0x9B, 0x98, 0xFA
        ])

        LZCU_SecurityAES128KEY11 = bytes([
            0x1A, 0xF0, 0x69, 0xCD, 0x52, 0x1B, 0xF9, 0x70,
            0xE8, 0xDC, 0x8E, 0xC6, 0xBB, 0x24, 0x62, 0x8D
        ])
        try:
            if zcu_type.upper() == 'RZCU':
                if level == 0x01:
                    key = RZCU_SecurityAES128KEY1
                elif level == 0x11:
                    key = RZCU_SecurityAES128KEY11
                else:
                    raise ValueError(f"Invalid security level for RZCU: {level}")
            elif zcu_type.upper() == 'LZCU':
                if level == 0x01:
                    key = LZCU_SecurityAES128KEY1
                elif level == 0x11:
                    key = LZCU_SecurityAES128KEY11
                else:
                    raise ValueError(f"Invalid security level for LZCU: {level}")
            else:
                raise ValueError(f"Invalid ZCU type: {zcu_type}")

            c = cmac.CMAC(algorithms.AES(key), backend=default_backend())
            c.update(seed)
            cmac_result = c.finalize()
            
            return cmac_result.hex().upper()
            
        except Exception as e:
            self.log(f"Security key calculation failed: {str(e)}")
            return None