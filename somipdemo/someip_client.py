import asyncio
import ipaddress
import logging

from someipy import (
    TransportLayerProtocol,
    ServiceBuilder,
    EventGroup,
    construct_client_service_instance,
)
from someipy.service_discovery import construct_service_discovery
from someipy.logging import set_someipy_log_level

# 配置参数
SD_MULTICAST_GROUP = "224.224.224.245"
SD_PORT = 30490
INTERFACE_IP = "127.0.0.1"

SAMPLE_SERVICE_ID = 0x1234
SAMPLE_INSTANCE_ID = 0x5678
SAMPLE_EVENTGROUP_ID = 0x0321
SAMPLE_EVENT_ID = 0x0123

# 事件回调函数
def event_callback(event_id, payload):
    # 解析温度数据
    if len(payload) >= 2:
        temperature = int.from_bytes(payload[:2], byteorder='big')
        print(f"Received temperature event {hex(event_id)}: {temperature}°C")
    else:
        print(f"Received event {hex(event_id)} with payload: {payload.hex()}")

async def main():
    # 设置日志级别
    set_someipy_log_level(logging.DEBUG)
    
    # 构建服务发现 - 需要await
    service_discovery = await construct_service_discovery(
        multicast_group_ip=SD_MULTICAST_GROUP,
        sd_port=SD_PORT,
        unicast_ip=INTERFACE_IP
    )
    
    # 构建客户端服务
    service_builder = ServiceBuilder()
    service_builder.with_service_id(SAMPLE_SERVICE_ID)
    service_builder.with_major_version(1)
    
    # 创建事件组对象
    eventgroup = EventGroup()
    eventgroup.id = SAMPLE_EVENTGROUP_ID
    eventgroup.add_event_id(SAMPLE_EVENT_ID)
    
    # 添加事件组对象
    service_builder.with_eventgroup(eventgroup)
    
    service = service_builder.build()
    
    print("Starting service discovery...")
    await service_discovery.start()
    
    # 创建客户端实例
    client_instance = construct_client_service_instance(
        service=service,
        instance_id=SAMPLE_INSTANCE_ID,
        endpoint=ipaddress.IPv4Address(INTERFACE_IP),
        ttl=5,
        sd_sender=service_discovery,
        protocol=TransportLayerProtocol.UDP
    )
    
    print("Subscribing to eventgroup...")
    
    # 订阅事件组
    client_instance.subscribe_eventgroup(
        eventgroup_id=SAMPLE_EVENTGROUP_ID,
        event_handler=event_callback
    )
    
    try:
        # 保持运行
        print("Client is running, waiting for events...")
        await asyncio.Future()  # 永远等待
    except KeyboardInterrupt:
        print("Client stopping...")
    finally:
        print("Service Discovery close...")
        service_discovery.close()

if __name__ == "__main__":
    asyncio.run(main())