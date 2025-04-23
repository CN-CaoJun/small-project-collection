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

class FlashingProcess:
    def __init__(self, uds_client: Client, trace_handler=None):
        self.client = uds_client
        self.trace_handler = trace_handler
        
    def log(self, message: str):
        """输出日志"""
        if self.trace_handler:
            self.trace_handler(message)

    def execute_flashing_sequence(self, firmware_folder: str) -> bool:
        try:
            with self.client as client:  # 使用上下文管理器
                # Step 0: 切换到编程会话 (使用原始发送)
                self.log("Step 0: 发送原始编程会话请求 (10 03)")
                try:
                    # 发送原始10 03请求
                    client.conn.send(bytes.fromhex('10 03'))
                    
                    # 等待响应并验证格式
                    response = client.wait_frame(timeout=client.config['request_timeout'])
                    if not response or len(response.data) < 2:
                        self.log("接收响应失败")
                        return False
                        
                    # 验证响应首字节为50（0x10的正响应格式）
                    if response.data[0] != 0x50:
                        self.log(f"无效响应首字节: 0x{response.data[0]:02X}")
                        return False
                        
                    self.log(f"成功进入编程会话，完整响应: {response.data.hex().upper()}")
                    
                except Exception as e:
                    self.log(f"编程会话请求失败: {str(e)}")
                    return False
                response = client.change_session(0x03)
                if not response or response.code != 0x50:
                    self.log("切换到编程会话失败")
                    return False
                
                # Step 1: 发送原始31 01 D0 03请求
                self.log("Step 1: 发送原始请求 31 01 D0 03")
                try:
                    # 构造请求数据
                    request_data = bytes.fromhex('31 01 D0 03')
                    # 使用底层连接发送原始数据
                    client.conn.send(request_data)
                    # 等待响应（根据配置的超时时间）
                    response = client.wait_frame(timeout=client.config['request_timeout'])
                    if not response:
                        self.log("接收响应超时")
                        return False
                    # 解析原始响应数据
                    expected_response = bytes.fromhex('71 01 D0 03 00')
                    if response.data != expected_response:
                        self.log(f"无效响应，期望：{expected_response.hex()}，实际收到：{response.data.hex()}")
                        return False
                    self.log("扩展会话请求成功")
                    
                except Exception as e:
                    self.log(f"发送原始请求失败: {str(e)}")
                    return False

                # Step 2: 切换到编程会话
                self.log("Step 2: 切换到编程会话 (10 02)")
                response = client.change_session(0x02)
                if not response or response.code != 0x50:
                    self.log("切换到编程会话失败")
                    return False
    
                # Step 3-4: 安全访问
                self.log("Step 3-4: 安全访问流程")
                seed = self.client.security_access(0x07)
                if not seed or seed.code != 0x67:
                    self.log("获取种子失败")
                    return False
                    
                key = bytes([0x9D, 0xEF, 0x8A, 0x4D])  # 示例密钥，需替换实际计算值
                unlock = self.client.security_access(0x08, key)
                if not unlock or unlock.code != 0x67:
                    self.log("密钥验证失败")
                    return False
    
                # Step 5: 写入数据标识符
                self.log("Step 5: 写入F15A标识符")
                data = bytes.fromhex('40 04 13 00 00 00 03 00 00 00 00 00 00 00 00')
                wdb_response = self.client.write_data_by_identifier(0xF15A, data)
                if not wdb_response or wdb_response.code != 0x6E:
                    self.log("写入数据标识符失败")
                    return False
    
                # Step 6: 请求下载
                self.log("Step 6: 请求下载")
                mem_loc = MemoryLocation(
                    address=0x00000000, 
                    size=0x0580,
                    address_format=MemoryLocation.Format.ABSOLUTE_ADDRESS,
                    memory_size_format=MemoryLocation.Format.ABSOLUTE_ADDRESS
                )
                dl_response = self.client.request_download(mem_loc)
                if not dl_response or dl_response.code != 0x74:
                    self.log("下载请求失败")
                    return False
    
                # Step 7: 传输数据 (gen6nu_sbl.hex)
                self.log("Step 7: 传输HEX文件")
                sbl_path = os.path.join(firmware_folder, 'gen6nu_sbl.hex')
                seq_num = 1
                for chunk in self.read_file_in_chunks(sbl_path, 512):
                    td_response = self.client.transfer_data(seq_num, chunk)
                    if not td_response or td_response.code != 0x76:
                        self.log(f"数据传输失败 @ 块{seq_num}")
                        return False
                    seq_num += 1
    
                # Step 8: 退出传输
                self.log("Step 8: 退出传输")
                exit_response = self.client.request_transfer_exit()
                if not exit_response or exit_response.code != 0x77:
                    self.log("退出传输失败")
                    return False
    
                # Step 9: 传输签名文件 (gen6nu_sbl_sign.bin)
                self.log("Step 9: 传输签名文件")
                sign_path = os.path.join(firmware_folder, 'gen6nu_sbl_sign.bin')
                with open(sign_path, 'rb') as f:
                    sign_data = f.read(512)
                    rc_response = client.routine_control(
                        routine_id=0xD002,
                        control_type=0x01,
                        data=sign_data
                    )
                    if not rc_response or rc_response.code != 0x71:
                        self.log("签名验证失败")
                        return False
    
            self.log("刷写流程成功完成")
            return True
        except Exception as e:
            self.log(f"刷写过程发生错误: {str(e)}")
            return False

               
            
    