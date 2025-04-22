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

class DoCANTester(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("IMS Tester ")
        self.geometry("1280x768")
        sv_ttk.set_theme("light") 
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Add CAN bus object property
        self.can_bus = None
        # Store channel configuration information
        self.channel_configs = {}
        
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
        
        self.hardware_combo = ttk.Combobox(hw_control_frame, values=[" "], width=16)
        self.hardware_combo.pack(side=tk.LEFT, padx=(0, 2))
        self.refresh_button = ttk.Button(hw_control_frame, text="Refresh", width=8, command=self.scan_vector_channels)
        self.refresh_button.pack(side=tk.LEFT)
        
        # Baudrate section
        baud_frame = ttk.Frame(controls_frame)
        baud_frame.pack(side=tk.LEFT, padx=5)
        ttk.Label(baud_frame, text="Baudrate Parameters:").pack(anchor=tk.W)
        
        # Use Entry widget instead of Combobox
        self.default_can_params = "fd=False,bitrate=500000,tseg1_abr=63,tseg2_abr=16,sjw_abr=16"
        self.default_canfd_params = "fd=True,bitrate=500000,data_bitrate=2000000,tseg1_abr=63,tseg2_abr=16,sjw_abr=16,sam_abr=1,tseg1_dbr=13,tseg2_dbr=6,sjw_dbr=6"
        
        self.baudrate_entry = ttk.Entry(baud_frame, width=50)
        self.baudrate_entry.insert(0, self.default_can_params)
        self.baudrate_entry.pack(anchor=tk.W)
        
        # CAN-FD checkbox section
        canfd_frame = ttk.Frame(controls_frame)
        canfd_frame.pack(side=tk.LEFT, padx=5)
        ttk.Label(canfd_frame, text="CAN-FD:").pack(anchor=tk.W)
        self.canfd_var = tk.BooleanVar()
        self.canfd_check = ttk.Checkbutton(canfd_frame, text="CAN-FD", variable=self.canfd_var, command=self.on_canfd_changed)
        self.canfd_check.pack(anchor=tk.W)
        
        # Button section
        button_frame = ttk.Frame(controls_frame)
        button_frame.pack(side=tk.LEFT, padx=5)
        ttk.Label(button_frame, text="Operation:").pack(anchor=tk.W)
        self.init_button = ttk.Button(button_frame, text="Initialize", width=8, command=self.initialize_can)
        self.init_button.pack(side=tk.LEFT, padx=2)
        self.release_button = ttk.Button(button_frame, text="Release", width=8, command=self.release_can)
        self.release_button.pack(side=tk.LEFT, padx=2)
    
    def scan_vector_channels(self):
        try:
            # Check if XL driver is available
            if canlib.xldriver is None:
                self.show_error("Vector XL API is not available") 
                return
            
            # Open XL driver
            canlib.xldriver.xlOpenDriver()
            
            # Get channel configurations
            channel_configs = canlib.get_channel_configs()
            
            if not channel_configs:
                self.show_error("No Vector channels found") 
                return
            
            # Prepare channel list
            channel_list = []
            # Clear old configuration information
            self.channel_configs.clear()  
            
            # Display channel information
            for config in channel_configs:
                channel_name = f"{config.name}"
                channel_list.append(channel_name)
                # Store configuration information
                self.channel_configs[channel_name] = config
                print(f"Detected Channel - HW: {config.hw_channel}, Type: {config.hw_type.name if hasattr(config.hw_type, 'name') else config.hw_type}, Bus: {config.connected_bus_type.name if hasattr(config.connected_bus_type, 'name') else 'N/A'}, Index: {config.hw_index}") 
            
            # Update dropdown list
            self.hardware_combo['values'] = channel_list
            
            # Select the first channel if available
            if channel_list:
                self.hardware_combo.current(0)
                
        except Exception as e:
            self.show_error(f"Error scanning channels: {str(e)}") 
        finally:
            try:
                # Close XL driver
                canlib.xldriver.xlCloseDriver()
            except:
                pass
    
    def show_error(self, message):
        # Create error message window
        error_window = tk.Toplevel(self)
        error_window.title("Error") 
        error_window.geometry("300x100")
        
        label = ttk.Label(error_window, text=message, wraplength=250)
        label.pack(padx=20, pady=20)
        
        ok_button = ttk.Button(error_window, text="OK", command=error_window.destroy) 
        ok_button.pack(pady=10)

    def parse_baudrate_parameters(self):
        params = {}
        try:
            # Split parameter string and convert to dictionary
            param_str = self.baudrate_entry.get()
            param_pairs = param_str.split(',')
            for pair in param_pairs:
                key, value = pair.split('=')
                key = key.strip()
                value = value.strip()
                
                # Handle boolean values
                if value.lower() == 'true':
                    params[key] = True
                elif value.lower() == 'false':
                    params[key] = False
                else:
                    # Handle numeric values
                    try:
                        params[key] = int(value)
                    except ValueError:
                        # Keep original string if cannot convert to integer
                        params[key] = value
            
            # Print all parameters
            print("CAN Parameter Configuration:")
            for key, value in params.items():
                print(f"  {key}: {value} ({type(value).__name__})")
                
            return params
        except Exception as e:
            self.show_error(f"Parameter format error: {str(e)}")
            return None

    def on_canfd_changed(self):
        """Handle CAN-FD checkbox state change"""
        # Clear current Entry content
        self.baudrate_entry.delete(0, tk.END)
        
        # Set parameters based on checkbox state
        if self.canfd_var.get():
            self.baudrate_entry.insert(0, self.default_canfd_params)
        else:
            self.baudrate_entry.insert(0, self.default_can_params)

    def initialize_can(self):
        """Initialize CAN channel"""
        try:
            # Check if channel is selected
            selected_channel = self.hardware_combo.get()
            if not selected_channel:
                self.show_error("Please select a CAN channel first")
                return
            
            # Get selected channel configuration
            if selected_channel not in self.channel_configs:
                self.show_error("Cannot find configuration for selected channel")
                return
                
            channel_config = self.channel_configs[selected_channel]
            
            # Get baudrate parameters
            params = self.parse_baudrate_parameters()
            if not params:
                return
            
            print(f"Selected channel: {selected_channel}")
            print(f"Channel ID: {channel_config.hw_channel}")
            
            if self.can_bus:
                self.can_bus.shutdown()
                
            self.can_bus = canlib.VectorBus(
                channel=channel_config.hw_channel,  # Use hardware channel number
                **params
            )
            
            self.init_button.configure(state='disabled')
            self.release_button.configure(state='normal')
            
            print(f"CAN channel initialized successfully: {selected_channel} (ID: {channel_config.hw_channel})")
            
        except Exception as e:
            self.show_error(f"Failed to initialize CAN channel: {str(e)}")
            
    def release_can(self):
        """Release CAN channel"""
        try:
            if self.can_bus:
                self.can_bus.shutdown()
                self.can_bus = None
                
            # Enable initialize button, disable release button
            self.init_button.configure(state='normal')
            self.release_button.configure(state='disabled')
            
            print("CAN channel released")
            
        except Exception as e:
            self.show_error(f"Failed to release CAN channel: {str(e)}")

if __name__ == "__main__":
    app = DoCANTester()
    app.mainloop()