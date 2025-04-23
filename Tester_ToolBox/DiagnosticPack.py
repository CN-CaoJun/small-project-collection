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
        

        
        # 消息发送框架
        self.msg_frame = ttk.LabelFrame(self.parent, text="Diag Request")
        self.msg_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 创建一个框架来容纳输入框和按钮
        self.input_container = ttk.Frame(self.msg_frame)
        self.input_container.pack(fill=tk.X, padx=5, pady=2)
        
        # 消息输入框
        self.msg_input = ttk.Entry(self.input_container)
        self.msg_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        # 发送按钮
        self.send_button = ttk.Button(self.input_container, text="Send", command=self.send_message)
        self.send_button.pack(side=tk.LEFT)
        
        # 消息显示框
        self.msg_display = tk.Text(self.msg_frame, height=10)
        self.msg_display.pack(fill=tk.BOTH, padx=5, pady=2)
        
    def send_message(self):
        try:
            # 获取主窗口的CAN总线对象
            main_window = self.parent.winfo_toplevel()
            can_bus = main_window.connection.get_can_bus()
            
            if not can_bus:
                self.msg_display.insert(tk.END, "错误：CAN总线未初始化\n")
                return
                
            # 获取TP层参数
            stmin = int(self.stmin_entry.get())
            blocksize = int(self.block_entry.get())
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
            
            # 创建ISO-TP栈
            stack = isotp.NotifierBasedCanStack(
                bus=can_bus,
                address=tp_addr,
                params=tp_params
            )
            
            # 获取要发送的消息
            message = self.msg_input.get()
            if not message:
                self.msg_display.insert(tk.END, "错误：请输入要发送的消息\n")
                return
                
            # 发送消息
            stack.send(message.encode())
            
            # 显示发送信息
            self.msg_display.insert(tk.END, f"发送消息：{message}\n")
            self.msg_display.insert(tk.END, f"TXID: 0x{txid:03X}, RXID: 0x{rxid:03X}\n")
            self.msg_display.see(tk.END)
            
        except Exception as e:
            self.msg_display.insert(tk.END, f"错误：{str(e)}\n")
            self.msg_display.see(tk.END)