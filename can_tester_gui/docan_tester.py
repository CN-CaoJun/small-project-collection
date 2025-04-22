import tkinter as tk
from tkinter import ttk
import sv_ttk
import sys
import os

sys.path.insert(0, os.path.abspath("reference_modules/python-can"))
sys.path.insert(0, os.path.abspath("reference_modules/python-can-isotp"))
sys.path.insert(0, os.path.abspath("reference_modules/python-udsoncan"))

from can.interfaces.vector import canlib, xlclass, xldefine

class DoCANTester(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DoCAN Tester")
        self.geometry("1024x768")
        # Apply Sun Valley theme
        # sv_ttk.set_theme("light") 
        # Create main frame
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        self.InitializeWidgets()
    def InitializeWidgets(self):
        self.InitializeConnectionWidgets()
        
    def InitializeConnectionWidgets(self):
        # Create groupbox frame
        connection_frame = ttk.LabelFrame(
            self.main_frame, 
            text="Connection",
            padding=(5, 5)
        )
        connection_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Create a frame to contain all controls
        controls_frame = ttk.Frame(connection_frame)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Hardware section
        hw_frame = ttk.Frame(controls_frame)
        hw_frame.pack(side=tk.LEFT, padx=5)
        ttk.Label(hw_frame, text="Hardware:").pack(anchor=tk.W)
        
        # Create a sub-frame to contain combo and refresh button
        hw_control_frame = ttk.Frame(hw_frame)
        hw_control_frame.pack(anchor=tk.W)
        
        self.hardware_combo = ttk.Combobox(hw_control_frame, values=[" "], width=30)
        self.hardware_combo.pack(side=tk.LEFT, padx=(0, 2))
        self.refresh_button = ttk.Button(hw_control_frame, text="Refresh", width=8, command=self.scan_vector_channels)
        self.refresh_button.pack(side=tk.LEFT)
        
        # Baudrate section
        baud_frame = ttk.Frame(controls_frame)
        baud_frame.pack(side=tk.LEFT, padx=5)
        ttk.Label(baud_frame, text="Baudrate:").pack(anchor=tk.W)
        self.baudrate_combo = ttk.Combobox(baud_frame, values=["500 kBit/sec"], width=12)
        self.baudrate_combo.pack(anchor=tk.W)
        
        # CAN-FD checkbox section
        canfd_frame = ttk.Frame(controls_frame)
        canfd_frame.pack(side=tk.LEFT, padx=5)
        ttk.Label(canfd_frame, text="CAN-FD:").pack(anchor=tk.W)
        self.canfd_var = tk.BooleanVar()
        self.canfd_check = ttk.Checkbutton(canfd_frame, text="CAN-FD", variable=self.canfd_var)
        self.canfd_check.pack(anchor=tk.W)
        
        # Button section
        button_frame = ttk.Frame(controls_frame)
        button_frame.pack(side=tk.LEFT, padx=5)
        ttk.Label(button_frame, text="Operation:").pack(anchor=tk.W)
        self.init_button = ttk.Button(button_frame, text="Initialize", width=8)
        self.init_button.pack(side=tk.LEFT, padx=2)
        self.release_button = ttk.Button(button_frame, text="Release", width=8)
        self.release_button.pack(side=tk.LEFT, padx=2)
    
    def scan_vector_channels(self):
        """扫描Vector通道并填充到下拉列表中"""
        try:
            # Check if XL driver is available
            if canlib.xldriver is None:
                self.show_error("Vector XL API is not available") # Vector XL API不可用
                return
            
            # Open XL driver
            canlib.xldriver.xlOpenDriver()
            
            # Get channel configurations
            channel_configs = canlib.get_channel_configs()
            
            if not channel_configs:
                self.show_error("No Vector channels found") # 未找到Vector通道
                return
            
            # Prepare channel list
            channel_list = []
            
            # Display channel information
            for config in channel_configs:
                channel_name = f"{config.name}"
                channel_list.append(channel_name)
                print(f"Detected Channel - HW: {config.hw_channel}, Type: {config.hw_type.name if hasattr(config.hw_type, 'name') else config.hw_type}, Bus: {config.connected_bus_type.name if hasattr(config.connected_bus_type, 'name') else 'N/A'}, Index: {config.hw_index}") 
            
            # Update dropdown list
            self.hardware_combo['values'] = channel_list
            
            # Select the first channel if available
            if channel_list:
                self.hardware_combo.current(0)
                
        except Exception as e:
            self.show_error(f"Error scanning channels: {str(e)}") # 扫描通道时出错
        finally:
            try:
                # Close XL driver
                canlib.xldriver.xlCloseDriver()
            except:
                pass
    
    def show_error(self, message):
        """显示错误消息"""
        # Create error message window
        error_window = tk.Toplevel(self)
        error_window.title("Error") # 错误
        error_window.geometry("300x100")
        
        label = ttk.Label(error_window, text=message, wraplength=250)
        label.pack(padx=20, pady=20)
        
        ok_button = ttk.Button(error_window, text="OK", command=error_window.destroy) # 确定
        ok_button.pack(pady=10)

if __name__ == "__main__":
    app = DoCANTester()
    app.mainloop()