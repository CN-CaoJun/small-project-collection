import tkinter as tk
from tkinter import ttk
from datetime import datetime

class TracePack:
    def __init__(self, parent):
        """Initialize message tracking module"""
        self.parent = parent
        self.create_widgets()
        
    def create_widgets(self):
        """Create interface widgets"""
        # Create message display area
        self.msg_display = tk.Text(self.parent, height=10)
        self.msg_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
        
        # Clear button
        self.clear_button = ttk.Button(self.parent, text="Clear", command=self.clear_display)
        self.clear_button.pack(side=tk.RIGHT, padx=5, pady=2)
        
    def append_message(self, msg):
        """Append new CAN message"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        # msg could be any type, convert to string for display
        msg_str = f"[{timestamp}] {str(msg)}\n"
        self.msg_display.insert(tk.END, msg_str)
        self.msg_display.see(tk.END)
        
    def clear_display(self):
        """Clear all messages in display area"""
        self.msg_display.delete(1.0, tk.END)