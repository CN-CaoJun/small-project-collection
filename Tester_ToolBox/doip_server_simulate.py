import socket
import threading
import struct
import time
import json
import os
from typing import Dict, Tuple
import sys

class DoIPServer:
    def __init__(self, host='127.0.0.1', port=13400, server_addr=0x1001, server_addr_func=0x1FFF, client_addr=0x0E80):
        self.host = host
        self.port = port
        self.server_addr = server_addr
        self.server_addr_func = server_addr_func 
        self.client_addr = client_addr
        self.tcp_socket = None
        self.udp_socket = None
        self.running = False
        self.clients = {}  
        
        # 加载响应配置
        self.response_config = self.load_response_config()
        
        # DoIP消息类型定义
        self.DOIP_HEADER_SIZE = 8
        self.DOIP_VERSION = 0x03
        self.DOIP_INVERSE_VERSION = 0xFC
        
        # DoIP消息类型
        self.DOIP_VEHICLE_IDENTIFICATION_REQUEST = 0x0001
        self.DOIP_VEHICLE_IDENTIFICATION_RESPONSE = 0x0004
        self.DOIP_ROUTING_ACTIVATION_REQUEST = 0x0005
        self.DOIP_ROUTING_ACTIVATION_RESPONSE = 0x0006
        self.DOIP_DIAGNOSTIC_MESSAGE = 0x8001
        self.DOIP_DIAGNOSTIC_MESSAGE_ACK = 0x8002
        self.DOIP_DIAGNOSTIC_MESSAGE_NACK = 0x8003
    
    def load_response_config(self):
        """加载响应配置文件"""
        config_path = os.path.join(os.path.dirname(__file__), 'config_json', 'R_ZCU_response_doip.json')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_list = json.load(f)
                # 将列表转换为字典，便于快速查找
                config_dict = {}
                for item in config_list:
                    req_hex = item['req'].upper()
                    res_hex = item['res'].upper()
                    config_dict[req_hex] = res_hex
                print(f"Loaded {len(config_dict)} response configurations from {config_path}")
                return config_dict
        except FileNotFoundError:
            print(f"Warning: Response config file not found: {config_path}")
            print("Using default response generation")
            return {}
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON config file: {e}")
            return {}
        except Exception as e:
            print(f"Error loading response config: {e}")
            return {}
    
    def start_server(self):
        """启动DoIP服务器（TCP和UDP）"""
        try:
            # 启动TCP服务器
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.tcp_socket.bind((self.host, self.port))
            self.tcp_socket.listen(5)
            
            # 启动UDP服务器
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # 添加广播权限
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.udp_socket.bind((self.host, self.port))
            
            self.running = True
            
            print(f"DoIP Server started on {self.host}:{self.port}")
            print(f"Physical Address: 0x{self.server_addr:04X}")
            print(f"Functional Address: 0x{self.server_addr_func:04X}")
            print(f"Expected Client Address: 0x{self.client_addr:04X}")
            print("TCP and UDP sockets are listening...")
            print("Waiting for connections...")
            
            self.send_udp_vehicle_announcements()
            print("Waiting for connections...")
            
            # 创建UDP监听线程
            udp_thread = threading.Thread(target=self.handle_udp_messages)
            udp_thread.daemon = True
            udp_thread.start()
            
            # TCP连接处理循环
            while self.running:
                try:
                    client_socket, client_address = self.tcp_socket.accept()
                    print(f"New TCP connection from {client_address}")
                    
                    # 为每个TCP客户端创建处理线程
                    client_thread = threading.Thread(
                        target=self.handle_tcp_client,
                        args=(client_socket, client_address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                except socket.error as e:
                    if self.running:
                        print(f"TCP Socket error: {e}")
                    break
        except KeyboardInterrupt:
            print("\nReceived keyboard interrupt")          
        except Exception as e:
            print(f"Server error: {e}")
        finally:
            self.stop_server()
    
    def handle_udp_messages(self):
        """处理UDP消息"""
        print("UDP message handler started")
        
        while self.running:
            try:
                # 接收UDP数据
                data, client_address = self.udp_socket.recvfrom(4096)
                print(f"Received UDP message from {client_address}, length: {len(data)}")
                
                if len(data) >= self.DOIP_HEADER_SIZE:
                    # 解析DoIP头
                    version, inv_version, payload_type, payload_length = struct.unpack('>BBHI', data[:self.DOIP_HEADER_SIZE])
                    
                    print(f"UDP DoIP message:")
                    print(f"  Version: 0x{version:02X}")
                    print(f"  Inverse Version: 0x{inv_version:02X}")
                    print(f"  Payload Type: 0x{payload_type:04X}")
                    print(f"  Payload Length: {payload_length}")
                    
                    # 获取载荷数据
                    payload_data = data[self.DOIP_HEADER_SIZE:self.DOIP_HEADER_SIZE + payload_length]
                    
                    # 处理UDP DoIP消息
                    self.process_udp_doip_message(client_address, payload_type, payload_data)
                else:
                    print(f"Invalid UDP DoIP message: too short ({len(data)} bytes)")
            except socket.timeout:
                continue
            except socket.error as e:
                if self.running:
                    print(f"UDP socket error: {e}")
                break
            except KeyboardInterrupt:
                print("\nReceived keyboard interrupt in UDP handler")
                break
            except Exception as e:
                print(f"UDP message handling error: {e}")
                
        print("UDP message handler stopped")
    
    def process_udp_doip_message(self, client_address: Tuple[str, int], payload_type: int, payload_data: bytes):
        """处理UDP DoIP消息"""
        # Skip loopback address processing for UDP messages
        # if client_address[0] == '127.0.0.1':
        #     print(f"Skipping loopback UDP message from {client_address}")
        #     return
        if payload_type == self.DOIP_VEHICLE_IDENTIFICATION_REQUEST:
            self.handle_udp_vehicle_identification_request(client_address, payload_data)
        else:
            print(f"Unknown UDP DoIP message type: 0x{payload_type:04X}")
    
    def handle_udp_vehicle_identification_request(self, client_address: Tuple[str, int], payload_data: bytes):
        """处理UDP车辆识别请求"""
        print(f"Processing UDP Vehicle Identification Request from {client_address}")
        
        # 构造车辆识别响应
        vin = b'1HGBH41JXMN109186'  # 示例VIN码
        logical_address = struct.pack('>H', self.server_addr)
        eid = b'\x01\x02\x03\x04\x05\x06'  # 示例EID
        gid = b'\x07\x08\x09\x0A\x0B\x0C'  # 示例GID
        further_action = b'\x00'  # 无需进一步操作
        
        response_payload = vin + logical_address + eid + gid + further_action
        
        # 发送UDP响应
        self.send_udp_doip_message(client_address, self.DOIP_VEHICLE_IDENTIFICATION_RESPONSE, response_payload)
        print(f"UDP Vehicle Identification Response sent to {client_address}")
    
    def send_udp_doip_message(self, client_address: Tuple[str, int], payload_type: int, payload_data: bytes):
        """发送UDP DoIP消息"""
        # 构造DoIP头
        header = struct.pack('>BBHI', 
                           self.DOIP_VERSION, 
                           self.DOIP_INVERSE_VERSION, 
                           payload_type, 
                           len(payload_data))
        
        # 发送UDP消息
        message = header + payload_data
        self.udp_socket.sendto(message, client_address)
        
        print(f"Sent UDP DoIP message to {client_address}: Type=0x{payload_type:04X}, Length={len(payload_data)}")
        
    def send_udp_vehicle_announcements(self):
        """启动时发送三次车辆公告消息"""
        print("Sending Vehicle Announcements...")
        
        # 构造车辆公告消息
        vin = b'1HGBH41JXMN109186'  # 示例VIN码
        logical_address = struct.pack('>H', self.server_addr)
        eid = b'\x01\x02\x03\x04\x05\x06'  # 示例EID
        gid = b'\x07\x08\x09\x0A\x0B\x0C'  # 示例GID
        further_action = b'\x00'  # 无需进一步操作
        sync_status = b'\x10'  # 同步状态 - 已同步
        
        # DoIP Vehicle Announcement Message (0x0004) 的载荷
        announcement_payload = vin + logical_address + eid + gid + further_action + sync_status
        
        # 广播地址
        broadcast_address = ('255.255.255.255', self.port)
        
        # 发送三次公告，每次间隔500毫秒
        for i in range(3):
            try:
                # 构造DoIP头
                header = struct.pack('>BBHI', 
                                   self.DOIP_VERSION, 
                                   self.DOIP_INVERSE_VERSION, 
                                   self.DOIP_VEHICLE_IDENTIFICATION_RESPONSE,  # 0x0004
                                   len(announcement_payload))
                
                # 发送UDP广播消息
                message = header + announcement_payload
                self.udp_socket.sendto(message, broadcast_address)
                
                print(f"Vehicle Announcement {i+1}/3 sent to broadcast address")
                
                # 等待500毫秒
                time.sleep(1)
                
            except Exception as e:
                print(f"Error sending vehicle announcement {i+1}: {e}")
        
        print("Vehicle Announcements completed")
        
    def handle_tcp_client(self, client_socket: socket.socket, client_address: Tuple[str, int]):
        """处理TCP客户端连接（原handle_client方法重命名）"""
        client_id = f"{client_address[0]}:{client_address[1]}"
        self.clients[client_id] = {
            'socket': client_socket,
            'address': client_address,
            'routing_activated': False
        }
        
        try:
            while self.running:
                # 接收DoIP消息头
                header_data = self.receive_exact(client_socket, self.DOIP_HEADER_SIZE)
                if not header_data:
                    break
                
                # 解析DoIP头
                version, inv_version, payload_type, payload_length = struct.unpack('>BBHI', header_data)
                
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Received TCP DoIP message: Version: 0x{version:02X}, Inverse Version: 0x{inv_version:02X}, Payload Type: 0x{payload_type:04X}, Payload Length: {payload_length}")
                
                # 接收载荷数据
                payload_data = b''
                if payload_length > 0:
                    payload_data = self.receive_exact(client_socket, payload_length)
                    if not payload_data:
                        break
                
                # 处理不同类型的DoIP消息
                self.process_tcp_doip_message(client_socket, payload_type, payload_data)
                
        except Exception as e:
            print(f"TCP Client {client_id} error: {e}")
        finally:
            print(f"TCP Client {client_id} disconnected")
            client_socket.close()
            if client_id in self.clients:
                del self.clients[client_id]
    
    def receive_exact(self, sock: socket.socket, length: int) -> bytes:
        """接收指定长度的数据"""
        data = b''
        while len(data) < length:
            chunk = sock.recv(length - len(data))
            if not chunk:
                return None
            data += chunk
        return data
    
    def process_tcp_doip_message(self, client_socket: socket.socket, payload_type: int, payload_data: bytes):
        """处理TCP DoIP消息（原process_doip_message方法重命名）"""
        if payload_type == self.DOIP_VEHICLE_IDENTIFICATION_REQUEST:
            self.handle_vehicle_identification_request(client_socket, payload_data)
        elif payload_type == self.DOIP_ROUTING_ACTIVATION_REQUEST:
            self.handle_routing_activation_request(client_socket, payload_data)
        elif payload_type == self.DOIP_DIAGNOSTIC_MESSAGE:
            self.handle_diagnostic_message(client_socket, payload_data)
        else:
            print(f"Unknown TCP DoIP message type: 0x{payload_type:04X}")
    
    def handle_vehicle_identification_request(self, client_socket: socket.socket, payload_data: bytes):
        """处理车辆识别请求"""
        print("Processing Vehicle Identification Request")
        
        # 构造车辆识别响应
        vin = b'1HGBH41JXMN109186'  # 示例VIN码
        logical_address = struct.pack('>H', self.server_addr)
        eid = b'\x01\x02\x03\x04\x05\x06'  # 示例EID
        gid = b'\x07\x08\x09\x0A\x0B\x0C'  # 示例GID
        further_action = b'\x00'  # 无需进一步操作
        
        response_payload = vin + logical_address + eid + gid + further_action
        
        self.send_doip_message(client_socket, self.DOIP_VEHICLE_IDENTIFICATION_RESPONSE, response_payload)
        print("Vehicle Identification Response sent")
    
    def handle_routing_activation_request(self, client_socket: socket.socket, payload_data: bytes):
        """处理路由激活请求"""
        print("Processing Routing Activation Request")
        
        if len(payload_data) >= 4:
            source_address = struct.unpack('>H', payload_data[0:2])[0]
            activation_type = payload_data[2]
            
            print(f"  Source Address: 0x{source_address:04X}")
            print(f"  Activation Type: 0x{activation_type:02X}")
            
            # 构造路由激活响应
            client_logical_address = struct.pack('>H', source_address)
            server_logical_address = struct.pack('>H', self.server_addr)
            response_code = b'\x10'  # 成功激活
            
            response_payload = client_logical_address + server_logical_address + response_code + b'\x00\x00\x00\x00'
            
            self.send_doip_message(client_socket, self.DOIP_ROUTING_ACTIVATION_RESPONSE, response_payload)
            print("Routing Activation Response sent (Success)")
            
            # 标记路由已激活
            for client_info in self.clients.values():
                if client_info['socket'] == client_socket:
                    client_info['routing_activated'] = True
                    break
        else:
            print("Invalid Routing Activation Request payload")
    
    def handle_diagnostic_message(self, client_socket: socket.socket, payload_data: bytes):
        """处理诊断消息"""
        print("Processing Diagnostic Message")
        
        if len(payload_data) >= 4:
            source_address = struct.unpack('>H', payload_data[0:2])[0]
            target_address = struct.unpack('>H', payload_data[2:4])[0]
            user_data = payload_data[4:]
            
            print(f"  Source Address: 0x{source_address:04X}，Target Address: 0x{target_address:04X}， User Data: {user_data.hex().upper()}")

            # 检查目标地址是否匹配物理地址或功能地址
            if target_address == self.server_addr:
                print(f"  Message type: Physical addressing (0x{self.server_addr:04X})")
                address_type = "physical"
            elif target_address == self.server_addr_func:
                print(f"  Message type: Functional addressing (0x{self.server_addr_func:04X})")
                address_type = "functional"
            else:
                print(f"  Warning: Target address 0x{target_address:04X} does not match server addresses")
                print(f"  Expected: 0x{self.server_addr:04X} (physical) or 0x{self.server_addr_func:04X} (functional)")
                address_type = "unknown"
                
            ack_payload = struct.pack('>HHB', source_address, target_address, 0x00)  # 确认码
            self.send_doip_message(client_socket, self.DOIP_DIAGNOSTIC_MESSAGE_ACK, ack_payload)
            
            if user_data:
                response_data = self.generate_diagnostic_response(user_data, address_type)
                if response_data:
                    # 对于功能寻址，响应时使用物理地址作为源地址
                    response_source = self.server_addr
                    response_payload = struct.pack('>HH', response_source, source_address) + response_data
                    self.send_doip_message(client_socket, self.DOIP_DIAGNOSTIC_MESSAGE, response_payload)
                    print(f"Diagnostic Response sent: {response_data.hex().upper()}")
                    print(f"Response source address: 0x{response_source:04X} (physical)")
        else:
            print("Invalid Diagnostic Message payload")
    
    def generate_diagnostic_response(self, request_data: bytes, address_type: str = "physical") -> bytes:
        """生成诊断响应数据"""
        if len(request_data) == 0:
            return None
        
        # 将请求数据转换为十六进制字符串
        request_hex = request_data.hex().upper()
        # print(f"Looking up response for request: {request_hex} (address_type: {address_type})")
        
        # 首先尝试从配置文件中查找完全匹配的响应
        if request_hex in self.response_config:
            response_hex = self.response_config[request_hex]
            print(f"Found configured response: {response_hex}")
            try:
                return bytes.fromhex(response_hex)
            except ValueError as e:
                print(f"Error converting hex response to bytes: {e}")
                return None
        
        # 如果配置文件中没有找到，使用默认的响应生成逻辑
        # print(f"No configured response found, using default logic")
        return self.generate_default_diagnostic_response(request_data, address_type)
    
    def generate_default_diagnostic_response(self, request_data: bytes, address_type: str = "physical") -> bytes:
        """生成默认诊断响应数据（原有逻辑）"""
        service_id = request_data[0]
        
        # 对于功能寻址，某些服务可能不响应或有特殊处理
        if address_type == "functional":
            # 功能寻址通常用于广播类服务，某些服务可能不响应
            if service_id == 0x3E:  # TesterPresent - 功能寻址时通常不响应
                print("TesterPresent with functional addressing - no response")
                return None
            elif service_id == 0x11:  # ECU Reset - 功能寻址时可能有特殊处理
                print("ECU Reset with functional addressing")
                # 可以添加特殊的功能寻址处理逻辑
        elif address_type == "physical":
            if service_id == 0x3E:
                # print("There is no need response for 3E80")
                return None
        
        if service_id == 0x10:  # DiagnosticSessionControl
            return bytes([0x50]) + request_data[1:2] + b'\x00\x32\x01\xF4'
        elif service_id == 0x22:  # ReadDataByIdentifier
            if len(request_data) >= 3:
                did = struct.unpack('>H', request_data[1:3])[0]
                return bytes([0x62]) + request_data[1:3] + b'\x01\x02\x03\x04'  # 示例数据
        elif service_id == 0x27:  # SecurityAccess
            if len(request_data) >= 2:
                level = request_data[1]
                if level % 2 == 1:  # 请求种子
                    return bytes([0x67, level]) + b'\x12\x34\x56\x78\x9A\xBC\xDE\xF0' * 2
                else:  # 发送密钥
                    return bytes([0x67, level])
        elif service_id == 0x3E:  # TesterPresent
            if address_type == "physical":
                return bytes([0x7E])  # 物理寻址时响应
            else:
                return None  # 功能寻址时不响应
        elif service_id == 0x11:  # ECU Reset
            if len(request_data) >= 2:
                reset_type = request_data[1]
                return bytes([0x51, reset_type])
            
        # 处理特定条件的直接响应

        if (request_data[0] == 0x31 and 
            request_data[1] == 0x01 and request_data[2] == 0xDD and request_data[3] == 0x02):
            response = bytes([0x71, 0x01, 0xDD, 0x02, 0x00])
            return response
        
        # 36 服务处理（TransferData）
        if len(request_data) > 0 and request_data[0] == 0x34 and len(request_data) > 1:
            response = bytes([0x74,0x40,0x00,0x00,0x3F,0x02])  # 正响应：76 + 块序列号
            return response
        
        
        # 36 服务处理（TransferData）
        if len(request_data) > 0 and request_data[0] == 0x36 and len(request_data) > 1:
            response = bytes([0x76, request_data[1]])  # 正响应：76 + 块序列号
            return response
        
        # 37 服务处理（RequestTransferExit）
        if len(request_data) > 0 and request_data[0] == 0x37:
            response = bytes([0x77])  # 正响应：77
            return response
        
        if (request_data[0] == 0x31 and 
            request_data[1] == 0x01 and request_data[2] == 0xFF and request_data[3] == 0x00):
            response = bytes([0x71, 0x01, 0xFF, 0x00, 0x00])
            return response
        
        return bytes([0x7F, service_id, 0x11])  # serviceNotSupported
    
    def send_doip_message(self, client_socket: socket.socket, payload_type: int, payload_data: bytes):
        """发送DoIP消息"""
        # 构造DoIP头
        header = struct.pack('>BBHI', 
                           self.DOIP_VERSION, 
                           self.DOIP_INVERSE_VERSION, 
                           payload_type, 
                           len(payload_data))
        
        # 发送消息
        message = header + payload_data
        client_socket.send(message)
        
        # print(f"Sent DoIP message: Type=0x{payload_type:04X}, Length={len(payload_data)}")
    
    def stop_server(self):
        """停止服务器"""
        print("Stopping DoIP server...")
        self.running = False
        
        # 关闭所有客户端连接
        for client_info in self.clients.values():
            try:
                client_info['socket'].close()
            except:
                pass
        self.clients.clear()
        
        # 关闭TCP服务器socket
        if self.tcp_socket:
            try:
                self.tcp_socket.close()
            except:
                pass
        
        # 关闭UDP服务器socket
        if self.udp_socket:
            try:
                self.udp_socket.close()
            except:
                pass
        
        print("DoIP server stopped")

def main():
    """主函数"""
    server = DoIPServer(
        host='127.0.0.1',
        port=13400,
        server_addr=0x0004,
        server_addr_func=0xE400,
        client_addr=0x0E80
    )
    
    try:
        server.start_server()
    except KeyboardInterrupt:
        print("\nReceived interrupt signal")
    finally:
        server.stop_server()

if __name__ == '__main__':
    sys.exit(main())