import tkinter as tk
from tkinter import ttk

class DoCANTester(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DoCAN Tester")
        self.geometry("1000x700")
        
        # Create main frame
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Create Connection groupbox
        self.create_connection_groupbox()
    
    def create_connection_groupbox(self):
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
        
        self.hardware_combo = ttk.Combobox(hw_control_frame, values=["PCAN_DNG: 1 (31h)"], width=30)
        self.hardware_combo.pack(side=tk.LEFT, padx=(0, 2))
        self.refresh_button = ttk.Button(hw_control_frame, text="Refresh", width=8)
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

if __name__ == "__main__":
    app = DoCANTester()
    app.mainloop()