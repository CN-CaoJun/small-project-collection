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


class BootloaderPack:
    def __init__(self, parent):
        self.parent = parent
        self.create_widgets()
        
    def create_widgets(self):
        # 主框架容器
        self.bootloader_frame = ttk.LabelFrame(self.parent, text="Bootloader")
        self.bootloader_frame.pack(fill=tk.X, padx=5, pady=5, expand=False)

        # 添加文件夹选择控件
        self.folder_selector_frame = ttk.Frame(self.bootloader_frame)
        self.folder_selector_frame.pack(fill=tk.X, padx=5, pady=5)

        # 文件夹选择按钮
        self.select_btn = ttk.Button(
            self.folder_selector_frame,
            text="选择固件目录",
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

    def select_firmware_folder(self):
        """处理文件夹选择"""
        from tkinter import filedialog
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.folder_path.set(folder_selected)
            # 添加文件检查逻辑
            required_files = {'gen6nu.hex', 'gen6nu_sbl.hex', 'gen6nu_sbl_sign.bin', 'gen6nu_sign.bin'}
            existing_files = set(os.listdir(folder_selected))
            missing_files = required_files - existing_files
            
            # 更新状态标签
            if not missing_files:
                self.status_label.config(text="File Check PASS", foreground="green")
            else:
                self.status_label.config(
                    text=f"File Check FAILED\nMissing: {', '.join(missing_files)}",
                    foreground="red"
                )
        