import sys
import os
import logging

sys.path.insert(0, os.path.abspath("reference_modules/python-can"))
sys.path.insert(0, os.path.abspath("reference_modules/python-can-isotp"))

import tkinter as tk
from tkinter import ttk
from can.interfaces.vector import canlib, xlclass, xldefine

class VectorScanner(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Vector Channel Scanner")
        self.geometry("600x400")

        # Create main frame
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Create scan button
        self.scan_button = ttk.Button(self.main_frame, text="Scan Vector Channels", command=self.scan_channels)
        self.scan_button.pack(pady=10)

        # Create treeview for displaying results
        self.tree = ttk.Treeview(self.main_frame, columns=("HW Channel", "Name", "Bus Type", "HW Index"), show="headings")
        self.tree.heading("HW Channel", text="HW Channel")
        self.tree.heading("Name", text="Name")
        self.tree.heading("Bus Type", text="Bus Type")
        self.tree.heading("HW Index", text="HW Index")
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.main_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Add Initialize CAN FD button
        self.init_button = ttk.Button(self.main_frame, text="Initialize as CAN FD", command=self.initialize_canfd)
        self.init_button.pack(pady=10)
        self.init_button.config(state=tk.DISABLED)  # Initially disabled

        # Bind selection event
        self.tree.bind('<<TreeviewSelect>>', self.on_select)

        self.selected_channel = None
        self.bus = None

    def on_select(self, event):
        selected_items = self.tree.selection()
        if selected_items:
            item = selected_items[0]
            values = self.tree.item(item)['values']
            if values:
                self.selected_channel = int(values[0])  # Store channel number
                self.init_button.config(state=tk.NORMAL)  # Enable initialize button
        else:
            self.init_button.config(state=tk.DISABLED)

    def initialize_canfd(self):
        if self.selected_channel is None:
            self.show_error("Please select a channel first")
            return

        try:
            # Close existing bus if any
            if self.bus:
                self.bus.shutdown()

            # Print the selected channel value
            print(f"Selected channel: {self.selected_channel}")
            # Initialize CAN FD bus
            self.bus = canlib.VectorBus(
                channel=self.selected_channel,
                # app_name="CANalyzer",
                fd=False,  # Enable CAN FD
                data_bitrate=2000000,  # 2 Mbps data rate
                bitrate=500000,  # 500 kbps arbitration rate
            )
            
            self.show_success(f"Successfully initialized CAN FD on channel {self.selected_channel}")
        except Exception as e:
            self.show_error(f"Error initializing CAN FD: {str(e)}")

    def scan_channels(self):
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            # Open the XL driver
            if canlib.xldriver is None:
                self.show_error("Vector XL API is not available")
                return

            canlib.xldriver.xlOpenDriver()

            # Get channel configurations
            channel_configs = canlib.get_channel_configs()

            if not channel_configs:
                self.show_error("No Vector channels found")
                return

            # Display channel information
            for config in channel_configs:
                print(f"Detected Channel - HW: {config.hw_channel}, Type: {config.hw_type.name if hasattr(config.hw_type, 'name') else config.hw_type}, Bus: {config.connected_bus_type.name}, Index: {config.hw_index}")
                self.tree.insert("", tk.END, values=(
                    f"{config.hw_channel}",
                    f"{config.name}",
                    f"{config.connected_bus_type.name if config.connected_bus_type else 'N/A'}",
                    f"{config.hw_index}"
                ))

        except Exception as e:
            self.show_error(f"Error scanning channels: {str(e)}")
        finally:
            try:
                canlib.xldriver.xlCloseDriver()
            except:
                pass

    def show_error(self, message):
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        # Show error message in tree
        self.tree.insert("", tk.END, values=(message, "", "", ""))

    def show_success(self, message):
        # Show success message without clearing the channel list
        success_window = tk.Toplevel(self)
        success_window.title("Success")
        success_window.geometry("300x100")
        
        label = ttk.Label(success_window, text=message, wraplength=250)
        label.pack(padx=20, pady=20)
        
        ok_button = ttk.Button(success_window, text="OK", command=success_window.destroy)
        ok_button.pack(pady=10)

if __name__ == "__main__":
    app = VectorScanner()
    app.mainloop()