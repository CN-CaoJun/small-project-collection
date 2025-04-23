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
from ecu_config import ECUConfig
from datetime import datetime
import threading

class IMS_DIAG(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("IMS Diagnostic Tool v1.2")
        self.geometry("1024x768")
        sv_ttk.use_dark_theme()  # 使用现代深色主题
        
        # 主界面布局
        self.main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True)
        
        # 左侧配置面板
        left_panel = ttk.Frame(self.main_paned, width=300)
        self.main_paned.add(left_panel, weight=0)
        self.InitializeConnectionWidgets(left_panel)
        self.InitializeISOTPWidgets(left_panel)
        
        # 右侧诊断面板
        right_panel = ttk.Frame(self.main_paned)
        self.main_paned.add(right_panel, weight=1)
        self.InitializeDiagServiceWidgets(right_panel)

    def InitializeDiagServiceWidgets(self, parent):
        # 诊断服务选项卡
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 常用服务页
        common_frame = ttk.Frame(notebook)
        notebook.add(common_frame, text="常用服务")
        ttk.Button(common_frame, text="读取DTC", command=self.read_dtc).pack(pady=2)
        ttk.Button(common_frame, text="清除DTC", command=self.clear_dtc).pack(pady=2)
        ttk.Button(common_frame, text="读取数据流", command=self.read_data_stream).pack(pady=2)
        
        # 编程服务页
        programming_frame = ttk.Frame(notebook)
        notebook.add(programming_frame, text="编程模式")
        ttk.Button(programming_frame, text="进入扩展会话", command=self.enter_extended).pack(pady=2)
        ttk.Button(programming_frame, text="安全校验", command=self.security_auth).pack(pady=2)
    def InitializeWidgets(self):
        self.InitializeConnectionWidgets()
    
    def InitializeConnectionWidgets(self):
        # Create groupbox frame
        connection_frame = ttk.LabelFrame(
            self.main_frame, 
            text="Connection",
            padding=(5, 5)
        )
        connection_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Create a frame to contain all controls
        controls_frame = ttk.Frame(connection_frame)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Hardware section
        hw_frame = ttk.Frame(controls_frame)
        hw_frame.pack(side=tk.LEFT, padx=5)
        ttk.Label(hw_frame, text="Hardware:").pack(anchor=tk.W)
        
        # Create a sub-frame to contain combo and refresh button
        hw_control_frame = ttk.Frame(hw_frame)
        hw_control_frame.pack(anchor=tk.W)
        
        self.hardware_combo = ttk.Combobox(hw_control_frame, values=[" "], width=24)
        self.hardware_combo.pack(side=tk.LEFT, padx=(0, 2))
        self.scan_button = ttk.Button(hw_control_frame, text="Scan", width=8, command=self.scan_vector_channels)
        self.scan_button.pack(side=tk.LEFT)
        
        # Baudrate section
        baud_frame = ttk.Frame(controls_frame)
        baud_frame.pack(side=tk.LEFT, padx=5)
        ttk.Label(baud_frame, text="Baudrate Parameters:").pack(anchor=tk.W)
        
        # Use Entry widget instead of Combobox
        self.default_can_params = "fd=False,bitrate=500000,tseg1_abr=63,tseg2_abr=16,sjw_abr=16"
        self.default_canfd_params = "fd=True,bitrate=500000,data_bitrate=2000000,tseg1_abr=63,tseg2_abr=16,sjw_abr=16,sam_abr=1,tseg1_dbr=13,tseg2_dbr=6,sjw_dbr=6"
        
        self.baudrate_entry = ttk.Entry(baud_frame, width=50)
        self.baudrate_entry.insert(0, self.default_can_params)
        self.baudrate_entry.pack(anchor=tk.W)
        
        # CAN-FD checkbox section
        canfd_frame = ttk.Frame(controls_frame)
        canfd_frame.pack(side=tk.LEFT, padx=5)
        ttk.Label(canfd_frame, text="CAN-FD:").pack(anchor=tk.W)
        self.canfd_var = tk.BooleanVar()
        self.canfd_check = ttk.Checkbutton(canfd_frame, text="CAN-FD", variable=self.canfd_var, command=self.on_canfd_changed)
        self.canfd_check.pack(anchor=tk.W)
        
        # Button section
        button_frame = ttk.Frame(controls_frame)
        button_frame.pack(side=tk.LEFT, padx=5)
        ttk.Label(button_frame, text="Operation:").pack(anchor=tk.W)
        
        self.style = ttk.Style()
        self.style.configure("Toggle.TButton", 
                           background="gray",
                           foreground="black")
        self.style.map("Toggle.TButton",
                      background=[("selected", "green"), ("!selected", "gray")],
                      foreground=[("selected", "white"), ("!selected", "black")])
        
        self.init_button = ttk.Checkbutton(
            button_frame, 
            text="Initialize",
            width=8,
            style="Toggle.TButton",
            command=self.on_init_toggle
        )
        self.init_button.pack(side=tk.LEFT, padx=2)
    
    def scan_vector_channels(self):
        try:
            # Check if XL driver is available
            if canlib.xldriver is None:
                self.show_error("Vector XL API is not available") 
                return
            
            # Open XL driver
            canlib.xldriver.xlOpenDriver()
            
            # Get channel configurations
            channel_configs = canlib.get_channel_configs()
            
            if not channel_configs:
                self.show_error("No Vector channels found") 
                return
            
            # Prepare channel list
            channel_list = []
            # Clear old configuration information
            self.channel_configs.clear()  
            
            # Display channel information
            for config in channel_configs:
                channel_name = f"{config.name}"
                channel_list.append(channel_name)
                # Store configuration information
                self.channel_configs[channel_name] = config
                print(f"Detected Channel - HW: {config.hw_channel}, Type: {config.hw_type.name if hasattr(config.hw_type, 'name') else config.hw_type}, Bus: {config.connected_bus_type.name if hasattr(config.connected_bus_type, 'name') else 'N/A'}, Index: {config.hw_index}") 
            
            # Update dropdown list
            self.hardware_combo['values'] = channel_list
            
            # Select the first channel if available
            if channel_list:
                self.hardware_combo.current(0)
                
        except Exception as e:
            self.show_error(f"Error scanning channels: {str(e)}") 
        finally:
            try:
                # Close XL driver
                canlib.xldriver.xlCloseDriver()
            except:
                pass
    
    def show_error(self, message):
        # Create error message window
        error_window = tk.Toplevel(self)
        error_window.title("Error") 
        error_window.geometry("300x100")
        
        label = ttk.Label(error_window, text=message, wraplength=250)
        label.pack(padx=20, pady=20)
        
        ok_button = ttk.Button(error_window, text="OK", command=error_window.destroy) 
        ok_button.pack(pady=10)

    def read_dtc(self):
        """UDS 19服务 - 读取故障码"""
        with self.create_uds_session() as uds:
            try:
                response = uds.read_dtc_information(0x0A)  # 读取所有DTC
                self.append_trace(f"DTC列表：{response.dtc_list}")
            except udsoncan.exceptions.NegativeResponseException as e:
                self.show_error(f"读取失败：{e.response_code.name}")

    def create_uds_session(self):
        """创建UDS会话上下文"""
        return udsoncan.Client(
            self.isotp_layer,
            request_timeout=5,
            config=udsoncan.configs.default_client_config
        )

    def append_trace(self, message):
        """安全添加跟踪信息"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.trace_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.trace_text.see(tk.END)
        self.status_var.set("最新操作：" + message)

    def InitializeISOTPWidgets(self, parent):
        # ISOTP控制台
        isotp_frame = ttk.LabelFrame(parent, text="ISOTP Console")
        isotp_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 消息跟踪框
        self.trace_text = tk.Text(isotp_frame, height=12, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(isotp_frame, command=self.trace_text.yview)
        self.trace_text.configure(yscrollcommand=scrollbar.set)
        
        self.trace_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 状态栏
        self.status_var = tk.StringVar()
        status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)