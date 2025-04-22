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

class DoCANTester(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("IMS Tester ")
        self.geometry("800x600")
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Add CAN bus object property
        self.can_bus = None
        # Store channel configuration information
        self.channel_configs = {}
        
        # 添加ISOTP相关属性
        self.isotp_layer = None
        self.notifier = None
        
        # 使用ECUConfig加载配置
        self.ecu_config = ECUConfig()
        self.ecu_id_map = self.ecu_config.get_ecu_map()
        
        self.InitializeWidgets()
    def InitializeWidgets(self):
        self.InitializeConnectionWidgets()
        self.InitializeISOTPConsoleWidgets()

    def InitializeISOTPConsoleWidgets(self):
        # 创建ISOTP Console框架
        isotp_frame = ttk.LabelFrame(
            self.main_frame, 
            text="ISOTP Console",
            padding=(5, 5)
        )
        isotp_frame.pack(fill=tk.X, padx=5, pady=5)
        
        config_frame = ttk.LabelFrame(isotp_frame, text="Configuration", padding=(5, 5))
        config_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 创建水平布局的配置区域
        config_content = ttk.Frame(config_frame)
        config_content.pack(fill=tk.X, padx=0, pady=2)
        
        # ID配置部分
        id_frame = ttk.Frame(config_content)
        id_frame.pack(side=tk.LEFT, padx=10)
        
        ttk.Label(id_frame, text="ECU:").pack(side=tk.LEFT)
        self.ecu_combo = ttk.Combobox(id_frame, width=8, values=list(self.ecu_id_map.keys()))
        self.ecu_combo.pack(side=tk.LEFT, padx=(2, 10))
        self.ecu_combo.bind('<<ComboboxSelected>>', self.on_ecu_selected)
        self.ecu_combo.set('IMS')  # 设置默认值
        
        ttk.Label(id_frame, text="TX ID:").pack(side=tk.LEFT)
        self.tx_id_label = ttk.Label(id_frame, text="0x749")
        self.tx_id_label.pack(side=tk.LEFT, padx=(2, 10))
        
        ttk.Label(id_frame, text="RX ID:").pack(side=tk.LEFT)
        self.rx_id_label = ttk.Label(id_frame, text="0x759")
        self.rx_id_label.pack(side=tk.LEFT, padx=(2, 10))

        # ISOTP参数配置
        params_frame = ttk.Frame(config_content)
        params_frame.pack(side=tk.LEFT, padx=10)
        
        ttk.Label(params_frame, text="STmin:").pack(side=tk.LEFT)
        self.stmin_entry = ttk.Entry(params_frame, width=4)
        self.stmin_entry.pack(side=tk.LEFT, padx=(2, 10))
        self.stmin_entry.insert(0, "1")
        
        ttk.Label(params_frame, text="Block Size:").pack(side=tk.LEFT)
        self.blocksize_entry = ttk.Entry(params_frame, width=4)
        self.blocksize_entry.pack(side=tk.LEFT, padx=(2, 10))
        self.blocksize_entry.insert(0, "8")
        
        ttk.Label(params_frame, text="Padding:").pack(side=tk.LEFT)
        self.padding_entry = ttk.Entry(params_frame, width=4)
        self.padding_entry.pack(side=tk.LEFT, padx=(2, 10))
        self.padding_entry.insert(0, "00")
        
        # ISOTP控制按钮
        control_frame = ttk.Frame(config_content)
        control_frame.pack(side=tk.LEFT, padx=10)
        
        self.isotp_enable_button = ttk.Checkbutton(
            control_frame,
            text="Enable ISOTP",
            style="Toggle.TButton",
            command=self.on_isotp_toggle
        )
        self.isotp_enable_button.pack(side=tk.LEFT)
        
        # 创建右侧发送/接收框架
        comm_frame = ttk.Frame(isotp_frame)
        comm_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建数据请求与响应框架
        data_frame = ttk.LabelFrame(
            comm_frame,
            text="Data Request and Response",
            padding=(5, 5)
        )
        data_frame.pack(fill=tk.BOTH, expand=True)
        
        # 发送部分
        send_frame = ttk.Frame(data_frame)
        send_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(send_frame, text="Data (hex):").pack(side=tk.LEFT)
        self.isotp_data_entry = ttk.Entry(send_frame, width=50)
        self.isotp_data_entry.pack(side=tk.LEFT, padx=2)
        # 添加输入验证和格式化
        self.format_hex_input(self.isotp_data_entry.bind('<KeyRelease>', self.format_hex_input))
        self.send_button = ttk.Button(
            send_frame, 
            text="Send",
            width=8,
            command=self.send_isotp_data,
            state='disabled'
        )
        self.send_button.pack(side=tk.LEFT, padx=5)
        
        # 响应显示区域
        # 消息追踪框
        trace_frame = ttk.LabelFrame(
            comm_frame,
            text="Msg Trace of req and res",
            padding=(5, 5)
        )
        trace_frame.pack(fill=tk.BOTH, expand=True)

        # 追踪显示区域
        trace_container = ttk.Frame(trace_frame)
        trace_container.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(trace_container, text="Trace:").pack(anchor=tk.W, pady=(5,0))
        self.trace_text = tk.Text(trace_container, height=10, wrap=tk.WORD)
        self.trace_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 添加滚动条到右侧
        scrollbar = ttk.Scrollbar(trace_container, orient=tk.VERTICAL, command=self.trace_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.trace_text.configure(yscrollcommand=scrollbar.set)

        response_container = ttk.Frame(data_frame)
        response_container.pack(fill=tk.BOTH, expand=True)
        
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
    def format_hex_input(self, event):
        # """格式化十六进制输入，每两个字符之间添加空格"""
        # 获取当前输入内容并移除所有空格
        content = self.isotp_data_entry.get().replace(" ", "")
        # 移除非十六进制字符
        content = ''.join(c for c in content if c in '0123456789ABCDEFabcdef')
        # 每两个字符添加一个空格
        formatted = ' '.join(content[i:i+2] for i in range(0, len(content), 2))
        # 更新Entry的内容
        self.isotp_data_entry.delete(0, tk.END)
        self.isotp_data_entry.insert(0, formatted)
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
            print("CAN Parameter Configuration:")
            for key, value in params.items():
                print(f"  {key}: {value} ({type(value).__name__})")
                
            return params
        except Exception as e:
            self.show_error(f"Parameter format error: {str(e)}")
            return None

    def on_canfd_changed(self):
        """Handle CAN-FD checkbox state change"""
        # Clear current Entry content
        self.baudrate_entry.delete(0, tk.END)
        
        # Set parameters based on checkbox state
        if self.canfd_var.get():
            self.baudrate_entry.insert(0, self.default_canfd_params)
        else:
            self.baudrate_entry.insert(0, self.default_can_params)

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
            
            print(f"Selected channel: {selected_channel}")
            print(f"Channel ID: {channel_config.hw_channel}")
            
            if self.can_bus:
                self.can_bus.shutdown()
                
            self.can_bus = canlib.VectorBus(
                channel=channel_config.hw_channel,
                **params
            )
            
            # Disable all controls in connection frame
            self.hardware_combo.configure(state='disabled')
            self.scan_button.configure(state='disabled')
            self.baudrate_entry.configure(state='disabled')
            self.canfd_check.configure(state='disabled')
            
            # 启用ISOTP Enable按钮
            self.isotp_enable_button.configure(state='normal')
            
            print(f"CAN channel initialized successfully: {selected_channel} (ID: {channel_config.hw_channel})")
        
            # 启用ISOTP发送按钮
            self.send_button.configure(state='normal')
            
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
            
            print("CAN channel released")
            
        except Exception as e:
            self.show_error(f"Failed to release CAN channel: {str(e)}")

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

    def send_isotp_data(self):
        try:
            if not self.isotp_layer:
                self.show_error("请先启动ISOTP层")
                return
            
            # 获取并解析十六进制数据
            hex_data = self.isotp_data_entry.get().replace(" ", "")
            data = bytes.fromhex(hex_data)
            
            # 记录带时间的请求
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            self.trace_text.insert(tk.END, f"[{timestamp}] TX: {hex_data.upper()}\n")
            
            # 发送数据
            self.isotp_layer.send(data)
            
            # 等待响应
            try:
                response = self.isotp_layer.recv(timeout=1.0)
                response_hex = ' '.join([f"{x:02X}" for x in response])
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                self.trace_text.insert(tk.END, f"[{timestamp}] RX: {response_hex}\n")
                self.trace_text.see(tk.END)
            except Exception as e:
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                self.trace_text.insert(tk.END, f"[{timestamp}] Error: {str(e)}\n")
                
        except ValueError as e:
            self.show_error(f"参数格式错误: {str(e)}")
        except Exception as e:
            self.show_error(f"发送ISOTP数据失败: {str(e)}")
            
    def release_can(self):
        # 停止ISOTP层
        if self.isotp_layer:
            self.stop_isotp()
            self.isotp_enable_button.state(['!selected'])
        
        # 禁用ISOTP Enable按钮
        self.isotp_enable_button.configure(state='disabled')
        
        try:
            if self.can_bus:
                self.can_bus.shutdown()
                self.can_bus = None
                
            # Enable all controls in connection frame
            self.hardware_combo.configure(state='normal')
            self.scan_button.configure(state='normal')
            self.baudrate_entry.configure(state='normal')
            self.canfd_check.configure(state='normal')
            
            print("CAN channel released")
            
        except Exception as e:
            self.show_error(f"Failed to release CAN channel: {str(e)}")

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

    def on_ecu_selected(self, event):
        """处理ECU选择变化"""
        selected_ecu = self.ecu_combo.get()
        if selected_ecu in self.ecu_id_map:
            ecu_ids = self.ecu_id_map[selected_ecu]
            self.tx_id_label.configure(text=f"0x{ecu_ids['TXID']:03X}")
            self.rx_id_label.configure(text=f"0x{ecu_ids['RXID']:03X}")
            # 打印选择的ECU ID信息
            print(f"Selected ECU: {selected_ecu}")
            print(f"TX ID: 0x{ecu_ids['TXID']:03X}")
            print(f"RX ID: 0x{ecu_ids['RXID']:03X}")

    def on_isotp_toggle(self):
        """处理ISOTP Enable按钮的状态变化"""
        if self.isotp_enable_button.instate(['selected']):
            self.start_isotp()
        else:
            self.stop_isotp()
    
    def start_isotp(self):
        """启动ISOTP层"""
        try:
            if not self.can_bus:
                self.show_error("请先初始化CAN通道")
                return
            
            # 获取当前选择的ECU的ID
            selected_ecu = self.ecu_combo.get()
            if selected_ecu not in self.ecu_id_map:
                self.show_error("请选择有效的ECU")
                return
            
            ecu_ids = self.ecu_id_map[selected_ecu]
            tx_id = ecu_ids['TXID']
            rx_id = ecu_ids['RXID']
            
            stmin = int(self.stmin_entry.get())
            blocksize = int(self.blocksize_entry.get())
            padding = int(self.padding_entry.get(), 16)
            
            # 创建ISOTP参数
            isotp_params = {
                'stmin': stmin,
                'blocksize': blocksize,
                'tx_padding': padding,
                'rx_flowcontrol_timeout': 1000,
                'rx_consecutive_frame_timeout': 100,
                'can_fd': self.canfd_var.get()
            }
            
            # 创建地址对象
            tp_addr = isotp.Address(
                isotp.AddressingMode.Normal_11bits,
                txid=tx_id,
                rxid=rx_id
            )
            
            # 创建通知器
            self.notifier = can.Notifier(self.can_bus, [])
            
            # 创建ISOTP层
            self.isotp_layer = isotp.NotifierBasedCanStack(
                bus=self.can_bus,
                notifier=self.notifier,
                address=tp_addr,
                error_handler=None,
                params=isotp_params
            )
            
            # 启动ISOTP层
            self.isotp_layer.start()
            
            # 启用发送按钮
            self.send_button.configure(state='normal')
            print("ISOTP layer started")
            
        except Exception as e:
            self.show_error(f"启动ISOTP层失败: {str(e)}")
            self.isotp_enable_button.state(['!selected'])
    
    def stop_isotp(self):
        """停止ISOTP层"""
        try:
            if self.isotp_layer:
                self.isotp_layer.stop()
                self.isotp_layer = None
            
            if self.notifier:
                self.notifier.stop()
                self.notifier = None
            
            # 禁用发送按钮
            self.send_button.configure(state='disabled')
            print("ISOTP layer stopped")
            
        except Exception as e:
            self.show_error(f"停止ISOTP层失败: {str(e)}")

if __name__ == "__main__":
    app = DoCANTester()
    app.mainloop()

