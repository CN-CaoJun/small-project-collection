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
        
        self.title("ECU Tester ToolBox")
        self.geometry("800x600")
        
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
        self.bootloader_frame = ttk.LabelFrame(self.main_frame, text="Bootloader")
        self.bootloader_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 初始化各个功能模块
        self.init_connection_pack()
        self.init_diagnostic_pack()
        # self.init_bootloader_pack()
    
    def init_connection_pack(self):
        from ConnectionPack import ConnectionPack
        self.connection = ConnectionPack(self.connection_frame)
        
        # 获取CAN总线对象的方法
        def get_bus(self):
            if self.connection:
                return self.connection.get_can_bus()
            return None
    
    def init_diagnostic_pack(self):
        """初始化诊断模块"""
        from DiagnosticPack import DiagnosticPack
        self.diagnostic = DiagnosticPack(self.diagnostic_frame)
    
    def init_bootloader_pack(self):
        """初始化Bootloader模块"""
        from BootloaderPack import BootloaderPack
        self.bootloader = BootloaderPack(self.bootloader_frame)

if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()
