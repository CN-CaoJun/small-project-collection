import tkinter as tk
from tkinter import ttk
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

class ConnectionPack:
    def __init__(self, parent):
        self.parent = parent
        self.can_bus = None
        self.connected = False
        # Store channel configuration information
        self.channel_configs = {}
        # 创建控件
        self.fdcan = False
        self.trace_handler = self.parent.winfo_toplevel().get_trace_handler()
        self.create_widgets()
        
    def create_widgets(self):
        # 创建控件容器框架
        self.controls_frame = ttk.Frame(self.parent)
        self.controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Hardware部分
        self.hw_frame = ttk.Frame(self.controls_frame)
        self.hw_frame.pack(side=tk.LEFT, padx=5)
        ttk.Label(self.hw_frame, text="Hardware:").pack(anchor=tk.W)
        
        self.hw_control_frame = ttk.Frame(self.hw_frame)
        self.hw_control_frame.pack(anchor=tk.W)
        
        self.hardware_combo = ttk.Combobox(self.hw_control_frame, values=[" "], width=24)
        self.hardware_combo.pack(side=tk.LEFT, padx=(0, 2))
        self.scan_button = ttk.Button(self.hw_control_frame, text="Scan", width=8, 
                                    command=self.scan_can_device)
        self.scan_button.pack(side=tk.LEFT)
        
        # Baudrate部分
        self.baud_frame = ttk.Frame(self.controls_frame)
        self.baud_frame.pack(side=tk.LEFT, padx=5)
        ttk.Label(self.baud_frame, text="Baudrate Parameters:").pack(anchor=tk.W)
        
        # 默认参数设置
        self.default_can_params = "fd=False,bitrate=500000,tseg1_abr=63,tseg2_abr=16,sjw_abr=16"
        self.default_canfd_params = "fd=True,bitrate=500000,data_bitrate=2000000,tseg1_abr=63,tseg2_abr=16,sjw_abr=16,sam_abr=1,tseg1_dbr=13,tseg2_dbr=6,sjw_dbr=6"
        
        self.baudrate_entry = ttk.Entry(self.baud_frame, width=50)
        self.baudrate_entry.insert(0, self.default_can_params)
        self.baudrate_entry.pack(anchor=tk.W)
        
        # CAN-FD选项部分
        self.canfd_frame = ttk.Frame(self.controls_frame)
        self.canfd_frame.pack(side=tk.LEFT, padx=5)
        ttk.Label(self.canfd_frame, text="CAN-FD:").pack(anchor=tk.W)
        self.canfd_var = tk.BooleanVar(value=False)
        self.canfd_check = ttk.Checkbutton(self.canfd_frame, text="CAN-FD", 
                                         variable=self.canfd_var, 
                                         command=self.on_canfd_changed)
        self.canfd_check.pack(anchor=tk.W)
        
        # 操作按钮部分
        self.button_frame = ttk.Frame(self.controls_frame)
        self.button_frame.pack(side=tk.LEFT, padx=5)
        ttk.Label(self.button_frame, text="Operation:").pack(anchor=tk.W)
        
        # 设置按钮样式
        self.style = ttk.Style()
        self.style.configure("Toggle.TButton",
                           background="gray",
                           foreground="black")
        self.style.map("Toggle.TButton",
                      background=[("selected", "green"), ("!selected", "gray")],
                      foreground=[("selected", "white"), ("!selected", "black")])
        
        self.init_button = ttk.Checkbutton(
            self.button_frame,
            text="Initialize",
            width=8,
            style="Toggle.TButton",
            command=self.on_init_toggle
        )
        self.init_button.pack(side=tk.LEFT, padx=2)
    
    def scan_can_device(self):
        try:
            self.channel_configs.clear()
            channel_list = []

            # Scan SocketCAN interfaces on Linux
            try:
                import os
                import platform
                print(f"platform.system(): {platform.system()}")
                if platform.system() == 'Linux':
                    print("Scanning SocketCAN interfaces...")
                    net_path = "/sys/class/net"
                    if os.path.exists(net_path):
                        for name in os.listdir(net_path):
                            if name.startswith(('can', 'vcan', 'slcan')):
                                channel_name = f"SocketCAN: {name}"
                                channel_list.append(channel_name)
                                self.channel_configs[channel_name] = {
                                    'type': 'socketcan',
                                    'channel': name
                                }
                                self.log(f"Found SocketCAN interface: {name}")
            except Exception as e:
                self.log(f"SocketCAN scan error: {str(e)}")

            # Scan Vector devices
            if canlib.xldriver is not None:
                try:
                    canlib.xldriver.xlOpenDriver()
                    vector_configs = canlib.get_channel_configs()
                    
                    # self.log("\nVector设备配置信息:")
                    # for config in vector_configs:
                    #     self.log(f"通道名称: {config.name}")
                    #     self.log(f"硬件通道: {config.hw_channel}")
                    #     self.log(f"硬件类型: {config.hw_type}")
                    #     self.log(f"硬件索引: {config.hw_index}")
                    #     self.log(f"通道掩码: {config.channel_mask}")
                    #     self.log("------------------------")
                    
                    for config in vector_configs:
                        channel_name = f"{config.serial_number}: {config.name}"
                        channel_list.append(channel_name)
                        # Store device type and configuration
                        self.channel_configs[channel_name] = {
                            'type': 'vector',
                            'config': config,
                            'hw_channel': config.hw_channel
                        }
                except Exception as e:
                    self.log(f"Vector scan error: {str(e)}")
                finally:
                    canlib.xldriver.xlCloseDriver()

            # Scan PCAN devices
            try:
                from can.interfaces.pcan.basic import (
                    PCANBasic, PCAN_ERROR_OK, PCAN_NONEBUS,
                    LOOKUP_DEVICE_TYPE, LOOKUP_DEVICE_ID,
                    LOOKUP_CONTROLLER_NUMBER, LOOKUP_IP_ADDRESS,
                    PCAN_CHANNEL_FEATURES, FEATURE_FD_CAPABLE
                )
                param_str = b'devicetype=PCAN_USB'
                pcan = PCANBasic()
                result = pcan.LookUpChannel(param_str)
                
                if result[0] == PCAN_ERROR_OK:
                    handle = result[1]
                    if handle != PCAN_NONEBUS:
                        feature_result = pcan.GetValue(handle, PCAN_CHANNEL_FEATURES)
                        if feature_result[0] == PCAN_ERROR_OK:
                            fd_support = (feature_result[1] & FEATURE_FD_CAPABLE) == FEATURE_FD_CAPABLE
                            channel_name = f"PCAN: 0x{handle.value:02X} (FD support: {fd_support})"  # 添加.value获取实际值
                            channel_list.append(channel_name)
                            self.channel_configs[channel_name] = {
                                'type': 'pcan',
                                'handle': handle.value,  # 确保存储十六进制值
                                'features': fd_support
                            }
            except Exception as e:
                self.log(f"PCAN scan error: {str(e)}")

            try:
                from can.interfaces import slcan
                from serial.tools.list_ports import comports
                
                # 扫描所有可用串口
                for port in comports():
                    self.log(f"Found port: {port.device}, location: {port.location}")
                    if port.location is not None:
                        channel_name = f"SLCAN: {port.device}"
                        channel_list.append(channel_name)
                        self.channel_configs[channel_name] = {
                            'type': 'slcan',
                            'port': port.device,
                            'description': port.description,
                            'hwid': port.hwid
                        }
                        # 新增调试信息打印
                        self.log(f"SLCAN设备信息 - 端口: {port.device}")
                        self.log(f"描述: {port.description}")
                        self.log(f"硬件ID: {port.hwid}\n")
                        
            except Exception as e:
                self.log(f"SLCAN scan error: {str(e)}")

            # Update UI
            if channel_list:
                self.hardware_combo['values'] = channel_list
                self.hardware_combo.current(0)
            else:
                self.show_error("No CAN devices found")

        except Exception as e:
            self.show_error(f"Device scan failed: {str(e)}")

    def show_error(self, message):
        # Create error message window
        error_window = tk.Toplevel(self.parent)  # Use self.parent instead of self
        error_window.title("Error") 
        error_window.geometry("300x100")
        
        label = ttk.Label(error_window, text=message, wraplength=250)
        label.pack(padx=20, pady=20)
        
        ok_button = ttk.Button(error_window, text="OK", command=error_window.destroy) 
        ok_button.pack(pady=10)
    def on_canfd_changed(self):
        """CAN-FD选项改变时的处理"""
        if self.canfd_var.get():
            self.baudrate_entry.delete(0, tk.END)
            self.baudrate_entry.insert(0, self.default_canfd_params)
            self.fdcan = True
        else:
            self.baudrate_entry.delete(0, tk.END)
            self.baudrate_entry.insert(0, self.default_can_params)
            self.fdcan = False
    def on_init_toggle(self):
        """处理Initialize toggle按钮的状态变化"""
        if self.init_button.instate(['selected']):
            self.initialize_can()
            if not self.can_bus:  
                self.init_button.state(['!selected'])  
                self.init_button.configure(text="Initialize")
            else:
                self.init_button.configure(text="Release")  
        else:
            self.release_can()
            self.init_button.configure(text="Initialize") 
    def initialize_can(self):
        """Initialize CAN channel"""
        try:
            # Check if channel is selected
            selected_channel = self.hardware_combo.get()
            if not selected_channel:
                self.show_error("Please select a CAN channel first")
                return
            
            # Get selected channel configuration
            if selected_channel not in self.channel_configs:
                self.show_error("Cannot find configuration for selected channel")
                return
                
            channel_config = self.channel_configs[selected_channel]
            
            # Get baudrate parameters
            params = self.parse_baudrate_parameters()
            if not params:
                return
            
            if self.can_bus:
                self.can_bus.shutdown()
            
            self.log(f"channel_config['type']: {channel_config['type']}")
            
            if channel_config['type'] == 'pcan':
                from can.interfaces.pcan import PcanBus
                # 添加PCAN通道映射
                pcan_channel_map = {
                    0x51: "PCAN_USBBUS1",
                    0x52: "PCAN_USBBUS2",
                    0x53: "PCAN_USBBUS3",
                    0x54: "PCAN_USBBUS4"
                }
                handle = channel_config['handle']
                if handle not in pcan_channel_map:
                    raise ValueError(f"Unsupported PCAN channel handle: 0x{handle:02X}")
                self.can_bus = PcanBus(
                    channel=pcan_channel_map[handle],
                    bitrate=500000,
                    fd=False,
                )
            elif channel_config['type'] == 'vector':
                self.can_bus = canlib.VectorBus(
                    channel=channel_config['hw_channel'],  
                    **params
                )
            elif channel_config['type'] == 'slcan':
                from can.interfaces.slcan import slcanBus
                self.can_bus = slcanBus(
                    channel=channel_config['port'],
                    bitrate = 500000,
                )
            elif channel_config['type'] == 'socketcan':
                self.log(f"channel_config['channel']: {channel_config['channel']}")
                self.can_bus = can.Bus(
                    interface='socketcan',
                    channel=channel_config['channel'],
                    bitrate = 500000,
                    fd = False,
                )
            # Disable all controls in connection frame
            self.hardware_combo.configure(state='disabled')
            self.scan_button.configure(state='disabled')
            self.baudrate_entry.configure(state='disabled')
            self.canfd_check.configure(state='disabled')
            
            
        except Exception as e:
            self.show_error(f"Failed to initialize CAN channel: {str(e)}")
            self.init_button.state(['!selected'])  
    def release_can(self):
        """Release CAN channel"""
        try:
            if self.can_bus:
                self.can_bus.shutdown()
                self.can_bus = None
                
            # Enable all controls in connection frame
            self.hardware_combo.configure(state='normal')
            self.scan_button.configure(state='normal')
            self.baudrate_entry.configure(state='normal')
            self.canfd_check.configure(state='normal')
            
            self.log("CAN channel released")
            
        except Exception as e:
            self.show_error(f"Failed to release CAN channel: {str(e)}")

    def parse_baudrate_parameters(self):
        params = {}
        try:
            # Split parameter string and convert to dictionary
            param_str = self.baudrate_entry.get()
            param_pairs = param_str.split(',')
            for pair in param_pairs:
                key, value = pair.split('=')
                key = key.strip()
                value = value.strip()
                
                # Handle boolean values
                if value.lower() == 'true':
                    params[key] = True
                elif value.lower() == 'false':
                    params[key] = False
                else:
                    # Handle numeric values
                    try:
                        params[key] = int(value)
                    except ValueError:
                        # Keep original string if cannot convert to integer
                        params[key] = value
            
            # Print all parameters
            self.log("CAN Parameter Configuration:")
            for key, value in params.items():
                self.log(f"  {key}: {value} ({type(value).__name__})")
                
            return params
        except Exception as e:
            self.show_error(f"Parameter format error: {str(e)}")
            return None
    def get_can_bus(self):
        return self.can_bus, self.fdcan

    def log(self, message: str):
        if self.trace_handler is None:
            self.trace_handler = self.parent.winfo_toplevel().get_trace_handler()
            
        self.trace_handler(message)

    
    