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
        
        # 添加文件路径和解析结果存储
        self.sbl_data = None
        self.sbl_start_addr = None
        self.sbl_data_length = None
        self.app_data = None
        self.app_start_addr = None 
        self.app_data_length = None

    def log(self, message: str):
        """输出日志"""
        if self.trace_handler:
            self.trace_handler(message)
    def read_hex_file(self, hex_file_path: str) -> Tuple[Optional[bytes], Optional[int], Optional[int]]:
        """Read hex file using IntelHex library
        
        Args:
            hex_file_path: Path to the hex file
            
        Returns:
            Tuple containing:
            - Binary data bytes
            - Start address
            - Data length
            Or (None, None, None) if parsing fails
        """
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
                    return True
                else:
                    return False
        except Exception as e:
            self.log(f"Write F15A identifier exception: {str(e)}")
            return False
            
    def request_download(self, download_type: str = 'sbl') -> bool:
        """Step 7: 统一下载请求函数"""
        self.log(f"Step: Request {download_type.upper()} download")
        try:
            with self.client as client:
                # 根据类型选择参数源
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
                    self.log(f"{download_type.upper()} download request successful, response: {response.get_payload().hex().upper()}")
                    return True
                else:
                    self.log(f"{download_type.upper()} download request failed, response: {response.get_payload().hex().upper() if response else 'None'}")
                    return False
        except Exception as e:
            self.log(f"{download_type.upper()} download request exception: {str(e)}")
            return False
            
    def transfer_hex_data(self) -> bool:
        self.log("Step: Transfer HEX file data")
        try:
            if not self.sbl_data:
                self.log("SBL data not initialized")
                return False
                
            hex_data = self.sbl_data
            start_addr = self.sbl_start_addr
            data_length = self.sbl_data_length
            
            self.log(f"HEX file parse result: Start address=0x{start_addr:04X}, Data length=0x{data_length:04X} bytes")
            
            with self.client as client:
                # Use raw send method instead of transfer_data
                # Build 36 service request data: 36 + sequence number + data
                sequence_number = 0x01  # Start with sequence number 1 for first transfer
                request = bytes([0x36, sequence_number]) + hex_data
                client.conn.send(request)
                
                # Wait for response, handle 78 pending case
                response = client.conn.wait_frame(timeout=5)
                
                # Check if it's 78 pending response
                while response and response.hex().upper() == '7F3678':
                    self.log("Received 78 pending response, continue waiting...")
                    # Wait for final response again
                    response = client.conn.wait_frame(timeout=5)
                
                if response and response.hex().upper().startswith('76'):
                    self.log(f"Data transfer successful, response: {response.hex().upper()}")
                    return True
                else:
                    self.log(f"Data transfer failed, response: {response.hex().upper() if response else 'None'}")
                    return False
                    
        except Exception as e:
            self.log(f"Data transfer exception: {str(e)}")
            return False
        
    def exit_transfer(self) -> bool:
        """Step 9: Exit transfer"""
        self.log("Step: Request exit transfer")
        try:
            with self.client as client:
                # Use raw send method
                client.conn.send(bytes([0x37]))
                response = client.conn.wait_frame(timeout=3)
                
                if response and response.hex().upper() == '77':
                    self.log("Exit transfer successful")
                    return True
                else:
                    self.log(f"Exit transfer failed, response: {response.hex().upper() if response else 'None'}")
                    return False
        except Exception as e:
            self.log(f"Exit transfer exception: {str(e)}")
            return False
            
    def transfer_signature(self, bin_path: str) -> bool:
        """Step 10: Transfer signature file"""
        self.log("Step: Transfer signature file")
        try:
            if not os.path.exists(bin_path):
                self.log(f"Error: Signature file does not exist: {bin_path}")
                return False
                
            with self.client as client:
                # Read signature file
                with open(bin_path, 'rb') as f:
                    bin_data = f.read(512)  # Read 512 bytes
                    
                # Send data
                header = bytes.fromhex('31 01 D0 02')
                request = header + bin_data
                client.conn.send(request)
                
                # Wait for response
                response = client.conn.wait_frame(timeout=3)
                if not response:
                    self.log("No response received")
                    return False
                    
                # 检查是否直接收到正响应
                if response.hex().upper() == '7101D00200':
                    self.log("Signature verification successful")
                    return True
                    
                # 如果收到中间响应，则继续等待最终响应
                if response.hex().upper() == '7F3178':
                    self.log("Received intermediate response, waiting for final response...")
                    final_response = client.conn.wait_frame(timeout=5)
                    if final_response and final_response.hex().upper() == '7101D00200':
                        self.log("Signature verification successful")
                        return True
                    else:
                        self.log(f"Signature verification failed, response: {final_response.hex().upper() if final_response else 'None'}")
                        return False
                
                # 如果既不是正响应也不是中间响应，则验证失败
                self.log(f"Unexpected response received: {response.hex().upper()}")
                return False
            
        except Exception as e:
            self.log(f"Signature transfer exception: {str(e)}")
            return False
            
    def erase_memory(self) -> bool:
        """Step 11: Erase APP address"""
        self.log("Step: Erase APP address")
        try:
            with self.client as client:
                request = bytes.fromhex('31 01 FF 00 44 00 00 00 00 00 02 E0 00')
                client.conn.send(request)
                # Wait for response
                response = client.conn.wait_frame(timeout=3)
                if not response:
                    self.log("No response received")
                    return False
                    
                # 检查是否直接收到正响应
                if response.hex().upper() == '7101FF0000':
                    self.log("Signature verification successful")
                    return True
                    
                # 如果收到中间响应，则继续等待最终响应
                if response.hex().upper() == '7F3178':
                    self.log("Received intermediate response, waiting for final response...")
                    final_response = client.conn.wait_frame(timeout=5)
                    if final_response and final_response.hex().upper() == '7101FF0000':
                        self.log("Signature verification successful")
                        return True
                    else:
                        self.log(f"Signature verification failed, response: {final_response.hex().upper() if final_response else 'None'}")
                        return False
                
                # 如果既不是正响应也不是中间响应，则验证失败
                self.log(f"Unexpected response received: {response.hex().upper()}")
                return False
            
        except Exception as e:
            self.log(f"Enter Flash mode exception: {str(e)}")
            return False

    def request_app_download(self) -> bool:
        """Step 12: Request application download"""
        self.log("Step: Request application download")
        try:
            with self.client as client:
                request = bytes.fromhex('34 00 44 00 00 00 00 00 02 E0 00')
                client.conn.send(request)
                response = client.conn.wait_frame(timeout=5)
                
                if response and response.hex().upper().startswith('74200FFA'):
                    self.log(f"Download request successful, response: {response.hex().upper()}")
                    return True
                else:
                    self.log(f"Download request failed, response: {response.hex().upper() if response else 'None'}")
                    return False
        except Exception as e:
            self.log(f"Download request exception: {str(e)}")
            return False

    def transfer_app_data(self) -> bool:
        self.log("Step: Transfer application data")
        try:
            if not self.app_data:
                self.log("APP data not initialized")
                return False
                
            hex_data = self.app_data
            start_addr = self.app_start_addr
            data_length = self.app_data_length
            
            self.log(f"HEX file parse result: Start address=0x{start_addr:04X}, Data length=0x{data_length:04X} bytes")
            
            with self.client as client:
                # Get max package length from 34 service response (example response: 74 20 0F FA)
                # Assume max package length is in response data bytes 3-4 (0x0FFA = 4090 bytes)
                max_block_size = 4088  # Need to parse based on actual response value
                sequence_number = 0x01
                offset = 0
                
                while offset < len(hex_data):
                    # Calculate current data block
                    block = hex_data[offset:offset + max_block_size]
                    
                    # Build 36 service request
                    request = bytes([0x36, sequence_number]) + block
                    client.conn.send(request)
                    
                    # Wait and handle response
                    response = client.conn.wait_frame(timeout=5)
                    retry_count = 0
                    
                    # Handle pending response
                    while response and response.hex().upper() == '7F3678' and retry_count < 3:
                        self.log(f"Received 78 pending response, retry {retry_count+1}/3...")
                        response = client.conn.wait_frame(timeout=5)
                        retry_count += 1
                    
                    if not response or not response.hex().upper().startswith('76'):
                        self.log(f"Data transfer failed, sequence number: {sequence_number}, response: {response.hex().upper() if response else 'None'}")
                        return False
                        
                    self.log(f"Successfully transferred block {sequence_number}, length: {len(block)} bytes")
                    
                    # Update sequence number and offset
                    sequence_number = (sequence_number % 0xFF) + 1  # Sequence number cycle
                    offset += max_block_size

                self.log("Application data transfer complete")
                return True
                
        except Exception as e:
            self.log(f"Data transfer exception: {str(e)}")
            return False

    def verify_app_signature(self) -> bool:
        """Step 15: Verify application signature"""
        self.log("Step: Verify application signature")
        try:
            if not self.firmware_folder:
                self.log("Error: Firmware folder path not set")
                return False
                
            bin_path = os.path.join(self.firmware_folder, 'gen6nu_sign.bin')
            if not os.path.exists(bin_path):
                self.log(f"Error: Signature file does not exist: {bin_path}")
                return False
                
            with self.client as client:
                with open(bin_path, 'rb') as f:
                    bin_data = f.read(512)
                    
                header = bytes.fromhex('31 01 D0 02')
                request = header + bin_data
                client.conn.send(request)
                
                # Wait for response
                response = client.conn.wait_frame(timeout=3)
                if not response:
                    self.log("No response received")
                    return False
                    
                # 检查是否直接收到正响应
                if response.hex().upper() == '7101D00200':
                    self.log("Signature verification successful")
                    return True
                    
                # 如果收到中间响应，则继续等待最终响应
                if response.hex().upper() == '7F3178':
                    self.log("Received intermediate response, waiting for final response...")
                    final_response = client.conn.wait_frame(timeout=5)
                    if final_response and final_response.hex().upper() == '7101D00200':
                        self.log("Signature verification successful")
                        return True
                    else:
                        self.log(f"Signature verification failed, response: {final_response.hex().upper() if final_response else 'None'}")
                        return False
                
                # 如果既不是正响应也不是中间响应，则验证失败
                self.log(f"Unexpected response received: {response.hex().upper()}")
                return False
        except Exception as e:
            self.log(f"Signature verification exception: {str(e)}")
            return False

    def complete_flash_process(self) -> bool:
        """Step 16: Complete flash process"""
        self.log("Step: Complete flash process")
        try:
            with self.client as client:
                request = bytes.fromhex('31 01 FF 01')
                client.conn.send(request)
                
                # Wait for response
                response = client.conn.wait_frame(timeout=3)
                if not response:
                    self.log("No response received")
                    return False
                    
                # 检查是否直接收到正响应
                if response.hex().upper() == '7101FF0100':
                    self.log("Complete flash process successful")
                    return True
                    
                # 如果收到中间响应(78 pending或7F3178)，则继续等待最终响应
                if response.hex().upper() in ['7F3178', '7F3178']:
                    self.log("Received intermediate response, waiting for final response...")
                    final_response = client.conn.wait_frame(timeout=5)
                    if final_response and final_response.hex().upper() == '7101FF0100':
                        self.log("Complete flash process successful")
                        return True
                    else:
                        self.log(f"Complete flash process failed, response: {final_response.hex().upper() if final_response else 'None'}")
                        return False
                
                # 如果既不是正响应也不是中间响应，则验证失败
                self.log(f"Unexpected response received: {response.hex().upper()}")
                return False
            
        except Exception as e:
            self.log(f"Complete flash process exception: {str(e)}")
            return False

    def reset_ecu(self) -> bool:
        """Step 17: Reset ECU"""
        self.log("Step: Reset ECU")
        try:
            with self.client as client:
                request = bytes.fromhex('11 03')
                client.conn.send(request)
                response = client.conn.wait_frame(timeout=3)
                
                if response and response.hex().upper() == '5103':
                    self.log("ECU reset successful")
                    return True
                else:
                    self.log(f"ECU reset failed, response: {response.hex().upper() if response else 'None'}")
                    return False
        except Exception as e:
            self.log(f"ECU reset exception: {str(e)}")
            return False

    def check_programming_status(self) -> bool:
        """Step 18: Check programming status"""
        self.log("Step: Check programming status")
        try:
            with self.client as client:
                request = bytes.fromhex('22 F0 F0')
                client.conn.send(request)
                response = client.conn.wait_frame(timeout=3)
                
                if response and response.hex().upper().startswith('62'):
                    self.log("Version check successful")
                    return True
                else:
                    self.log(f"Version check failed, response: {response.hex().upper() if response else 'None'}")
                    return False
        except Exception as e:
            self.log(f"Programming status check exception: {str(e)}")
            return False

    def execute_flashing_sequence(self, firmware_folder: str) -> bool:
        """Execute complete flashing sequence"""
        self.firmware_folder = firmware_folder
        self.log("Start executing flashing sequence...")
        
        sbl_path = os.path.join(firmware_folder, 'gen6nu_sbl.hex')
        app_path = os.path.join(firmware_folder, 'gen6nu.hex')
        
        # 读取SBL文件
        self.sbl_data, self.sbl_start_addr, self.sbl_data_length = self.read_hex_file(sbl_path)
        if not self.sbl_data:
            self.log("Failed to read SBL HEX file")
            return False
            
        # 读取APP文件
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
                lambda:self.request_download('sbl'),                              # Step 7: Request download
                self.transfer_hex_data,                                           # Step 8: Transfer HEX data
                self.exit_transfer,                                               # Step 9: Exit transfer
                lambda: self.transfer_signature(os.path.join(firmware_folder, 'gen6nu_sbl_sign.bin')),  # Step 10: Transfer signature
                self.erase_memory,                                               # Step 11: Enter Flash mode
                lambda:self.request_download('app'),                             # Step 12: Request download application
                self.transfer_app_data,                                          # Step 13: Transfer application data
                self.exit_transfer,                                              # Step 14: Exit transfer
                self.verify_app_signature,                                       # Step 15: Verify application signature
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