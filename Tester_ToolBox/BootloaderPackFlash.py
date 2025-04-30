import tkinter as tk
from tkinter import ttk
import sv_ttk
import sys
import os
import intelhex

sys.path.insert(0, os.path.abspath("reference_modules/python-can"))
sys.path.insert(0, os.path.abspath("reference_modules/python-can-isotp"))
sys.path.insert(0, os.path.abspath("reference_modules/python-udsoncan"))
import can
import isotp
import udsoncan
from can.interfaces.vector import canlib, xlclass, xldefine
from datetime import datetime
import threading
import time

from udsoncan.connections import PythonIsoTpConnection
from udsoncan.client import Client
import udsoncan.configs
# from udsoncan import services
# from udsoncan import MemoryLocation
from typing import Optional, List, Union, Tuple
from udsoncan import Response
from udsoncan import MemoryLocation

class FlashingProcess:
    def __init__(self, uds_client: Client, trace_handler=None):
        self.client = uds_client
        self.trace_handler = trace_handler
        self.firmware_folder = None
        
        self.sbl_sig_data = None
        self.app_sig_data = None
        self.sbl_data = None
        self.sbl_start_addr = None
        self.sbl_data_length = None
        self.app_data = None
        self.app_start_addr = None 
        self.app_data_length = None
        
        self.max_block_size = 0
    def log(self, message: str):
        """输出日志"""
        if self.trace_handler:
            self.trace_handler(message)
    def read_signature_file(self, file_path: str) -> Optional[bytes]:
        """Read and validate signature file
        
        Args:
            file_path: Path to the signature binary file
            
        Returns:
            Optional[bytes]: Signature data if successful, None if failed
        """
        try:
            if not os.path.exists(file_path):
                self.log(f"Error: Signature file does not exist: {file_path}")
                return None
                
            with open(file_path, 'rb') as f:
                data = f.read()
                self.log(f"Successfully read signature file {os.path.basename(file_path)}")
                self.log(f"File size: 0x{len(data):04X} bytes")
                # self.log(f"File content: {data.hex().upper()}")
                return data
                
        except Exception as e:
            self.log(f"Signature file read exception: {str(e)}")
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
                response = client.routine_control(routine_id=0xD003, control_type=0x01)
                self.log(f"Response content: {response.data.hex().upper() if response else 'None'}")
                if response and response.data.hex().upper().startswith('01D00300'):
                    self.log("Extended session successful")
                    return True
                else:
                    self.log(f"Extended session failed, response: {response.data.hex().upper() if response else 'None'}")
                    return False
        except Exception as e:
            self.log(f"Extended session exception: {str(e)}")
            return False
            
    def security_access(self) -> bool:
        """Step 4 and 5: Security access"""
        self.log("Step: Execute security access")
        try:
            with self.client as client:
                # Request seed (Step 4)
                response = client.request_seed(level=0x07)
                if not response:
                    self.log("Failed to get seed")
                    return False
                    
                self.log(f"Complete response data: {response.data.hex().upper()}")
                print(f"seed response: {response.data.hex().upper()}")
                
                seed = response.data[1:5]  # Extract correct 4 bytes
                self.log(f"Successfully got seed (length {len(seed)}): {seed.hex().upper()}")
                
                seed_int = int.from_bytes(seed, byteorder='big')  # Convert bytes type seed to integer
                computed_key = SecurityKeyAlgorithm.compute_level4(
                    seed=seed_int, 
                    keyk=SecurityKeyAlgorithm.SECURITY_KKEY_L4
                )
                key = computed_key.to_bytes(4, byteorder='big')
                print(f"Key: 0x{computed_key:08X}")  # Print key value
                response = client.send_key(level=0x08, key=key)
                
                if response:
                    self.log("Security access successful")
                    return True
                else:
                    self.log("Security access failed")
                    return False
        except Exception as e:
            self.log(f"Security access exception: {str(e)}")
            return False
            
    def write_f15a_identifier(self) -> bool:
        """Step 6: Write F15A identifier"""
        self.log("Step: Write F15A identifier")
        try:
            with self.client as client:
                data = bytes.fromhex('40 04 13 00 00 00 03 00 00 00 00 00 00 00 00')
                response = client.write_data_by_identifier(did=0xF15A, value=data)
                
                if response and response.positive:
                    self.log("Has successfully written F15A identifier")
                    return True
                else:
                    return False
        except Exception as e:
            self.log(f"Write F15A identifier exception: {str(e)}")
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
                if not self.sbl_data:
                    self.log("SBL data not initialized")
                    return False
                hex_data = self.sbl_data
                start_addr = self.sbl_start_addr
                data_length = self.sbl_data_length
            elif data_type.lower() == 'app':
                if not self.app_data:
                    self.log("APP data not initialized")
                    return False
                hex_data = self.app_data
                start_addr = self.app_start_addr
                data_length = self.app_data_length
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
                            total_packets = 1  # Ensure at least one packet
                            
                        self.log(f"Data transfer info - Total length: 0x{data_length:04X} bytes, Packets: {total_packets}, Max block size: 0x{self.max_block_size:04X} bytes")
                        
                        sequence_number = 0x01
                        for packet_index in range(total_packets):
                            start_offset = packet_index * self.max_block_size
                            end_offset = min(start_offset + self.max_block_size, data_length)
                            current_block = hex_data[start_offset:end_offset]
                            
                            self.log(f"Transferring packet {packet_index + 1:02d}/{total_packets:02d}, Sequence: 0x{sequence_number:02X}, Length: 0x{len(current_block):04X} bytes")
                            response = client.transfer_data(sequence_number=sequence_number, data=current_block)
                            
                            if not response.positive:
                                self.log(f"Data block transfer failed, Sequence: 0x{sequence_number:02X}, Response code: 0x{response.code:02X}")
                                return False
                            
                            sequence_number = (sequence_number % 0xFF) + 1
                        
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
            else:
                self.log(f"Error: Invalid signature type: {data_type}")
                return False
                
            with self.client as client:
                response = client.routine_control(
                    routine_id=0xD002,
                    control_type=0x01,
                    data=sig_data
                )
                
                if not response:
                    self.log("No response received")
                    return False
                    
                if response.positive and response.data.hex().upper().startswith('01D00200'):
                    self.log(f"{data_type.upper()} signature verification successful")
                    return True
                    
                self.log(f"Unexpected response received: {response.get_payload().hex().upper()}")
                return False
                
        except Exception as e:
            self.log(f"{data_type.upper()} signature transfer exception: {str(e)}")
            return False
            
    def erase_memory(self) -> bool:
        """Step 11: Erase APP address using routine control service"""
        self.log("Step: Erase APP address")
        try:
            with self.client as client:

                response = client.routine_control(
                    routine_id=0xFF00,
                    control_type=0x01,
                    data=bytes.fromhex('44 00 00 00 00 00 02 E0 00')
                )
                
                if not response:
                    self.log("No response received")
                    return False
                    
                if response.positive and response.data.hex().upper().startswith('01FF0000'):
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
                
                # 处理意外响应
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
                if response.positive and response.data.hex().upper().startswith('01FF0100'):
                    self.log("Complete flash process successful")
                    return True
                    
                # Handle unexpected response
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
                response = client.ecu_reset(reset_type=0x03)  # 0x03 = soft reset
                
                if response and response.positive:
                    self.log("ECU reset successful")
                    return True
                else:
                    self.log(f"ECU reset failed, response: {response.get_payload().hex().upper() if response else 'None'}")
                    return False
        except Exception as e:
            self.log(f"ECU reset exception: {str(e)}")
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

    def execute_flashing_sequence(self, firmware_folder: str) -> bool:
        """Execute complete flashing sequence"""
        self.firmware_folder = firmware_folder
        self.log("Start executing flashing sequence...")
        
        sbl_sig_path = os.path.join(firmware_folder, 'gen6nu_sbl_sign.bin')
        app_sig_path = os.path.join(firmware_folder, 'gen6nu_sign.bin')
        self.sbl_sig_data = self.read_signature_file(sbl_sig_path)
        self.app_sig_data = self.read_signature_file(app_sig_path)
        
        sbl_path = os.path.join(firmware_folder, 'gen6nu_sbl.hex')
        app_path = os.path.join(firmware_folder, 'gen6nu.hex')
        self.sbl_data, self.sbl_start_addr, self.sbl_data_length = self.read_hex_file(sbl_path)
        if not self.sbl_data:
            self.log("Failed to read SBL HEX file")
            return False
            
        self.app_data, self.app_start_addr, self.app_data_length = self.read_hex_file(app_path) 
        if not self.app_data:
            self.log("Failed to read APP HEX file")
            return False
        
        try:
            steps = [
                lambda: self.change_session(0x03),                                # Step 1: Switch to extended diagnostic session
                self.enter_extended_session,                                      # Step 2: Enter extended session
                lambda: self.change_session(0x02),                                # Step 3: Switch to programming session
                self.security_access,                                             # Step 4-5: Security access
                self.write_f15a_identifier,                                       # Step 6: Write F15A identifier
                lambda:self.request_download(download_type = 'sbl'),                # Step 7: Request download
                lambda:self.transfer_hex_data(data_type = 'sbl'),               # Step 8: Transfer HEX data
                lambda:self.exit_transfer(),                                          # Step 9: Exit transfer
                lambda:self.transfer_signature(data_type = 'sbl'),                  # Step 10: Transfer signature
                self.erase_memory,                                               # Step 11: Enter Flash mode
                lambda:self.request_download(download_type = 'app'),                             # Step 12: Request download application
                lambda:self.transfer_hex_data(data_type = 'app'),                                          # Step 13: Transfer application data
                lambda:self.exit_transfer(),                                              # Step 14: Exit transfer
                lambda:self.transfer_signature(data_type = 'app'),                                       # Step 15: Verify application signature
                self.complete_flash_process,                                     # Step 16: Complete flash process
                self.reset_ecu,                                                 # Step 17: Reset ECU
                self.check_programming_status                                    # Step 18: Check programming status
            ]
            
            for i, step in enumerate(steps, 1):
                self.log(f"Executing step {i}/{len(steps)}")
                if not step():
                    self.log(f"Step {i} failed, terminating flashing sequence")
                    return False
                    
            self.log("Flashing sequence completed")
            return True
            
        except Exception as e:
            self.log(f"Flashing sequence exception terminated: {str(e)}")
    
class SecurityKeyAlgorithm:
    SECURITY_KKEY_L2 = 0x0000CDCA  # Level2算法密钥
    SECURITY_KKEY_L4 = 0x00001D5C  # Level4算法密钥

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


class SecurityKeyAlgorithmUP:
    SECURITY_KKEY_L2 = 0x0000CDCA  # Level2算法密钥
    SECURITY_KKEY_L4 = 0x00001D5C  # Level4算法密钥

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