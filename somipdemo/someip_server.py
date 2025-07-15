import asyncio
import ipaddress
import logging

from someipy import (
    TransportLayerProtocol,
    ServiceBuilder,
    EventGroup,
    construct_server_service_instance,
)
from someipy.service_discovery import construct_service_discovery
from someipy.logging import set_someipy_log_level
from someipy.serialization import Uint8, Uint64, Float32

# 定义消息结构
class TemperatureMsg:
    def __init__(self):
        self.temperature = 0
    
    def serialize(self):
        # 简单的序列化，返回温度值的字节表示
        return self.temperature.to_bytes(2, byteorder='big')

# 配置参数
SD_MULTICAST_GROUP = "224.224.224.245"
SD_PORT = 30490
INTERFACE_IP = "127.0.0.1"

SAMPLE_SERVICE_ID = 0x1234
SAMPLE_INSTANCE_ID = 0x5678
SAMPLE_EVENTGROUP_ID = 0x0321
SAMPLE_EVENT_ID = 0x0123

async def main():
    # 设置日志级别
    set_someipy_log_level(logging.DEBUG)
    
    # 构建服务发现 - 需要await
    service_discovery = await construct_service_discovery(
        multicast_group_ip=SD_MULTICAST_GROUP,
        sd_port=SD_PORT,
        unicast_ip=INTERFACE_IP
    )
    
    # 构建服务
    service_builder = ServiceBuilder()
    service_builder.with_service_id(SAMPLE_SERVICE_ID)
    service_builder.with_major_version(1)
    
    # 创建事件组对象 - 正确的初始化方式
    eventgroup = EventGroup(id=SAMPLE_EVENTGROUP_ID, event_ids=[SAMPLE_EVENT_ID])
    
    # 添加事件组对象
    service_builder.with_eventgroup(eventgroup)
    
    service = service_builder.build()
    
    # 创建服务器实例 - 需要await
    service_instance_temperature = await construct_server_service_instance(
        service,  # 第一个参数直接传service，不使用关键字参数
        instance_id=SAMPLE_INSTANCE_ID,
        endpoint=(
            ipaddress.IPv4Address(INTERFACE_IP),
            3000,
        ),  # endpoint必须是元组格式
        ttl=5,
        sd_sender=service_discovery,
        cyclic_offer_delay_ms=2000,
        protocol=TransportLayerProtocol.UDP
    )
    
    # 将服务实例附加到服务发现对象 - 这是关键步骤！
    service_discovery.attach(service_instance_temperature)
    
    print("Start offering service...")
    # start_offer()不是异步方法，不需要await
    service_instance_temperature.start_offer()
    
    # 创建温度消息
    temp_counter = 20
    
    try:
        # 周期性发送事件
        # 在发送事件前检查是否有订阅者
        while True:
            await asyncio.sleep(1)
            
            # 检查是否有订阅者 - 使用 _subscribers 属性
            if hasattr(service_instance_temperature, '_subscribers') and service_instance_temperature._subscribers:
                # 创建温度消息
                tmp_msg = TemperatureMsg()
                tmp_msg.temperature = temp_counter
                temp_counter += 1
                if temp_counter > 30:
                    temp_counter = 20
                
                # 发送事件
                payload = tmp_msg.serialize()
                print(f"Sending temperature: {tmp_msg.temperature}°C")
                
                service_instance_temperature.send_event(
                    SAMPLE_EVENTGROUP_ID, SAMPLE_EVENT_ID, payload
                )
            else:
                print("No subscribers, skipping event send")
            
    except asyncio.CancelledError:
        print("Stop offering service...")
        await service_instance_temperature.stop_offer()
    finally:
        print("Service Discovery close...")
        service_discovery.close()

if __name__ == "__main__":
    asyncio.run(main())