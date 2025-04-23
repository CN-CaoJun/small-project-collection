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

class DiagnosticPack:
    def __init__(self, parent):
        self.parent = parent
        self.receive_active = False  # 控制接收线程的标志
        self.receive_thread = None   # 接收线程对象
        self.create_widgets()
        
    def create_widgets(self):
        # TP层参数设置框架
        self.tp_params_frame = ttk.LabelFrame(self.parent, text="ISO-TP Parameters")
        self.tp_params_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 创建一个框架来容纳所有参数设置
        self.params_container = ttk.Frame(self.tp_params_frame)
        self.params_container.pack(fill=tk.X, padx=5, pady=2)
        
        # TXID设置
        self.txid_frame = ttk.Frame(self.params_container)
        self.txid_frame.pack(side=tk.LEFT)
        ttk.Label(self.txid_frame, text="TXID:").pack(anchor=tk.W)  # 使用anchor=tk.W实现左对齐
        self.txid_entry = ttk.Entry(self.txid_frame, width=8)
        self.txid_entry.insert(0, "0x749")
        self.txid_entry.pack()
        
        ttk.Frame(self.params_container, width=10).pack(side=tk.LEFT)
        
        # RXID设置
        self.rxid_frame = ttk.Frame(self.params_container)
        self.rxid_frame.pack(side=tk.LEFT)
        ttk.Label(self.rxid_frame, text="RXID:").pack(anchor=tk.W)  # 使用anchor=tk.W实现左对齐
        self.rxid_entry = ttk.Entry(self.rxid_frame, width=8)
        self.rxid_entry.insert(0, "0x759")
        self.rxid_entry.pack()
        
        ttk.Frame(self.params_container, width=10).pack(side=tk.LEFT)
        
        # STMIN设置
        self.stmin_frame = ttk.Frame(self.params_container)
        self.stmin_frame.pack(side=tk.LEFT)
        ttk.Label(self.stmin_frame, text="stmin:").pack(anchor=tk.W)  # 使用anchor=tk.W实现左对齐
        self.stmin_entry = ttk.Entry(self.stmin_frame, width=8)
        self.stmin_entry.insert(0, "0x04")
        self.stmin_entry.pack()
        
        # 添加10像素间隔
        ttk.Frame(self.params_container, width=10).pack(side=tk.LEFT)
        
        # BLOCKSIZE设置
        self.block_frame = ttk.Frame(self.params_container)
        self.block_frame.pack(side=tk.LEFT)
        ttk.Label(self.block_frame, text="blocksize:").pack(anchor=tk.W)  # 使用anchor=tk.W实现左对齐
        self.block_entry = ttk.Entry(self.block_frame, width=8)
        self.block_entry.insert(0, "0x08")
        self.block_entry.pack()
        
        # 添加10像素间隔
        ttk.Frame(self.params_container, width=10).pack(side=tk.LEFT)
        
        # PADDING设置
        self.padding_frame = ttk.Frame(self.params_container)
        self.padding_frame.pack(side=tk.LEFT)
        ttk.Label(self.padding_frame, text="padding:").pack(anchor=tk.W)  # 使用anchor=tk.W实现左对齐
        self.padding_entry = ttk.Entry(self.padding_frame, width=8)
        self.padding_entry.insert(0, "0x00")
        self.padding_entry.pack()
        
        # 添加10像素间隔
        ttk.Frame(self.params_container, width=5).pack(side=tk.LEFT)

        # 添加Operation标签和按钮的框架
        self.operation_frame = ttk.Frame(self.params_container)
        self.operation_frame.pack(side=tk.LEFT)
        
        ttk.Label(self.operation_frame, text="  ").pack(anchor=tk.W)
        
        # Enable Diag按钮
        self.enable_button = ttk.Checkbutton(
            self.operation_frame,  # 改为新的框架容器
            text="Enable Diag",
            style="Toggle.TButton",
            command=self.on_enable_diag
        )
        self.enable_button.pack(padx=(5,0))  # 调整间距

        
        # 消息发送框架
        self.msg_frame = ttk.LabelFrame(self.parent, text="Diag Request")
        self.msg_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 创建一个框架来容纳输入框和按钮
        self.input_container = ttk.Frame(self.msg_frame)
        self.input_container.pack(fill=tk.X, padx=5, pady=2)
        
        # 消息输入框
        self.msg_input = ttk.Entry(self.input_container, validate="key", 
                                 validatecommand=(self.parent.register(self.on_hex_input), '%P'))
        self.msg_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        ttk.Label(self.input_container, text="(Hex: 11 22 33)").pack(side=tk.LEFT)
        # 添加保持会话按钮
        self.keep_alive_button = ttk.Checkbutton(
            self.input_container,
            text="Keep Alive: OFF",
            style="Toggle.TButton",
            command=self.on_keep_alive
        )
        self.keep_alive_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # 发送按钮
        self.send_button = ttk.Button(self.input_container, text="Send", command=self.send_message)
        self.send_button.pack(side=tk.LEFT)
        self.send_button.configure(state='disabled')  # 初始状态设为禁用
        
        # 消息显示框
        self.msg_display = tk.Text(self.msg_frame, height=10)
        self.msg_display.pack(fill=tk.BOTH, padx=5, pady=2)
        
        # 添加ISO-TP栈属性
        self.tp_stack = None
        
    def on_enable_diag(self):
        """处理Enable Diag按钮的状态变化"""
        if self.enable_button.instate(['selected']):
            # 禁用所有参数输入控件
            for child in self.params_container.winfo_children():
                if isinstance(child, (ttk.Entry, ttk.Frame)):
                    for widget in child.winfo_children():
                        if isinstance(widget, ttk.Entry):
                            widget.configure(state='disabled')
            self.initialize_tp_layer()
            if not self.tp_stack:
                self.enable_button.state(['!selected'])
            else:
                self.send_button.configure(state='normal')
        else:
            # 启用所有参数输入控件
            for child in self.params_container.winfo_children():
                if isinstance(child, (ttk.Entry, ttk.Frame)):
                    for widget in child.winfo_children():
                        if isinstance(widget, ttk.Entry):
                            widget.configure(state='normal')
            self.release_tp_layer()
            self.send_button.configure(state='disabled')
            
    def initialize_tp_layer(self):
        """初始化ISO-TP层"""
        try:
            # 获取主窗口的CAN总线对象
            main_window = self.parent.winfo_toplevel()
            can_bus = main_window.connection.get_can_bus()
            
            if not can_bus:
                self.msg_display.insert(tk.END, "ERROR：CAN总线未初始化\n")
                return
                
            # 获取TP层参数
            stmin = int(self.stmin_entry.get(), 16)
            blocksize = int(self.block_entry.get(), 16)
            padding = int(self.padding_entry.get(), 16)
            
            # 获取ID
            txid = int(self.txid_entry.get(), 16)
            rxid = int(self.rxid_entry.get(), 16)
            
            # 创建ISO-TP地址
            tp_addr = isotp.Address(isotp.AddressingMode.Normal_11bits, txid=txid, rxid=rxid)
            
            # 创建ISO-TP参数
            tp_params = {
                'stmin': stmin,
                'blocksize': blocksize,
                'tx_padding': padding,
                'rx_flowcontrol_timeout': 1000,
                'rx_consecutive_frame_timeout': 1000
            }
            
            # 创建 notifier
            self.notifier = can.Notifier(can_bus, [])
            
            # 创建ISO-TP栈
            self.tp_stack = isotp.NotifierBasedCanStack(
                bus=can_bus,
                notifier=self.notifier,
                address=tp_addr,
                params=tp_params
            )
            
            # 启动 ISO-TP 栈
            self.tp_stack.start()
            
            # 启用发送按钮
            self.send_button.configure(state='normal')
            
            # 创建接收线程
            self.receive_active = True
            self.receive_thread = threading.Thread(target=self.receive_loop, daemon=True)
            self.receive_thread.start()
            
            self.msg_display.insert(tk.END, f"ISO-TP Layer init success -- ")
            self.msg_display.insert(tk.END, f"Request ID: 0x{txid:03X}, Response ID: 0x{rxid:03X}\n")
            self.msg_display.see(tk.END)
            
        except Exception as e:
            self.msg_display.insert(tk.END, f"ERROR：{str(e)}\n")
            self.msg_display.see(tk.END)
            
    def release_tp_layer(self):
        """释放ISO-TP层"""
        # 首先停止接收线程
        self.receive_active = False
        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_thread.join(timeout=1.0)  # 等待接收线程结束
        
        if self.tp_stack:
            self.tp_stack.stop()  # 停止 ISO-TP 栈
            self.tp_stack = None
            
            if hasattr(self, 'notifier'):
                self.notifier.stop()  # 停止 notifier
                self.notifier = None
                
            self.msg_display.insert(tk.END, "ISO-TP Layer released\n")
            self.msg_display.see(tk.END)
            
    def send_message(self):
        """发送诊断消息"""
        try:
            if not self.tp_stack:
                self.msg_display.insert(tk.END, "ERROR：ISO-TP Layer no init\n")
                return
                
            # 获取并解析十六进制数据
            hex_str = self.msg_input.get().replace(" ", "")
            if not hex_str:
                self.msg_display.insert(tk.END, "ERROR：请输入十六进制数据\n")
                return
                
            # 自动补零处理奇数长度
            if len(hex_str) % 2 != 0:
                last_nibble = hex_str[-1]  # 获取最后半字节
                hex_str = hex_str[:-1] + f"{int(last_nibble, 16):02X}"  # 高位补零
                # self.msg_display.insert(tk.END, f"注意：已补高位零 → {' '.join(hex_str[i:i+2] for i in range(0, len(hex_str), 2))}\n")
                
            try:
                data = bytes.fromhex(hex_str)
            except ValueError as e:
                self.msg_display.insert(tk.END, f"ERROR：无效的十六进制数据 - {str(e)}\n")
                return
                
            # 发送消息
            self.tp_stack.send(data)
            
            # 显示发送信息（添加时间戳）
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            self.msg_display.insert(tk.END, f"[{timestamp}] Req: {hex_str.upper()}\n")
            self.msg_display.see(tk.END)
            
        except Exception as e:
            self.msg_display.insert(tk.END, f"ERROR：{str(e)}\n")
            self.msg_display.see(tk.END)
    def receive_loop(self):
        """后台接收线程循环"""
        while self.receive_active and self.tp_stack:
            try:
                response = self.tp_stack.recv(timeout=0.01)
                if response:
                    # 传递原始数据和当前时间戳到主线程
                    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    self.parent.after(0, self.update_display, response, timestamp)
            except Exception as e:
                if self.receive_active:
                    error_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    self.parent.after(0, self.show_error, 
                                    f"[{error_time}] Recv ERROR：{str(e)}")

    def update_display(self, data, timestamp):
        """更新显示内容（主线程执行）"""
        try:
            hex_str = ' '.join(f"{b:02X}" for b in data)
            self.msg_display.insert(tk.END, f"[{timestamp}] Res: {hex_str}\n")
            self.msg_display.see(tk.END)
        except Exception as e:
            self.show_error(f"Display ERROR：{str(e)}")
            
    def show_error(self, error_msg):
        """显示ERROR信息"""
        self.msg_display.insert(tk.END, f"{error_msg}\n")
        self.msg_display.see(tk.END)

    def on_hex_input(self, new_value):
        """处理十六进制输入格式化"""
        # 过滤非法字符
        filtered = ''.join([c for c in new_value.upper() if c in '0123456789ABCDEF '])
        # 格式化添加空格
        clean_str = filtered.replace(' ', '')
        formatted = ' '.join(clean_str[i:i+2] for i in range(0, len(clean_str), 2))
        # 更新输入框
        self.msg_input.delete(0, tk.END)
        self.msg_input.insert(0, formatted.strip())
        return False  # 阻止默认处理
    def format_hex_input(self, event):
        """处理键盘释放事件后的格式化"""
        content = self.msg_input.get().replace(" ", "")
        # 移除非十六进制字符
        content = ''.join(c for c in content if c in '0123456789ABCDEF')
        # 每两个字符添加一个空格
        formatted = ' '.join(content[i:i+2] for i in range(0, len(content), 2))
        # 更新Entry的内容
        self.msg_input.delete(0, tk.END)
        self.msg_input.insert(0, formatted)
        self.msg_input.bind('<KeyRelease>', self.format_hex_input)  # 添加KeyRelease事件绑定

    def on_keep_alive(self):
        """处理保持会话按钮状态变化"""
        if self.keep_alive_button.instate(['selected']):
            self.keep_alive_active = True
            self.keep_alive_button.configure(text="3E00: ON")
            self.start_keep_alive()
        else:
            self.stop_keep_alive()
            self.keep_alive_button.configure(text="3E00: OFF")

    def start_keep_alive(self):
        """启动保持会话线程"""
        self.keep_alive_thread = threading.Thread(target=self.send_keep_alive, daemon=True)
        self.keep_alive_thread.start()

    def stop_keep_alive(self):
        """停止保持会话"""
        self.keep_alive_active = False
        if self.keep_alive_thread and self.keep_alive_thread.is_alive():
            self.keep_alive_thread.join(timeout=1.0)

    def send_keep_alive(self):
        """定时发送3E00"""
        while self.keep_alive_active and self.tp_stack:
            try:
                data = bytes.fromhex("3E00")
                self.tp_stack.send(data)
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                self.msg_display.insert(tk.END, f"[{timestamp}] Keep Alive: 3E 00\n")
                self.msg_display.see(tk.END)
            except Exception as e:
                self.msg_display.insert(tk.END, f"Keep Alive Error: {str(e)}\n")
                self.msg_display.see(tk.END)
            time.sleep(3)