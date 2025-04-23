import tkinter as tk
from tkinter import ttk
from datetime import datetime

class TracePack(ttk.LabelFrame):
    def __init__(self, parent):
        super().__init__(parent, text="Trace Messages")
        self.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.create_widgets()
        
    def create_widgets(self):
        # 创建文本框和滚动条
        self.text = tk.Text(self, wrap=tk.WORD, state='disabled')
        self.scroll = ttk.Scrollbar(self, command=self.text.yview)
        self.text.configure(yscrollcommand=self.scroll.set)
        
        # 创建清除按钮
        self.clear_btn = ttk.Button(self, text="Clear", command=self.clear_messages)
        
        # 布局
        self.clear_btn.pack(side=tk.BOTTOM, anchor=tk.E, padx=5, pady=2)
        self.scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 配置标签样式
        self.text.tag_config('ERROR', foreground='red')
        self.text.tag_config('INFO', foreground='black') 
        self.text.tag_config('SUCCESS', foreground='green')

    def append_message(self, message, level='INFO'):
        """添加带时间戳的消息"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.text.configure(state='normal')
        self.text.insert(tk.END, f"[{timestamp}] {message}\n", (level,))
        self.text.configure(state='disabled')
        self.text.see(tk.END)
        
    def clear_messages(self):
        """清除所有消息"""
        self.text.configure(state='normal')
        self.text.delete(1.0, tk.END)
        self.text.configure(state='disabled')