import tkinter as tk
from tkinter import ttk
import os

class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("Chery ZCU Diagnostic ToolBox V1.0.0.4")
        self.geometry("768x800")
        
        icon_path = os.path.join(os.path.dirname(__file__), 'assets', 'icon.ico')
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)

        # create main frame
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Connection Pack 
        self.connection_frame = ttk.LabelFrame(self.main_frame, text="Connection")
        self.connection_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Diagnostic Pack 
        self.diagnostic_frame = ttk.LabelFrame(self.main_frame, text="Diagnostic")
        self.diagnostic_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Bootloader Pack 
        self.bootloader_frame = ttk.LabelFrame(self.main_frame, text="Chery Bootloader")
        self.bootloader_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Trace Pack
        self.trace_frame = ttk.LabelFrame(self.main_frame, text="Trace Messages")
        self.trace_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # init all modules
        self.init_connection_pack()
        # self.init_diagnostic_pack()
        self.init_bootloader_pack()
        self.init_trace_pack()
        
    def get_trace_handler(self):
        """get trace handler"""
        return self.trace.append_message if hasattr(self, 'trace') else None

    def init_connection_pack(self):
        """init connection pack"""
        from ConnectionPack import ConnectionPack
        self.connection = ConnectionPack(self.connection_frame)
        
    def init_diagnostic_pack(self):
        """init diagnostic pack"""
        from DiagnosticPack import DiagnosticPack
        self.diagnostic = DiagnosticPack(self.diagnostic_frame)
    
    def init_bootloader_pack(self):
        """init bootloader pack"""
        from BootloaderPack import BootloaderPack
        self.bootloader = BootloaderPack(self.bootloader_frame)
        # pass trace handler
        self.bootloader.trace_handler = self.get_trace_handler()

    def init_trace_pack(self):
        """init trace pack"""
        from TracePack import TracePack
        self.trace = TracePack(self.trace_frame)

if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()
