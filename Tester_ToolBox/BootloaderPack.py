import logging
import tkinter as tk
from tkinter import ttk
import sys
import os
import logging

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
from BootloaderPackFlash import FlashingProcess 
from udsoncan import services
from udsoncan.services import ReadDataByIdentifier

class BootloaderPack:
    def __init__(self, parent):
        self.parent = parent
        self.trace_handler = self.parent.winfo_toplevel().get_trace_handler()
        self.uds_client = None
        self.is_flashing = False
        self.flash_config = {}
        self.create_widgets()
    
    def init_uds_client(self):
        try:
            # Get CAN bus object from main window
            main_window = self.parent.winfo_toplevel()
            can_bus ,isfd = main_window.connection.get_can_bus()
            
            if not can_bus:
                if self.ensure_trace_handler():
                    self.trace_handler("Error: CAN bus not initialized")
                return False
            
            # logging.basicConfig(
            #     level=logging.WARN,
            #     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            #     handlers=[
            #         logging.FileHandler('bootloader_flash.log', encoding='utf-8'),  
            #         logging.StreamHandler()  
            #     ]
            # )
            
            # Configure ISO-TP parameters
            if isfd:
                isotp_params = {
                    'stmin': 0,
                    'blocksize': 0,
                    'tx_padding': 0x00,
                    'override_receiver_stmin': None,
                    'wftmax': 4,
                    'tx_data_length': 64,
                    'tx_data_min_length':8,
                    'rx_flowcontrol_timeout': 1000,
                    'rx_consecutive_frame_timeout': 100,
                    'can_fd': True,
                    'max_frame_size': 4095,
                    'bitrate_switch': False,
                    'rate_limit_enable': False,
                    'listen_mode': False,
                    'blocking_send': False
                }
                if self.ensure_trace_handler():
                    self.trace_handler("Using CAN-FD ISO-TP parameters")
            else:
                isotp_params = {
                    'stmin': 0,
                    'blocksize': 0,
                    'tx_padding': 0x00,
                    'override_receiver_stmin': None,
                    'wftmax': 4,
                    'tx_data_length': 8,
                    'tx_data_min_length':8,
                    'rx_flowcontrol_timeout': 1000,
                    'rx_consecutive_frame_timeout': 100,
                    'can_fd': False,
                    'max_frame_size': 4095,
                    'bitrate_switch': False,
                    'rate_limit_enable': False,
                    'listen_mode': False,
                    'blocking_send': False  
                }
                if self.ensure_trace_handler():
                    self.trace_handler("Using Standard CAN ISO-TP parameters")
            
            # Create notifier
            self.notifier = can.Notifier(can_bus, [])
            
            # Configure ISO-TP address
            tp_addr = isotp.Address(
                isotp.AddressingMode.Normal_11bits,
                txid=0x730,  # Transmit ID
                rxid=0x738   # Receive ID
            )
            
            # Create ISO-TP stack
            self.stack = isotp.NotifierBasedCanStack(
                bus=can_bus,
                notifier=self.notifier,
                address=tp_addr,
                params=isotp_params
            )
            
            # Create UDS connection
            conn = PythonIsoTpConnection(self.stack)
            
            # Configure UDS client
            uds_config = udsoncan.configs.default_client_config.copy()
            uds_config['data_identifiers'] = {
                'default': '>H',
                0x7705: FlexRawData(30),
                0xF15A: FlexRawData(9),
                0xF0F0: FlexRawData(1),
                0x4611: FlexRawData(32),
            }
            # Modify timeout configuration
            uds_config['p2_timeout'] = 5 # Increased to 2 seconds
            uds_config['p2_star_timeout'] = 5
            uds_config['request_timeout'] = 5  # Increased total timeout
            uds_config['session_timing'] = {
                'p2_server_max': 5,  # Server maximum response time
                'p2_star_server_max': 5  # Server maximum extended response time
            }
            
            # Print UDS configuration information
            if self.ensure_trace_handler():
                self.trace_handler("UDS Configuration Information:")
                for key, value in uds_config.items():
                    self.trace_handler(f"  {key}: {value}")
            
            self.uds_client = Client(conn, config=uds_config)
            
            if self.ensure_trace_handler():
                self.trace_handler("UDS client initialization successful")
            return True
            
        except Exception as e:
            if self.ensure_trace_handler():
                self.trace_handler(f"UDS client initialization failed: {str(e)}")
            return False
            
    def close_uds_connection(self):
        """Close UDS connection"""
        try:
            if self.uds_client:
                self.notifier.stop()
                self.uds_client = None
                if self.ensure_trace_handler():
                    self.trace_handler("UDS connection closed")
        except Exception as e:
            if self.ensure_trace_handler():
                self.trace_handler(f"Failed to close UDS connection: {str(e)}")

    def ensure_trace_handler(self):
        """Ensure trace_handler is available"""
        if self.trace_handler is None:
            self.trace_handler = self.parent.winfo_toplevel().get_trace_handler()
        return self.trace_handler is not None

    def toggle_uds_client(self):
        """Toggle UDS client connection status"""
        if self.uds_client is None:
            # Try to initialize UDS client
            if self.init_uds_client():
                self.init_uds_btn.config(text="Close UDS Client")
                self.uds_status_label.config(text="UDS Client: Connected", foreground="green")
                # start test present
                self.start_tester_present_thread()
            else:
                self.uds_status_label.config(text="UDS Client: Connection Failed", foreground="red")
        else:
            # stop test present
            self.stop_tester_present_thread()
            # Close UDS client
            self.close_uds_connection()
            self.init_uds_btn.config(text="Init UDS Client")
            self.uds_status_label.config(text="UDS Client: Offline", foreground="black")

    def start_tester_present_thread(self):
        self.tester_present_running = True
        self.tester_present_thread = threading.Thread(target=self._tester_present_loop, daemon=True)
        self.tester_present_thread.start()

    def stop_tester_present_thread(self):
        self.tester_present_running = False
        if hasattr(self, 'tester_present_thread'):
            self.tester_present_thread = None

    def _tester_present_loop(self):
        while self.tester_present_running and self.uds_client:
            try:
                if not hasattr(self, 'is_flashing') or not self.is_flashing:
                    with self.uds_client as client:
                        response = client.tester_present()
                        if response:
                            if response.positive:
                                self.uds_status_label.config(text="UDS Client: Online", foreground="green")
                        else: 
                            self.uds_status_label.config(text="UDS Client: Offline", foreground="red")
                        
            except Exception as e:
                if self.ensure_trace_handler():
                    self.trace_handler(f"TesterPresent error: {str(e)}")
                    self.uds_status_label.config(text="UDS Client: Offline", foreground="red")
            
            time.sleep(3.0)
    
    def perform_ecu_reset(self):
        """Execute ECU reset"""
        try:
            if not self.uds_client:
                if self.ensure_trace_handler():
                    self.trace_handler("Error: UDS client not connected")
                return False
                
            with self.uds_client as client:
                # Send hardware reset command (reset_type=1 indicates hardware reset)
                response = client.ecu_reset(reset_type=1)
                
                if response and self.trace_handler:
                    # Print complete response content
                    self.trace_handler(f"ECU reset command sent, response content: {response.data.hex().upper()}")
                return True if response else False
                
        except Exception as e:
            if self.ensure_trace_handler():
                self.trace_handler(f"ECU reset failed: {str(e)}")
            return False

    def start_flashing(self):
        """Start flashing process"""
        def flash_thread():
            try:
                self.is_flashing = True
                self.uds_status_label.config(text="UDS Client: Online", foreground="green")
                # Immediately disable button (main thread operation)
                self.start_flash_btn.config(state=tk.DISABLED)
                flashing = FlashingProcess(self.uds_client, self.trace_handler)
                success = flashing.execute_flashing_sequence(
                    sbl_hex_path=self.flash_config['sbl_hex'],
                    app_hex_path=self.flash_config['app_hex']
                )
                self.status_label.config(text="Flashing Ongoing", foreground="green")
                self.update_flash_status(success)
            except Exception as e:
                self.show_flash_error(str(e))
            finally:
                self.is_flashing = False
                self.uds_status_label.config(text="Wait TesterPresent", foreground="green")
                self.start_flash_btn.config(state=tk.NORMAL)

        threading.Thread(target=flash_thread, daemon=True).start()

    def update_flash_status(self, success):
        """Update flashing status"""
        try:
            if success:
                self.status_label.config(text="Flashing Complete", foreground="green")
                if self.ensure_trace_handler():
                    self.trace_handler("Flashing process completed")
            else:
                self.status_label.config(text="Flashing Failed", foreground="red")
        except Exception as e:
            if self.ensure_trace_handler():
                self.trace_handler(f"Status update exception: {str(e)}")

    def show_flash_error(self, error):
        """Display error message"""
        try:
            self.status_label.config(text=f"Unexpected Err", foreground="red")
            if self.ensure_trace_handler():
                self.trace_handler(f"Flashing error: {error}")
        except Exception as e:
            if self.ensure_trace_handler():
                self.trace_handler(f"Error handling exception: {str(e)}")

    def get_version(self):
        try:
            if not self.uds_client:
                if self.ensure_trace_handler():
                    self.trace_handler("Error: UDS client not connected")
                return False
                
            with self.uds_client as client:
                # Read DID 0x7705 using UDS service
                response = client.read_data_by_identifier(0x4611)
                
                if response and response.service_data.values:
                    # Get raw data from response
                    data = response.service_data.values[0x4611]
                    # Convert version information to ASCII string
                    version_str = data.decode('ascii', errors='ignore').strip()
                    # Update version information label in UI
                    self.version_label.config(
                        text=f"Ver: {version_str[:12]}",
                        foreground="green"
                    )
                    # Log complete version information to trace handler
                    if self.ensure_trace_handler():
                        log_msg = (
                            f"Complete version information:\n"
                            f"  Version: {version_str}\n"
                        )
                        self.trace_handler(log_msg)
                    return True
                else:
                    # Handle failed response
                    err_msg = "Failed to get version information"
                    self.version_label.config(
                        text=err_msg,
                        foreground="red"
                    )
                    if self.ensure_trace_handler():
                        self.trace_handler(err_msg)
                    return False
                    
        except Exception as e:
            # Handle any exceptions during version retrieval
            err_msg = f"Version retrieval exception: {str(e)}"
            self.version_label.config(
                text=err_msg,
                foreground="red"
            )
            if self.ensure_trace_handler():
                self.trace_handler(err_msg)
            return False
    def select_file(self, file_type):
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(
            title=f"选择{file_type.upper()}文件",
            filetypes=[("HEX files", "*.hex"), ("All files", "*.*")]
        )
        if file_path:
            if file_type == 'sbl':
                # 获取文件最后修改时间
                mod_time = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
                self.sbl_path_label.config(text=f"[ {os.path.basename(file_path)} ] Last Modified: {mod_time}", foreground="green")
                self.flash_config['sbl_hex'] = file_path
            else:
                # 获取文件最后修改时间
                mod_time = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
                self.app_path_label.config(text=f"[{os.path.basename(file_path)} ] Last Modified: {mod_time}", foreground="green")
                self.flash_config['app_hex'] = file_path
            
            if 'sbl_hex' in self.flash_config and 'app_hex' in self.flash_config:
                if os.path.exists(self.flash_config['sbl_hex']) and os.path.exists(self.flash_config['app_hex']):
                    if self.ensure_trace_handler():
                        self.trace_handler("Config check PASS - All required files found")
                    self.start_flash_btn.config(state=tk.NORMAL)
                    return
            
            self.start_flash_btn.config(state=tk.DISABLED)
    def create_widgets(self):
        self.bootloader_frame = ttk.LabelFrame(self.parent, text="Operation")
        self.bootloader_frame.pack(fill=tk.X, padx=5, pady=5, expand=False)

        # Create file path display frame
        self.file_frame = ttk.Frame(self.bootloader_frame)
        self.file_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # SBL file path display frame
        self.sbl_frame = ttk.Frame(self.file_frame)
        self.sbl_frame.pack(fill=tk.X, padx=5, pady=2)
        
        self.sbl_label = ttk.Label(self.sbl_frame, text="SBL File: ")
        self.sbl_label.pack(side=tk.LEFT, padx=(0,5))
        
        self.sbl_path_label = ttk.Label(
            self.sbl_frame, 
            text="N/A",
            relief="solid",  # 添加边框
            borderwidth=1,   # 设置边框宽度
            width=30,        # 设置固定宽度
            anchor="w",      # 文本左对齐
            padding=(5,2)    # 内边距
        )
        self.sbl_path_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.sbl_select_btn = ttk.Button(
            self.sbl_frame,
            text="Select SBL",
            command=lambda: self.select_file('sbl')
        )
        self.sbl_select_btn.pack(side=tk.RIGHT, padx=5)
        
        # APP file path display frame
        self.app_frame = ttk.Frame(self.file_frame)
        self.app_frame.pack(fill=tk.X, padx=5, pady=2)
        
        self.app_label = ttk.Label(self.app_frame, text="APP File:")
        self.app_label.pack(side=tk.LEFT, padx=(0,5))
        
        self.app_path_label = ttk.Label(
            self.app_frame, 
            text="N/A",
            relief="solid",  # 添加边框
            borderwidth=1,   # 设置边框宽度
            width=30,        # 设置固定宽度
            anchor="w",      # 文本左对齐
            padding=(5,2)    # 内边距
        )
        self.app_path_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.app_select_btn = ttk.Button(
            self.app_frame,
            text="Select APP",
            command=lambda: self.select_file('app')
        )
        self.app_select_btn.pack(side=tk.RIGHT, padx=5)
        
        # 添加UDS初始化控制框架
        self.uds_control_frame = ttk.Frame(self.bootloader_frame)
        self.uds_control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 添加UDS初始化按钮
        self.init_uds_btn = ttk.Button(
            self.uds_control_frame,
            text="Init UDS Client",
            command=self.toggle_uds_client
        )
        self.init_uds_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 添加UDS连接状态标签
        self.uds_status_label = ttk.Label(
            self.uds_control_frame,
            text="UDS Client: Not Connected",
            font=('Arial', 9)
        )
        self.uds_status_label.pack(side=tk.LEFT, padx=5)
        
        # # 添加ECU复位按钮
        # self.ecu_reset_btn = ttk.Button(
        #     self.uds_control_frame,
        #     text="ECU Reset",
        #     command=self.perform_ecu_reset
        # )
        # self.ecu_reset_btn.pack(side=tk.LEFT, padx=(10, 5))
        
        # 添加开始刷写按钮
        self.start_flash_btn = ttk.Button(
            self.uds_control_frame,
            text="Start Flashing",
            command=self.start_flashing,
            state=tk.DISABLED  # 初始状态设置为禁用
        )
        self.start_flash_btn.pack(side=tk.LEFT, padx=(10, 5))
        
        # 添加刷写状态标签
        self.status_label = ttk.Label(
            self.uds_control_frame,
            text="Status: Ready",
            font=('Arial', 9),
            foreground="black"
        )
        self.status_label.pack(side=tk.LEFT, padx=(5, 10))
        
        # 在现有按钮后添加版本获取按钮
        self.get_version_btn = ttk.Button(
            self.uds_control_frame,
            text="Get Version",
            command=self.get_version
        )
        self.get_version_btn.pack(side=tk.LEFT, padx=(10, 5))
        
        # 添加版本信息显示标签
        self.version_label = ttk.Label(
            self.uds_control_frame,
            text="Version: N/A",
            font=('Arial', 9),
            foreground="gray"
        )
        self.version_label.pack(side=tk.LEFT, padx=(10, 0))

class FlexRawData(udsoncan.DidCodec):
    def __init__(self, length: int):
        self.data_length = length
    def encode(self, val):
        if not isinstance(val, (bytes, bytearray)):
            raise ValueError("Input data must be bytes or bytearray type")
        
        if len(val) != self.data_length:
            raise ValueError('Data length must be 30 bytes')
            
        return val  # Return raw data directly
    def decode(self, payload):
        if len(payload) != self.data_length:
            raise ValueError('Received data length must be 30 bytes')
            
        return payload  # Return raw data directly
    def __len__(self):
        return self.data_length

