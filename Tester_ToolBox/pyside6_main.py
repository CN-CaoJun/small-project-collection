import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QComboBox, QPushButton, QLineEdit, QCheckBox,
    QMessageBox, QTextEdit, QFrame
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QIcon

# 添加模块路径
sys.path.insert(0, os.path.abspath("reference_modules/python-can"))
sys.path.insert(0, os.path.abspath("reference_modules/python-can-isotp"))
sys.path.insert(0, os.path.abspath("reference_modules/python-udsoncan"))

import can
from can.interfaces.vector import canlib

class ConnectionWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.can_bus = None
        self.connected = False
        self.channel_configs = {}
        self.fdcan = False
        self.trace_handler = None
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 主控制框架
        controls_frame = QFrame()
        controls_layout = QHBoxLayout(controls_frame)
        
        # 硬件选择部分
        hw_group = QGroupBox("Hardware")
        hw_layout = QVBoxLayout(hw_group)
        
        hw_control_layout = QHBoxLayout()
        self.hardware_combo = QComboBox()
        self.hardware_combo.setMinimumWidth(200)
        self.scan_button = QPushButton("Scan")
        self.scan_button.setMaximumWidth(80)
        self.scan_button.clicked.connect(self.scan_can_device)
        
        hw_control_layout.addWidget(self.hardware_combo)
        hw_control_layout.addWidget(self.scan_button)
        hw_layout.addLayout(hw_control_layout)
        
        # 波特率参数部分
        baud_group = QGroupBox("Baudrate Parameters")
        baud_layout = QVBoxLayout(baud_group)
        
        self.default_can_params = "fd=False,bitrate=500000,tseg1_abr=63,tseg2_abr=16,sjw_abr=16"
        self.default_canfd_params = "fd=True,bitrate=500000,data_bitrate=2000000,tseg1_abr=63,tseg2_abr=16,sjw_abr=16,sam_abr=1,tseg1_dbr=13,tseg2_dbr=6,sjw_dbr=6"
        
        self.baudrate_entry = QLineEdit()
        self.baudrate_entry.setText(self.default_can_params)
        self.baudrate_entry.setMinimumWidth(400)
        baud_layout.addWidget(self.baudrate_entry)
        
        # CAN-FD选项部分
        canfd_group = QGroupBox("CAN-FD")
        canfd_layout = QVBoxLayout(canfd_group)
        
        self.canfd_check = QCheckBox("CAN-FD")
        self.canfd_check.stateChanged.connect(self.on_canfd_changed)
        canfd_layout.addWidget(self.canfd_check)
        
        # 操作按钮部分
        operation_group = QGroupBox("Operation")
        operation_layout = QVBoxLayout(operation_group)
        
        self.init_button = QPushButton("Initialize")
        self.init_button.setCheckable(True)
        self.init_button.clicked.connect(self.on_init_toggle)
        operation_layout.addWidget(self.init_button)
        
        # 添加所有组件到主布局
        controls_layout.addWidget(hw_group)
        controls_layout.addWidget(baud_group)
        controls_layout.addWidget(canfd_group)
        controls_layout.addWidget(operation_group)
        
        layout.addWidget(controls_frame)
        self.setLayout(layout)
        
    def scan_can_device(self):
        try:
            self.channel_configs.clear()
            channel_list = []

            # 扫描SocketCAN接口（Linux）
            try:
                import platform
                self.log(f"platform.system(): {platform.system()}")
                if platform.system() == 'Linux':
                    self.log("Scanning SocketCAN interfaces...")
                    net_path = "/sys/class/net"
                    if os.path.exists(net_path):
                        for name in os.listdir(net_path):
                            if name.startswith(('can', 'vcan', 'slcan')):
                                channel_name = f"SocketCAN: {name}"
                                channel_list.append(channel_name)
                                self.channel_configs[channel_name] = {
                                    'type': 'socketcan',
                                    'channel': name
                                }
                                self.log(f"Found SocketCAN interface: {name}")
            except Exception as e:
                self.log(f"SocketCAN scan error: {str(e)}")

            # 扫描Vector设备
            if canlib.xldriver is not None:
                try:
                    canlib.xldriver.xlOpenDriver()
                    vector_configs = canlib.get_channel_configs()
                    
                    for config in vector_configs:
                        channel_name = f"{config.serial_number}: {config.name}"
                        channel_list.append(channel_name)
                        self.channel_configs[channel_name] = {
                            'type': 'vector',
                            'config': config,
                            'hw_channel': config.hw_channel
                        }
                except Exception as e:
                    self.log(f"Vector scan error: {str(e)}")
                finally:
                    canlib.xldriver.xlCloseDriver()

            # 更新UI
            if channel_list:
                self.hardware_combo.clear()
                self.hardware_combo.addItems(channel_list)
            else:
                self.show_error("No CAN devices found")

        except Exception as e:
            self.show_error(f"Device scan failed: {str(e)}")

    def show_error(self, message):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("Error")
        msg_box.setText(message)
        msg_box.exec()
        
    def on_canfd_changed(self, state):
        """CAN-FD选项改变时的处理"""
        if state == Qt.Checked:
            self.baudrate_entry.setText(self.default_canfd_params)
            self.fdcan = True
        else:
            self.baudrate_entry.setText(self.default_can_params)
            self.fdcan = False
            
    def on_init_toggle(self):
        """处理Initialize toggle按钮的状态变化"""
        if self.init_button.isChecked():
            self.initialize_can()
            if not self.can_bus:
                self.init_button.setChecked(False)
                self.init_button.setText("Initialize")
            else:
                self.init_button.setText("Release")
        else:
            self.release_can()
            self.init_button.setText("Initialize")
            
    def initialize_can(self):
        """Initialize CAN channel"""
        try:
            # 检查是否选择了通道
            selected_channel = self.hardware_combo.currentText()
            if not selected_channel:
                self.show_error("Please select a CAN channel first")
                return
            
            # 获取选中通道的配置
            if selected_channel not in self.channel_configs:
                self.show_error("Cannot find configuration for selected channel")
                return
                
            channel_config = self.channel_configs[selected_channel]
            
            # 获取波特率参数
            params = self.parse_baudrate_parameters()
            if not params:
                return
            
            if self.can_bus:
                self.can_bus.shutdown()
            
            self.log(f"channel_config['type']: {channel_config['type']}")
            
            if channel_config['type'] == 'vector':
                self.can_bus = canlib.VectorBus(
                    channel=channel_config['hw_channel'],
                    **params
                )
            elif channel_config['type'] == 'socketcan':
                self.log(f"channel_config['channel']: {channel_config['channel']}")
                self.can_bus = can.Bus(
                    interface='socketcan',
                    channel=channel_config['channel'],
                    bitrate=500000,
                    fd=False,
                )
                
            # 禁用连接框架中的所有控件
            self.hardware_combo.setEnabled(False)
            self.scan_button.setEnabled(False)
            self.baudrate_entry.setEnabled(False)
            self.canfd_check.setEnabled(False)
            
            self.log("CAN channel initialized successfully")
            
        except Exception as e:
            self.show_error(f"Failed to initialize CAN channel: {str(e)}")
            self.init_button.setChecked(False)
            
    def release_can(self):
        """Release CAN channel"""
        try:
            if self.can_bus:
                self.can_bus.shutdown()
                self.can_bus = None
                
            # 启用连接框架中的所有控件
            self.hardware_combo.setEnabled(True)
            self.scan_button.setEnabled(True)
            self.baudrate_entry.setEnabled(True)
            self.canfd_check.setEnabled(True)
            
            self.log("CAN channel released")
            
        except Exception as e:
            self.show_error(f"Failed to release CAN channel: {str(e)}")

    def parse_baudrate_parameters(self):
        params = {}
        try:
            # 分割参数字符串并转换为字典
            param_str = self.baudrate_entry.text()
            param_pairs = param_str.split(',')
            for pair in param_pairs:
                key, value = pair.split('=')
                key = key.strip()
                value = value.strip()
                
                # 处理布尔值
                if value.lower() == 'true':
                    params[key] = True
                elif value.lower() == 'false':
                    params[key] = False
                else:
                    # 处理数值
                    try:
                        params[key] = int(value)
                    except ValueError:
                        # 如果无法转换为整数则保持原始字符串
                        params[key] = value
            
            # 打印所有参数
            self.log("CAN Parameter Configuration:")
            for key, value in params.items():
                self.log(f"  {key}: {value} ({type(value).__name__})")
                
            return params
        except Exception as e:
            self.show_error(f"Parameter format error: {str(e)}")
            return None
            
    def get_can_bus(self):
        return self.can_bus, self.fdcan

    def log(self, message: str):
        if self.trace_handler:
            self.trace_handler(message)
        else:
            print(message)  # 如果没有trace_handler，则打印到控制台
            
    def set_trace_handler(self, handler):
        self.trace_handler = handler

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chery ZCU Diagnostic ToolBox V1.0.0.4 - PySide6")
        self.setGeometry(100, 100, 800, 600)
        
        # 设置图标
        icon_path = os.path.join(os.path.dirname(__file__), 'assets', 'icon.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建连接组件
        connection_group = QGroupBox("Connection")
        connection_layout = QVBoxLayout(connection_group)
        
        self.connection_widget = ConnectionWidget()
        connection_layout.addWidget(self.connection_widget)
        
        # 创建诊断组件（占位）
        diagnostic_group = QGroupBox("Diagnostic")
        diagnostic_layout = QVBoxLayout(diagnostic_group)
        diagnostic_placeholder = QLabel("Diagnostic functionality will be implemented here")
        diagnostic_layout.addWidget(diagnostic_placeholder)
        
        # 创建引导加载程序组件（占位）
        bootloader_group = QGroupBox("Chery Bootloader")
        bootloader_layout = QVBoxLayout(bootloader_group)
        bootloader_placeholder = QLabel("Bootloader functionality will be implemented here")
        bootloader_layout.addWidget(bootloader_placeholder)
        
        # 创建跟踪消息组件
        trace_group = QGroupBox("Trace Messages")
        trace_layout = QVBoxLayout(trace_group)
        
        self.trace_text = QTextEdit()
        self.trace_text.setReadOnly(True)
        self.trace_text.setMaximumHeight(200)
        trace_layout.addWidget(self.trace_text)
        
        # 添加所有组件到主布局
        main_layout.addWidget(connection_group)
        main_layout.addWidget(diagnostic_group)
        main_layout.addWidget(bootloader_group)
        main_layout.addWidget(trace_group)
        
        # 设置trace处理器
        self.connection_widget.set_trace_handler(self.append_trace_message)
        
    def append_trace_message(self, message):
        """添加跟踪消息到文本区域"""
        self.trace_text.append(message)
        # 自动滚动到底部
        scrollbar = self.trace_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()