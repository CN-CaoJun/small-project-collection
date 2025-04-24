import tkinter as tk
from tkinter import ttk
import sv_ttk
import sys
import os

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
        self.create_widgets()
    
    def init_uds_client(self):
        try:
            # Get CAN bus object from main window
            main_window = self.parent.winfo_toplevel()
            can_bus = main_window.connection.get_can_bus()
            
            if not can_bus:
                if self.ensure_trace_handler():
                    self.trace_handler("Error: CAN bus not initialized")
                return False
                
            # Configure ISO-TP parameters
            isotp_params = {
                'stmin': 10,
                'blocksize': 8,
                'wftmax': 0,
                'tx_data_length': 8,
                'tx_data_min_length': None,
                'tx_padding': 0,
                'rx_flowcontrol_timeout': 2000,    # Increased to 2000ms
                'rx_consecutive_frame_timeout': 2000,  # Increased to 2000ms
                'override_receiver_stmin': None,
                'max_frame_size': 4095,
                'can_fd': False,
                'bitrate_switch': False,
                'rate_limit_enable': False,
                'listen_mode': False
            }
            
            # Create notifier
            self.notifier = can.Notifier(can_bus, [])
            
            # Configure ISO-TP address
            tp_addr = isotp.Address(
                isotp.AddressingMode.Normal_11bits,
                txid=0x749,  # Transmit ID
                rxid=0x759   # Receive ID
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
                'default' : '>H',                     
            }
            # Modify timeout configuration
            uds_config['p2_timeout'] = 2  # Increased to 2 seconds
            uds_config['p2_star_timeout'] = 5  
            uds_config['request_timeout'] = 4  # Increased total timeout
            uds_config['session_timing'] = {
                'p2_server_max': 2,  # Server maximum response time
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

    def select_firmware_folder(self):
        """Handle folder selection"""
        from tkinter import filedialog
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.folder_path.set(folder_selected)
            required_files = {'gen6nu.hex', 'gen6nu_sbl.hex', 'gen6nu_sbl_sign.bin', 'gen6nu_sign.bin'}
            existing_files = set(os.listdir(folder_selected))
            missing_files = required_files - existing_files
            
            try:
                if self.ensure_trace_handler():
                    self.trace_handler(f"Selected firmware folder: {folder_selected}")
                    
                    # Update status label and Start Flashing button state
                    if not missing_files:
                        self.status_label.config(text="File Check PASS", foreground="green")
                        self.trace_handler("File check PASS - All required files found")
                        self.start_flash_btn.config(state=tk.NORMAL)  # 启用按钮
                    else:
                        self.status_label.config(
                            text=f"File Check FAILED\nMissing: {', '.join(missing_files)}",
                            foreground="red"
                        )
                        self.trace_handler(f"File check FAILED - Missing files: {', '.join(missing_files)}")
                        self.start_flash_btn.config(state=tk.DISABLED)  # 禁用按钮
                else:
                    print("Warning: Trace handler not available")
            except Exception as e:
                print(f"Error in trace handling: {str(e)}")
                # Ensure status label and button state are still updated
                if not missing_files:
                    self.status_label.config(text="File Check PASS", foreground="green")
                    self.start_flash_btn.config(state=tk.NORMAL)  # 启用按钮
                else:
                    self.status_label.config(
                        text=f"File Check FAILED\nMissing: {', '.join(missing_files)}",
                        foreground="red"
                    )
                    self.start_flash_btn.config(state=tk.DISABLED)  # 禁用按钮

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
            self.uds_status_label.config(text="UDS Client: Not Connected", foreground="black")

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
                        client.conn.send(bytes.fromhex('3E 00'))
                        response = client.conn.wait_frame(timeout=0.5)
                        if response:
                            if self.ensure_trace_handler():
                                self.trace_handler(f"TesterPresent response: {response.hex().upper()}")
                        if response and response.hex().upper() != '7E00':
                            if self.ensure_trace_handler():
                                self.trace_handler(f"Unexpected TesterPresent response: {response.hex().upper()}")
            except Exception as e:
                if self.ensure_trace_handler():
                    self.trace_handler(f"TesterPresent error: {str(e)}")
            time.sleep(2)
    
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
                # 设置刷写标志，暂停TesterPresent发送
                self.is_flashing = True
                # Immediately disable button (main thread operation)
                self.start_flash_btn.config(state=tk.DISABLED)
                flashing = FlashingProcess(self.uds_client, self.trace_handler)
                success = flashing.execute_flashing_sequence(self.folder_path.get())
                self.update_flash_status(success)
            except Exception as e:
                self.show_flash_error(str(e))
            finally:  
                # 清除刷写标志，恢复TesterPresent发送
                self.is_flashing = False
                # Restore button state (main thread operation)
                self.start_flash_btn.config(state=tk.NORMAL)

        # Start thread directly
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
            self.status_label.config(text=f"Error: {error}", foreground="red")
            if self.ensure_trace_handler():
                self.trace_handler(f"Flashing error: {error}")
        except Exception as e:
            if self.ensure_trace_handler():
                self.trace_handler(f"Error handling exception: {str(e)}")

    def get_version(self):
        """Get ECU version number"""
        try:
            if not self.uds_client:
                if self.ensure_trace_handler():
                    self.trace_handler("Error: UDS client not connected")
                return False
                
            with self.uds_client as client:
                # Send raw 22 77 05 request
                request = bytes.fromhex('22 77 05')
                client.conn.send(request)
                response = client.conn.wait_frame(timeout=3)
                
                if response and response.hex().upper().startswith('627705'):
                    # Parse complete data structure: 62 77 05 [10 bytes version] [12 bytes date] [8 bytes time]
                    version_data = response[3:13]   # 10 bytes version info
                    date_data = response[13:25]     # 12 bytes date data
                    time_data = response[25:33]     # 8 bytes time data
                    
                    # Convert version information
                    version_str = version_data.decode('ascii', errors='ignore').strip()
                    
                    # Convert date information (assuming ASCII format)
                    try:
                        date_str = date_data.decode('ascii', errors='ignore').strip()
                    except:
                        date_str = "Date parsing failed"
                        
                    # Convert time information (assuming ASCII format)
                    try:
                        time_str = time_data.decode('ascii', errors='ignore').strip()
                    except:
                        time_str = "Time parsing failed"
                    
                    # Update version information label
                    self.version_label.config(
                        text=f"Ver: {version_str}",
                        foreground="green"
                    )
                    
                    # Log to tracehandler
                    if self.ensure_trace_handler():
                        log_msg = (
                            f"Complete version information:\n"
                            f"  Version: {version_str}\n"
                            f"  Date: {date_str} \n"
                            f"  Time: {time_str} "
                        )
                        self.trace_handler(log_msg)
                    return True
                else:
                    err_msg = f"Failed to get version, response: {response.hex().upper() if response else 'No response'}"
                    self.status_label.config(
                        text=err_msg,
                        foreground="red"
                    )
                    if self.ensure_trace_handler():
                        self.trace_handler(err_msg)
                    return False
                    
        except Exception as e:
            err_msg = f"Version retrieval exception: {str(e)}"
            self.status_label.config(
                text=err_msg,
                foreground="red"
            )
            if self.ensure_trace_handler():
                self.trace_handler(err_msg)
            return False

    def create_widgets(self):
        # 主框架容器
        self.bootloader_frame = ttk.LabelFrame(self.parent, text="Operation")
        self.bootloader_frame.pack(fill=tk.X, padx=5, pady=5, expand=False)

        # 添加文件夹选择控件
        self.folder_selector_frame = ttk.Frame(self.bootloader_frame)
        self.folder_selector_frame.pack(fill=tk.X, padx=5, pady=5)

        # 文件夹选择按钮
        self.select_btn = ttk.Button(
            self.folder_selector_frame,
            text="Select BIN folder",
            command=self.select_firmware_folder
        )
        self.select_btn.pack(side=tk.LEFT, padx=(0, 5))

        # 路径显示框
        self.folder_path = tk.StringVar()
        self.path_entry = ttk.Entry(
            self.folder_selector_frame,
            textvariable=self.folder_path,
            state='readonly',
            width=50
        )
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 在路径显示框下添加状态标签
        self.status_label = ttk.Label(
            self.folder_selector_frame,
            text="File Check: Not Performed",
            font=('Arial', 9)
        )
        self.status_label.pack(side=tk.LEFT, padx=5)

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
        
        # 添加ECU复位按钮
        self.ecu_reset_btn = ttk.Button(
            self.uds_control_frame,
            text="ECU Reset",
            command=self.perform_ecu_reset
        )
        self.ecu_reset_btn.pack(side=tk.LEFT, padx=(10, 5))
        
        # 添加开始刷写按钮
        self.start_flash_btn = ttk.Button(
            self.uds_control_frame,
            text="Start Flashing",
            command=self.start_flashing,
            state=tk.DISABLED  # 初始状态设置为禁用
        )
        self.start_flash_btn.pack(side=tk.LEFT, padx=(10, 5))
        
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