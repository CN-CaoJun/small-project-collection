import tkinter as tk
from tkinter import ttk
import sv_ttk
from datetime import datetime

class TracePack:
    def __init__(self, parent):
        """初始化消息追踪模块"""
        self.parent = parent
        self.create_widgets()
        
    def create_widgets(self):
        """创建界面控件"""
        # 创建消息显示区域
        self.msg_display = tk.Text(self.parent, height=10)
        self.msg_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
        
        # 清除按钮
        self.clear_button = ttk.Button(self.parent, text="Clear", command=self.clear_display)
        self.clear_button.pack(side=tk.RIGHT, padx=5, pady=2)
        
    def append_message(self, msg):
        """追加新的CAN消息"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        msg_str = f"[{timestamp}] {str(msg)}\n"
        self.msg_display.insert(tk.END, msg_str)
        self.msg_display.see(tk.END)  # 自动滚动到最新消息
        
    def clear_display(self):
        """清除显示区域的所有消息"""
        self.msg_display.delete(1.0, tk.END)