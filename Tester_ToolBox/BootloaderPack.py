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
            # 获取主窗口的CAN总线对象
            main_window = self.parent.winfo_toplevel()
            can_bus = main_window.connection.get_can_bus()
            
            if not can_bus:
                if self.ensure_trace_handler():
                    self.trace_handler("错误：CAN总线未初始化")
                return False
                
            # 配置ISO-TP参数
            isotp_params = {
                'stmin': 10,
                'blocksize': 8,
                'wftmax': 0,
                'tx_data_length': 8,
                'tx_data_min_length': None,
                'tx_padding': 0,
                'rx_flowcontrol_timeout': 2000,    # 增加到2000毫秒
                'rx_consecutive_frame_timeout': 2000,  # 增加到2000毫秒
                'override_receiver_stmin': None,
                'max_frame_size': 4095,
                'can_fd': False,
                'bitrate_switch': False,
                'rate_limit_enable': False,
                'listen_mode': False
            }
            
            # 创建notifier
            self.notifier = can.Notifier(can_bus, [])
            
            # 配置ISO-TP地址
            tp_addr = isotp.Address(
                isotp.AddressingMode.Normal_11bits,
                txid=0x749,  # 发送ID
                rxid=0x759   # 接收ID
            )
            
            # 创建ISO-TP栈
            self.stack = isotp.NotifierBasedCanStack(
                bus=can_bus,
                notifier=self.notifier,
                address=tp_addr,
                params=isotp_params
            )
            
            # 创建UDS连接
            conn = PythonIsoTpConnection(self.stack)
            
            # 配置UDS客户端
            uds_config = udsoncan.configs.default_client_config.copy()
            uds_config['data_identifiers'] = {
                'default' : '>H',                     
            }
            # 修改超时配置
            uds_config['p2_timeout'] = 2  # 增加到2秒
            uds_config['p2_star_timeout'] = 5  
            uds_config['request_timeout'] = 4  # 增加总体超时时间
            uds_config['session_timing'] = {
                'p2_server_max': 2,  # 服务器最大响应时间
                'p2_star_server_max': 5  # 服务器最大扩展响应时间
            }
            
            # 打印UDS配置信息
            if self.ensure_trace_handler():
                self.trace_handler("UDS配置信息:")
                for key, value in uds_config.items():
                    self.trace_handler(f"  {key}: {value}")
            
            self.uds_client = Client(conn, config=uds_config)
            
            if self.ensure_trace_handler():
                self.trace_handler("UDS客户端初始化成功")
            return True
            
        except Exception as e:
            if self.ensure_trace_handler():
                self.trace_handler(f"UDS客户端初始化失败: {str(e)}")
            return False
            
    def close_uds_connection(self):
        """关闭UDS连接"""
        try:
            if self.uds_client:
                self.notifier.stop()
                self.uds_client = None
                if self.ensure_trace_handler():
                    self.trace_handler("UDS连接已关闭")
        except Exception as e:
            if self.ensure_trace_handler():
                self.trace_handler(f"关闭UDS连接失败: {str(e)}")
            
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
            command=self.start_flashing
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

    def ensure_trace_handler(self):
        """确保trace_handler可用"""
        if self.trace_handler is None:
            self.trace_handler = self.parent.winfo_toplevel().get_trace_handler()
        return self.trace_handler is not None

    def select_firmware_folder(self):
        """处理文件夹选择"""
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
                    
                    # 更新状态标签
                    if not missing_files:
                        self.status_label.config(text="File Check PASS", foreground="green")
                        self.trace_handler("File check PASS - All required files found")
                    else:
                        self.status_label.config(
                            text=f"File Check FAILED\nMissing: {', '.join(missing_files)}",
                            foreground="red"
                        )
                        self.trace_handler(f"File check FAILED - Missing files: {', '.join(missing_files)}")
                else:
                    print("Warning: Trace handler not available")
            except Exception as e:
                print(f"Error in trace handling: {str(e)}")
                # 确保状态标签仍然更新
                if not missing_files:
                    self.status_label.config(text="File Check PASS", foreground="green")
                else:
                    self.status_label.config(
                        text=f"File Check FAILED\nMissing: {', '.join(missing_files)}",
                        foreground="red"
                    )

    def toggle_uds_client(self):
        """切换UDS客户端连接状态"""
        if self.uds_client is None:
            # 尝试初始化UDS客户端
            if self.init_uds_client():
                self.init_uds_btn.config(text="Close UDS Client")
                self.uds_status_label.config(text="UDS Client: Connected", foreground="green")
            else:
                self.uds_status_label.config(text="UDS Client: Connection Failed", foreground="red")
        else:
            # 关闭UDS客户端
            self.close_uds_connection()
            self.init_uds_btn.config(text="Init UDS Client")
            self.uds_status_label.config(text="UDS Client: Not Connected", foreground="black")

    def perform_ecu_reset(self):
        """执行ECU复位"""
        try:
            if not self.uds_client:
                if self.ensure_trace_handler():
                    self.trace_handler("错误：UDS客户端未连接")
                return False
                
            with self.uds_client as client:
                # 发送硬件复位命令 (reset_type=1 表示硬件复位)
                response = client.ecu_reset(reset_type=1)
                
                if response and self.trace_handler:
                    # 打印完整的响应内容
                    self.trace_handler(f"ECU复位命令已发送，响应内容: {response.data.hex().upper()}")
                return True if response else False
                
        except Exception as e:
            if self.ensure_trace_handler():
                self.trace_handler(f"ECU复位失败: {str(e)}")
            return False

    def start_flashing(self):
        """开始刷写流程"""
        def flash_thread():
            try:
                # 立即禁用按钮（主线程操作）
                self.start_flash_btn.config(state=tk.DISABLED)
                flashing = FlashingProcess(self.uds_client, self.trace_handler)
                success = flashing.execute_flashing_sequence(self.folder_path.get())
                self.update_flash_status(success)
            except Exception as e:
                self.show_flash_error(str(e))
            finally:  
                # 恢复按钮状态（主线程操作）
                self.start_flash_btn.config(state=tk.NORMAL)

        # 直接启动线程
        threading.Thread(target=flash_thread, daemon=True).start()

    def update_flash_status(self, success):
        """更新刷写状态"""
        try:
            if success:
                self.status_label.config(text="刷写完成", foreground="green")
                if self.ensure_trace_handler():
                    self.trace_handler("刷写流程完成")
            else:
                self.status_label.config(text="刷写失败", foreground="red")
        except Exception as e:
            if self.ensure_trace_handler():
                self.trace_handler(f"状态更新异常: {str(e)}")

    def show_flash_error(self, error):
        """显示错误信息"""
        try:
            self.status_label.config(text=f"错误: {error}", foreground="red")
            if self.ensure_trace_handler():
                self.trace_handler(f"刷写错误: {error}")
        except Exception as e:
            if self.ensure_trace_handler():
                self.trace_handler(f"错误处理异常: {str(e)}")

    def get_version(self):
        """获取ECU版本号"""
        try:
            if not self.uds_client:
                if self.ensure_trace_handler():
                    self.trace_handler("错误：UDS客户端未连接")
                return False
                
            with self.uds_client as client:
                # 发送原始22 F0 F0请求
                request = bytes.fromhex('22 77 05')
                client.conn.send(request)
                response = client.conn.wait_frame(timeout=3)
                
                if response and response.hex().upper().startswith('627705'):
                    # 解析完整数据结构：62 77 05 [10字节版本] [12字节日期] [8字节时间]
                    version_data = response[3:13]   # 10字节版本信息
                    date_data = response[13:25]     # 12字节日期数据
                    time_data = response[25:33]     # 8字节时间数据
                    
                    # 转换版本信息
                    version_str = version_data.decode('ascii', errors='ignore').strip()
                    
                    # 转换日期信息（假设为ASCII格式）
                    try:
                        date_str = date_data.decode('ascii', errors='ignore').strip()
                    except:
                        date_str = "日期解析失败"
                        
                    # 转换时间信息（假设为ASCII格式）
                    try:
                        time_str = time_data.decode('ascii', errors='ignore').strip()
                    except:
                        time_str = "时间解析失败"
                    
                    # 更新版本信息标签
                    self.version_label.config(
                        text=f"Ver: {version_str}",
                        foreground="green"
                    )
                    
                    # 记录到tracehandler
                    if self.ensure_trace_handler():
                        log_msg = (
                            f"完整版本信息:\n"
                            f"  版本号: {version_str}\n"
                            f"  日期: {date_str} (原始数据: {date_data.hex().upper()})\n"
                            f"  时间: {time_str} (原始数据: {time_data.hex().upper()})"
                        )
                        self.trace_handler(log_msg)
                    return True
                else:
                    err_msg = f"获取版本号失败，响应: {response.hex().upper() if response else '无响应'}"
                    self.status_label.config(
                        text=err_msg,
                        foreground="red"
                    )
                    if self.ensure_trace_handler():
                        self.trace_handler(err_msg)
                    return False
                    
        except Exception as e:
            err_msg = f"获取版本号异常: {str(e)}"
            self.status_label.config(
                text=err_msg,
                foreground="red"
            )
            if self.ensure_trace_handler():
                self.trace_handler(err_msg)
            return False