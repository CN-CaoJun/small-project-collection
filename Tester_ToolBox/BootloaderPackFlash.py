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

from udsoncan.connections import PythonIsoTpConnection
from udsoncan.client import Client
import udsoncan.configs
# from udsoncan import services
# from udsoncan import MemoryLocation
from typing import Optional, List, Union, Tuple
from udsoncan import Response

class FlashingProcess:
    def __init__(self, uds_client: Client, trace_handler=None):
        self.client = uds_client
        self.trace_handler = trace_handler
        self.firmware_folder = None
        
    def log(self, message: str):
        """输出日志"""
        if self.trace_handler:
            self.trace_handler(message)
            
    def change_session(self, session_type: int) -> bool:
        """步骤1和3: 切换诊断会话"""
        self.log(f"步骤: 切换到会话类型 0x{session_type:02X}")
        try:
            with self.client as client:
                response = client.change_session(session_type)
                if response:
                    self.log(f"会话切换成功，响应: {response.data.hex().upper()}")
                    return True
                else:
                    self.log("会话切换失败")
                    return False
        except Exception as e:
            self.log(f"会话切换异常: {str(e)}")
            return False
            
    def enter_extended_session(self) -> bool:
        """步骤2: 进入扩展会话"""
        self.log("步骤: 进入扩展会话")
        try:
            with self.client as client:
                # 使用原始发送方式
                request = bytes.fromhex('31 01 D0 03')
                client.conn.send(request)
                response = client.conn.wait_frame(timeout=3)
                # Print response content
                self.log(f"Response content: {response.hex().upper() if response else 'None'}")
                if response and response.hex().upper().startswith('7101D00300'):
                    self.log("扩展会话成功")
                    return True
                else:
                    self.log(f"扩展会话失败，响应: {response.hex().upper() if response else 'None'}")
                    return False
        except Exception as e:
            self.log(f"扩展会话异常: {str(e)}")
            return False
            
    def security_access(self) -> bool:
        """步骤4和5: 安全访问"""
        self.log("步骤: 执行安全访问")
        try:
            with self.client as client:
                # 请求种子 (步骤4)
                response = client.request_seed(level=0x07)
                if not response:
                    self.log("获取种子失败")
                    return False
                    
                seed = response.data[2:6]  # 提取种子数据
                self.log(f"获取种子成功: {seed.hex().upper()}")
                
                # 发送密钥 (步骤5)
                key = bytes.fromhex('9D EF 8A 4D')  # 固定密钥
                response = client.send_key(level=0x08, key=key)
                
                if response:
                    self.log("安全访问成功")
                    return True
                else:
                    self.log("安全访问失败")
                    return False
        except Exception as e:
            self.log(f"安全访问异常: {str(e)}")
            return False
            
    def write_f15a_identifier(self) -> bool:
        """步骤6: 写入F15A标识符"""
        self.log("步骤: 写入F15A标识符")
        try:
            with self.client as client:
                # 使用原始发送方式
                data = bytes.fromhex('2E F1 5A 40 04 13 00 00 00 03 00 00 00 00 00 00 00 00')
                client.conn.send(data)
                
                # 等待中间响应 (7F 2E 78)
                response = client.conn.wait_frame(timeout=3)
                if not response or response.hex().upper() != '7F2E78':
                    self.log(f"未收到预期的中间响应，收到: {response.hex().upper() if response else 'None'}")
                    return False
                    
                # 等待最终响应 (6E F1 5A)
                final_response = client.conn.wait_frame(timeout=5)
                if final_response and final_response.hex().upper() == '6EF15A':
                    self.log("写入F15A标识符成功")
                    return True
                else:
                    self.log(f"写入F15A标识符失败，响应: {final_response.hex().upper() if final_response else 'None'}")
                    return False
        except Exception as e:
            self.log(f"写入F15A标识符异常: {str(e)}")
            return False
            
    def request_download(self) -> bool:
        """步骤7: 请求下载"""
        self.log("步骤: 请求下载")
        try:
            with self.client as client:
                # 使用原始发送方式
                request = bytes.fromhex('34 00 44 20 00 00 00 00 00 05 80')
                client.conn.send(request)
                response = client.conn.wait_frame(timeout=5)
                
                if response and response.hex().upper().startswith('74'):
                    self.log(f"下载请求成功，响应: {response.hex().upper()}")
                    return True
                else:
                    self.log(f"下载请求失败，响应: {response.hex().upper() if response else 'None'}")
                    return False
        except Exception as e:
            self.log(f"下载请求异常: {str(e)}")
            return False
            
    def transfer_hex_data(self) -> bool:
        """步骤8: 传输HEX文件数据"""
        self.log("步骤: 传输HEX文件数据")
        try:
            if not self.firmware_folder:
                self.log("错误: 固件文件夹路径未设置")
                return False
                
            hex_file_path = os.path.join(self.firmware_folder, 'gen6nu_sbl.hex')
            if not os.path.exists(hex_file_path):
                self.log(f"错误: HEX文件不存在: {hex_file_path}")
                return False
                
            with self.client as client:
                # 读取hex文件内容
                with open(hex_file_path, 'rb') as f:
                    hex_data = f.read()
                    
                # 发送数据块
                sequence = 1
                request = bytes([0x36, sequence]) + hex_data
                client.conn.send(request)
                
                # 等待中间响应 (7F 36 78)
                response = client.conn.wait_frame(timeout=3)
                if not response or response.hex().upper() != '7F3678':
                    self.log(f"未收到预期的中间响应，收到: {response.hex().upper() if response else 'None'}")
                    return False
                    
                # 等待最终响应 (76 01)
                final_response = client.conn.wait_frame(timeout=10)  # 增加超时时间
                if final_response and final_response.hex().upper() == '7601':
                    self.log("数据传输成功")
                    return True
                else:
                    self.log(f"数据传输失败，响应: {final_response.hex().upper() if final_response else 'None'}")
                    return False
        except Exception as e:
            self.log(f"数据传输异常: {str(e)}")
            return False
            
    def exit_transfer(self) -> bool:
        """步骤9: 退出传输"""
        self.log("步骤: 请求退出传输")
        try:
            with self.client as client:
                # 使用原始发送方式
                client.conn.send(bytes([0x37]))
                response = client.conn.wait_frame(timeout=3)
                
                if response and response.hex().upper() == '77':
                    self.log("退出传输成功")
                    return True
                else:
                    self.log(f"退出传输失败，响应: {response.hex().upper() if response else 'None'}")
                    return False
        except Exception as e:
            self.log(f"退出传输异常: {str(e)}")
            return False
            
    def transfer_signature(self, bin_path: str) -> bool:
        """步骤10: 传输签名文件"""
        self.log("步骤: 传输签名文件")
        try:
            if not os.path.exists(bin_path):
                self.log(f"错误: 签名文件不存在: {bin_path}")
                return False
                
            with self.client as client:
                # 读取签名文件
                with open(bin_path, 'rb') as f:
                    bin_data = f.read(512)  # 读取512字节
                    
                # 发送数据
                header = bytes.fromhex('31 01 D0 02')
                request = header + bin_data
                client.conn.send(request)
                
                # 等待中间响应 (7F 31 78)
                response = client.conn.wait_frame(timeout=3)
                if not response or response.hex().upper() != '7F3178':
                    self.log(f"未收到预期的中间响应，收到: {response.hex().upper() if response else 'None'}")
                    return False
                    
                # 等待最终响应 (71 01 D0 02 00)
                final_response = client.conn.wait_frame(timeout=5)
                if final_response and final_response.hex().upper() == '7101D00200':
                    self.log("签名验证成功")
                    return True
                else:
                    self.log(f"签名验证失败，响应: {final_response.hex().upper() if final_response else 'None'}")
                    return False
        except Exception as e:
            self.log(f"签名传输异常: {str(e)}")
            return False
            
    def execute_flashing_sequence(self, firmware_folder: str) -> bool:
        """执行完整的刷写流程"""
        self.firmware_folder = firmware_folder
        self.log("开始执行刷写流程...")
        
        try:
            # 定义刷写步骤
            steps = [
                # Lambda is used here to create an anonymous function that calls change_session with a fixed parameter
                # This allows the function to be passed as a callback without executing immediately
                lambda: self.change_session(0x03),                                # 步骤1: 切换到扩展诊断会话
                self.enter_extended_session,                                      # 步骤2: 进入扩展会话
                lambda: self.change_session(0x02),                                # 步骤3: 切换到编程会话
                self.security_access,                                             # 步骤4-5: 安全访问
                self.write_f15a_identifier,                                       # 步骤6: 写入F15A标识符
                self.request_download,                                            # 步骤7: 请求下载
                self.transfer_hex_data,                                           # 步骤8: 传输HEX数据
                self.exit_transfer,                                               # 步骤9: 退出传输
                lambda: self.transfer_signature(os.path.join(firmware_folder, 'gen6nu_sbl_sign.bin'))  # 步骤10: 传输签名
            ]
            
            # 执行每个步骤
            for i, step in enumerate(steps, 1):
                self.log(f"执行步骤 {i}/{len(steps)}")
                if not step():
                    self.log(f"步骤 {i} 失败，终止刷写流程")
                    return False
                    
            self.log("刷写流程全部完成")
            return True
            
        except Exception as e:
            self.log(f"刷写流程异常终止: {str(e)}")