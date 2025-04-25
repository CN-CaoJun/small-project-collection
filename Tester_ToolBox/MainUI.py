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


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("Diagnostic ToolBox")
        self.geometry("750x800")

        # 创建主框架
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Connection Pack - CAN连接模块
        self.connection_frame = ttk.LabelFrame(self.main_frame, text="Connection")
        self.connection_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Diagnostic Pack - 诊断模块
        self.diagnostic_frame = ttk.LabelFrame(self.main_frame, text="Diagnostic")
        self.diagnostic_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Bootloader Pack - 刷写模块
        self.bootloader_frame = ttk.LabelFrame(self.main_frame, text="IMS Bootloader")
        self.bootloader_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 添加Trace Pack框架
        self.trace_frame = ttk.LabelFrame(self.main_frame, text="Trace Messages")
        self.trace_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 初始化各个功能模块
        self.init_connection_pack()
        self.init_diagnostic_pack()
        self.init_bootloader_pack()
        self.init_trace_pack()
        
    def get_trace_handler(self):
        """获取消息处理器"""
        return self.trace.append_message if hasattr(self, 'trace') else None

    def init_connection_pack(self):
        from ConnectionPack import ConnectionPack
        self.connection = ConnectionPack(self.connection_frame)
        
    def init_diagnostic_pack(self):
        """初始化诊断模块"""
        from DiagnosticPack import DiagnosticPack
        self.diagnostic = DiagnosticPack(self.diagnostic_frame)
    
    def init_bootloader_pack(self):
        """初始化Bootloader模块"""
        from BootloaderPack import BootloaderPack
        self.bootloader = BootloaderPack(self.bootloader_frame)
        # 传递trace handler
        self.bootloader.trace_handler = self.get_trace_handler()

    def init_trace_pack(self):
        """初始化消息追踪模块"""
        from TracePack import TracePack
        self.trace = TracePack(self.trace_frame)

if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()
