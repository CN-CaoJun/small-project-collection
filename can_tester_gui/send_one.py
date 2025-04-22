#!/usr/bin/env python


import sys
import os
import logging

# 添加本地 python-can 源码到 Python 路径
sys.path.insert(0, os.path.abspath("python-can"))
sys.path.insert(0, os.path.abspath("python-can-isotp"))

"""
This example shows how sending a single message works.
"""

# 导入本地库（优先于系统安装的库）
import can
from can.interface import Bus

# 配置日志（可选，用于调试）
logging.basicConfig(level=logging.DEBUG)


can.rc['interface'] = 'vector'
can.rc['bustype'] = 'vector'
can.rc['channel'] = '0'
can.rc['app_name'] = 'Vector_CAN'
 
can.rc['fd'] = False  
can.rc['bitrate'] = 500000
# can.rc['data_bitrate'] = 2000000

can.rc['sjw_abr'] = 16
can.rc['tseg1_abr'] = 63
can.rc['tseg2_abr'] = 16
can.rc['sam_abr'] = 1

def send_can_message():
    try:
        bus = Bus()
                
        msg = can.Message(
            arbitration_id=0x123,
            data=[0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18],
            is_extended_id=False  # 标准帧
        )
        
        bus.send(msg)
        print(f"[Success] Sent CAN message: {msg}")
        
    except Exception as e:
        print(f"[Error] Failed to send message: {e}")
    finally:
        if 'bus' in locals():
            bus.shutdown()

if __name__ == "__main__":
    send_can_message()