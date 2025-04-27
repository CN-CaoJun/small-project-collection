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

class DiagnosticPack:
    def __init__(self, parent):
        self.parent = parent
        self.receive_active = False  # Flag to control receive thread
        self.receive_thread = None   # Receive thread object
        self.trace_handler = self.parent.winfo_toplevel().get_trace_handler()
        self.create_widgets()
        
    def create_widgets(self):
        # ISO-TP Parameters frame
        self.tp_params_frame = ttk.LabelFrame(self.parent, text="ISO-TP Parameters")
        self.tp_params_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Create a frame to contain all parameter settings
        self.params_container = ttk.Frame(self.tp_params_frame)
        self.params_container.pack(fill=tk.X, padx=5, pady=2)
        
        # TXID settings
        self.txid_frame = ttk.Frame(self.params_container)
        self.txid_frame.pack(side=tk.LEFT)
        ttk.Label(self.txid_frame, text="TXID:").pack(anchor=tk.W)  # Use anchor=tk.W for left alignment
        self.txid_entry = ttk.Entry(self.txid_frame, width=8)
        self.txid_entry.insert(0, "0x749")
        self.txid_entry.pack()
        
        # Add 10 pixel spacing
        ttk.Frame(self.params_container, width=10).pack(side=tk.LEFT)
        
        # RXID settings
        self.rxid_frame = ttk.Frame(self.params_container)
        self.rxid_frame.pack(side=tk.LEFT)
        ttk.Label(self.rxid_frame, text="RXID:").pack(anchor=tk.W)  # Use anchor=tk.W for left alignment
        self.rxid_entry = ttk.Entry(self.rxid_frame, width=8)
        self.rxid_entry.insert(0, "0x759")
        self.rxid_entry.pack()
        
        ttk.Frame(self.params_container, width=10).pack(side=tk.LEFT)
        
        # STMIN settings
        self.stmin_frame = ttk.Frame(self.params_container)
        self.stmin_frame.pack(side=tk.LEFT)
        ttk.Label(self.stmin_frame, text="stmin:").pack(anchor=tk.W)  # Use anchor=tk.W for left alignment
        self.stmin_entry = ttk.Entry(self.stmin_frame, width=8)
        self.stmin_entry.insert(0, "0x04")
        self.stmin_entry.pack()
        
        # Add 10 pixel spacing
        ttk.Frame(self.params_container, width=10).pack(side=tk.LEFT)
        
        # BLOCKSIZE settings
        self.block_frame = ttk.Frame(self.params_container)
        self.block_frame.pack(side=tk.LEFT)
        ttk.Label(self.block_frame, text="blocksize:").pack(anchor=tk.W)  # Use anchor=tk.W for left alignment
        self.block_entry = ttk.Entry(self.block_frame, width=8)
        self.block_entry.insert(0, "0x08")
        self.block_entry.pack()
        
        # Add 10 pixel spacing
        ttk.Frame(self.params_container, width=10).pack(side=tk.LEFT)
        
        # PADDING settings
        self.padding_frame = ttk.Frame(self.params_container)
        self.padding_frame.pack(side=tk.LEFT)
        ttk.Label(self.padding_frame, text="padding:").pack(anchor=tk.W)  # Use anchor=tk.W for left alignment
        self.padding_entry = ttk.Entry(self.padding_frame, width=8)
        self.padding_entry.insert(0, "0x00")
        self.padding_entry.pack()
        
        # Add 10 pixel spacing
        ttk.Frame(self.params_container, width=5).pack(side=tk.LEFT)

        # Add Operation tag and button frame
        self.operation_frame = ttk.Frame(self.params_container)
        self.operation_frame.pack(side=tk.LEFT)
        
        ttk.Label(self.operation_frame, text="  ").pack(anchor=tk.W)
        
        # Enable Diag button
        self.enable_button = ttk.Checkbutton(
            self.operation_frame,  # Change to new frame container
            text="Enable Diag",
            style="Toggle.TButton",
            command=self.on_enable_diag
        )
        self.enable_button.pack(padx=(5,0))  # Adjust spacing

        
        # Message sending frame
        self.msg_frame = ttk.LabelFrame(self.parent, text="Diag Request")
        self.msg_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Create a frame to contain input box and button
        self.input_container = ttk.Frame(self.msg_frame)
        self.input_container.pack(fill=tk.X, padx=5, pady=2)
        
        # Message input box
        self.msg_input = ttk.Entry(self.input_container, validate="key", 
                                 validatecommand=(self.parent.register(self.on_hex_input), '%P'))
        self.msg_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        # 添加回车键绑定
        self.msg_input.bind('<Return>', lambda event: self.send_message())
        
        ttk.Label(self.input_container, text="(Hex: 11 22 33)").pack(side=tk.LEFT)
        # Add keep alive button
        self.keep_alive_button = ttk.Checkbutton(
            self.input_container,
            text="Keep Alive: OFF",
            style="Toggle.TButton",
            command=self.on_keep_alive
        )
        self.keep_alive_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # Send button
        self.send_button = ttk.Button(self.input_container, text="Send", command=self.send_message)
        self.send_button.pack(side=tk.LEFT)
        self.send_button.configure(state='disabled')  # Initial state set to disabled
        
        # Message display box
        # Comment or delete message display box creation code
        # self.msg_display = tk.Text(self.msg_frame, height=10)
        # self.msg_display.pack(fill=tk.BOTH, padx=5, pady=2)
        
        # Add ISO-TP stack property
        self.tp_stack = None
        
    def on_enable_diag(self):
        """Handle Enable Diag button state change"""
        if self.enable_button.instate(['selected']):
            # Disable all parameter input controls
            for child in self.params_container.winfo_children():
                if isinstance(child, (ttk.Entry, ttk.Frame)):
                    for widget in child.winfo_children():
                        if isinstance(widget, ttk.Entry):
                            widget.configure(state='disabled')
            self.initialize_tp_layer()
            if not self.tp_stack:
                self.enable_button.state(['!selected'])
            else:
                self.send_button.configure(state='normal')
        else:
            # Enable all parameter input controls
            for child in self.params_container.winfo_children():
                if isinstance(child, (ttk.Entry, ttk.Frame)):
                    for widget in child.winfo_children():
                        if isinstance(widget, ttk.Entry):
                            widget.configure(state='normal')
            self.release_tp_layer()
            self.send_button.configure(state='disabled')
            
    def initialize_tp_layer(self):
        """Initialize ISO-TP layer"""
        try:
            # Get CAN bus object from main window
            main_window = self.parent.winfo_toplevel()
            can_bus, is_fd = main_window.connection.get_can_bus()
            
            if not can_bus:
                if self.ensure_trace_handler():
                    self.trace_handler("ERROR: CAN bus not initialized")
                return
                
            # Get TP layer parameters
            stmin = int(self.stmin_entry.get(), 16)
            blocksize = int(self.block_entry.get(), 16)
            padding = int(self.padding_entry.get(), 16)
            
            # Get IDs
            txid = int(self.txid_entry.get(), 16)
            rxid = int(self.rxid_entry.get(), 16)
            
            # Create ISO-TP address
            tp_addr = isotp.Address(isotp.AddressingMode.Normal_11bits, txid=txid, rxid=rxid)
            
            # Create ISO-TP parameters based on CAN type
            if is_fd:
                tp_params = {
                    'stmin': stmin,
                    'blocksize': blocksize,
                    'tx_padding': padding,
                    'override_receiver_stmin': None,
                    'wftmax': 4,
                    'tx_data_length': 64,
                    'tx_data_min_length':8,
                    'rx_flowcontrol_timeout': 1000,
                    'rx_consecutive_frame_timeout': 100,
                    'can_fd': True,
                    'max_frame_size': 4095,
                    'bitrate_switch': False,
                    'rate_limit_enable': False,
                    'listen_mode': False,
                    'blocking_send': False
                }
                if self.ensure_trace_handler():
                    self.trace_handler("Using CAN-FD ISO-TP parameters")
            else:
                tp_params = {
                    'stmin': stmin,
                    'blocksize': blocksize,
                    'tx_padding': padding,
                    'override_receiver_stmin': None,
                    'wftmax': 4,
                    'tx_data_length': 8,
                    'tx_data_min_length':8,
                    'rx_flowcontrol_timeout': 1000,
                    'rx_consecutive_frame_timeout': 100,
                    'can_fd': False,
                    'max_frame_size': 4095,
                    'bitrate_switch': False,
                    'rate_limit_enable': False,
                    'listen_mode': False,
                    'blocking_send': False  
                }
                if self.ensure_trace_handler():
                    self.trace_handler("Using Standard CAN ISO-TP parameters")
            
            # Create notifier
            self.notifier = can.Notifier(can_bus, [])
            # Create ISO-TP stack
            self.tp_stack = isotp.NotifierBasedCanStack(
                bus=can_bus,
                notifier=self.notifier,
                address=tp_addr,
                params=tp_params
            )
            # Start ISO-TP stack
            self.tp_stack.start()
            # Enable send button
            self.send_button.configure(state='normal')
            # Create receive thread
            self.receive_active = True
            self.receive_thread = threading.Thread(target=self.receive_loop, daemon=True)
            self.receive_thread.start()
            
            if self.ensure_trace_handler():
                self.trace_handler(f"ISO-TP Layer init success -- Request ID: 0x{txid:03X}, Response ID: 0x{rxid:03X}")
            
        except Exception as e:
            if self.ensure_trace_handler():
                self.trace_handler(f"ERROR: {str(e)}")

    def release_tp_layer(self):
        """Release ISO-TP layer"""
        # First stop receive thread
        self.receive_active = False
        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_thread.join(timeout=1.0)  # Wait for receive thread to end
        
        if self.tp_stack:
            self.tp_stack.stop()  # Stop ISO-TP stack
            self.tp_stack = None
            
            if hasattr(self, 'notifier'):
                self.notifier.stop()  # Stop notifier
                self.notifier = None
                
            if self.ensure_trace_handler():
                self.trace_handler("ISO-TP Layer released")
            
    def send_message(self):
        """Send diagnostic message"""
        try:
            if not self.tp_stack:
                if self.ensure_trace_handler():
                    self.trace_handler("ERROR: ISO-TP Layer not initialized")
                return
                
            # Get and parse hex data
            hex_str = self.msg_input.get().replace(" ", "")
            if not hex_str:
                if self.ensure_trace_handler():
                    self.trace_handler("ERROR: Please input hex data")
                return
                
            # Auto pad zero for odd length
            if len(hex_str) % 2 != 0:
                last_nibble = hex_str[-1]  # Get last half byte
                hex_str = hex_str[:-1] + f"{int(last_nibble, 16):02X}"  # Pad high nibble with zero
                
            try:
                data = bytes.fromhex(hex_str)
            except ValueError as e:
                if self.ensure_trace_handler():
                    self.trace_handler(f"ERROR: Invalid hex data - {str(e)}")
                return
                
            # Send message
            self.tp_stack.send(data)
            
            # Display send info (with timestamp)
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            
            if self.ensure_trace_handler():
                self.trace_handler(f"TX: {hex_str.upper()}")
            
        except Exception as e:
            if self.ensure_trace_handler():
                self.trace_handler(f"ERROR: {str(e)}")

    def receive_loop(self):
        """Background receive thread loop"""
        while self.receive_active and self.tp_stack:
            try:
                response = self.tp_stack.recv(timeout=0.01)
                if response:
                    # Pass raw data and current timestamp to main thread
                    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    self.parent.after(0, self.update_display, response, timestamp)
            except Exception as e:
                if self.receive_active:
                    error_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    if self.ensure_trace_handler():
                        self.trace_handler(f"[{error_time}] RX ERROR: {str(e)}")

    def update_display(self, data, timestamp):
        """Update display content (executed in main thread)"""
        try:
            hex_str = ' '.join(f"{b:02X}" for b in data)
            if self.ensure_trace_handler():
                self.trace_handler(f"RX: {hex_str}")
        except Exception as e:
            if self.ensure_trace_handler():
                self.trace_handler(f"Display ERROR: {str(e)}")

    def show_error(self, error_msg):
        """Show error message"""
        self.msg_display.insert(tk.END, f"{error_msg}\n")
        self.msg_display.see(tk.END)

    def on_hex_input(self, new_value):
        """Handle hex input formatting"""
        # Filter invalid characters
        filtered = ''.join([c for c in new_value.upper() if c in '0123456789ABCDEF '])
        # Format with spaces
        clean_str = filtered.replace(' ', '')
        formatted = ' '.join(clean_str[i:i+2] for i in range(0, len(clean_str), 2))
        # Update input field
        self.msg_input.delete(0, tk.END)
        self.msg_input.insert(0, formatted.strip())
        return False  # Prevent default handling

    def format_hex_input(self, event):
        """Handle keyboard release event formatting"""
        content = self.msg_input.get().replace(" ", "")
        # Remove non-hex characters
        content = ''.join(c for c in content if c in '0123456789ABCDEF')
        # Add space every two characters
        formatted = ' '.join(content[i:i+2] for i in range(0, len(content), 2))
        # Update Entry content
        self.msg_input.delete(0, tk.END)
        self.msg_input.insert(0, formatted)
    def on_keep_alive(self):
        """Handle keep alive button state change"""
        if self.ensure_trace_handler():
            self.trace_handler("Start 3E 00")
        if self.keep_alive_button.instate(['selected']):
            self.keep_alive_active = True
            self.keep_alive_button.configure(text="3E00: ON")
            self.start_keep_alive()
        else:
            self.stop_keep_alive()
            self.keep_alive_button.configure(text="3E00: OFF")

    def start_keep_alive(self):
        """Start keep alive thread"""
        self.keep_alive_thread = threading.Thread(target=self.send_keep_alive, daemon=True)
        self.keep_alive_thread.start()

    def stop_keep_alive(self):
        """Stop keep alive"""
        self.keep_alive_active = False
        if self.ensure_trace_handler():
            self.trace_handler("Stop 3E 00")
        if self.keep_alive_thread and self.keep_alive_thread.is_alive():
            self.keep_alive_thread.join(timeout=1.0)

    def send_keep_alive(self):
        """Send 3E00 periodically"""
        while self.keep_alive_active and self.tp_stack:
            try:
                data = bytes.fromhex("3E00")
                self.tp_stack.send(data)
                if self.ensure_trace_handler():
                    self.trace_handler(f"Keep Alive: 3E 00")
            except Exception as e:
                if self.ensure_trace_handler():
                    self.trace_handler(f"Keep Alive Error: {str(e)}")
            time.sleep(3.5)
            
    def ensure_trace_handler(self):
        """Ensure trace_handler is available"""
        if self.trace_handler is None:
            self.trace_handler = self.parent.winfo_toplevel().get_trace_handler()
        return self.trace_handler is not None