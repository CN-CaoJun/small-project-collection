import socket
import threading
import struct
import time
import json
import os
from typing import Dict, Tuple

class DoIPServer:
    def __init__(self, host='127.0.0.1', port=13400, server_addr=0x1001, client_addr=0x0E80):
        self.host = host
        self.port = port
        self.server_addr = server_addr
        self.client_addr = client_addr
        self.socket = None
        self.running = False
        self.clients = {}  # 存储连接的客户端
        
        # 加载响应配置
        self.response_config = self.load_response_config()
        
        # DoIP消息类型定义
        self.DOIP_HEADER_SIZE = 8
        self.DOIP_VERSION = 0x02
        self.DOIP_INVERSE_VERSION = 0xFD
        
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
        config_path = os.path.join(os.path.dirname(__file__), 'config_json', 'R_ZCU_response.json')
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
        """启动DoIP服务器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.listen(5)
            self.running = True
            
            print(f"DoIP Server started on {self.host}:{self.port}")
            print(f"Server Address: 0x{self.server_addr:04X}")
            print(f"Expected Client Address: 0x{self.client_addr:04X}")
            print("Waiting for connections...")
            
            while self.running:
                try:
                    client_socket, client_address = self.socket.accept()
                    print(f"New connection from {client_address}")
                    
                    # 为每个客户端创建处理线程
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, client_address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                except socket.error as e:
                    if self.running:
                        print(f"Socket error: {e}")
                    break
                    
        except Exception as e:
            print(f"Server error: {e}")
        finally:
            self.stop_server()
    
    def handle_client(self, client_socket: socket.socket, client_address: Tuple[str, int]):
        """处理客户端连接"""
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
                
                print(f"Received DoIP message:")
                print(f"  Version: 0x{version:02X}")
                print(f"  Inverse Version: 0x{inv_version:02X}")
                print(f"  Payload Type: 0x{payload_type:04X}")
                print(f"  Payload Length: {payload_length}")
                
                # 接收载荷数据
                payload_data = b''
                if payload_length > 0:
                    payload_data = self.receive_exact(client_socket, payload_length)
                    if not payload_data:
                        break
                
                # 处理不同类型的DoIP消息
                self.process_doip_message(client_socket, payload_type, payload_data)
                
        except Exception as e:
            print(f"Client {client_id} error: {e}")
        finally:
            print(f"Client {client_id} disconnected")
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
    
    def process_doip_message(self, client_socket: socket.socket, payload_type: int, payload_data: bytes):
        """处理DoIP消息"""
        if payload_type == self.DOIP_VEHICLE_IDENTIFICATION_REQUEST:
            self.handle_vehicle_identification_request(client_socket, payload_data)
        elif payload_type == self.DOIP_ROUTING_ACTIVATION_REQUEST:
            self.handle_routing_activation_request(client_socket, payload_data)
        elif payload_type == self.DOIP_DIAGNOSTIC_MESSAGE:
            self.handle_diagnostic_message(client_socket, payload_data)
        else:
            print(f"Unknown DoIP message type: 0x{payload_type:04X}")
    
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
            
            print(f"  Source Address: 0x{source_address:04X}")
            print(f"  Target Address: 0x{target_address:04X}")
            print(f"  User Data: {user_data.hex().upper()}")
            
            # 发送诊断消息确认
            ack_payload = struct.pack('>HHB', source_address, target_address, 0x00)  # 确认码
            self.send_doip_message(client_socket, self.DOIP_DIAGNOSTIC_MESSAGE_ACK, ack_payload)
            
            # 生成诊断响应
            if user_data:
                response_data = self.generate_diagnostic_response(user_data)
                if response_data:
                    # 发送诊断响应消息
                    response_payload = struct.pack('>HH', target_address, source_address) + response_data
                    self.send_doip_message(client_socket, self.DOIP_DIAGNOSTIC_MESSAGE, response_payload)
                    print(f"Diagnostic Response sent: {response_data.hex().upper()}")
        else:
            print("Invalid Diagnostic Message payload")
    
    def generate_diagnostic_response(self, request_data: bytes) -> bytes:
        """生成诊断响应数据"""
        if len(request_data) == 0:
            return None
        
        # 将请求数据转换为十六进制字符串
        request_hex = request_data.hex().upper()
        print(f"Looking up response for request: {request_hex}")
        
        # 首先尝试从配置文件中查找完全匹配的响应
        if request_hex in self.response_config:
            response_hex = self.response_config[request_hex]
            print(f"Found configured response: {response_hex}")
            try:
                return bytes.fromhex(response_hex)
            except ValueError as e:
                print(f"Error converting hex response to bytes: {e}")
                return None
        
        # 如果没有找到完全匹配，尝试部分匹配（例如，只匹配服务ID）
        service_id = request_data[0]
        service_hex = f"{service_id:02X}"
        
        # 查找以相同服务ID开头的配置
        for req_pattern, res_hex in self.response_config.items():
            if req_pattern.startswith(service_hex):
                # 检查请求长度是否匹配
                if len(req_pattern) == len(request_hex):
                    print(f"Found partial match for service 0x{service_hex}: {res_hex}")
                    try:
                        return bytes.fromhex(res_hex)
                    except ValueError as e:
                        print(f"Error converting hex response to bytes: {e}")
                        continue
        
        # 如果配置文件中没有找到，使用默认的响应生成逻辑
        print(f"No configured response found, using default logic")
        return self.generate_default_diagnostic_response(request_data)
    
    def generate_default_diagnostic_response(self, request_data: bytes) -> bytes:
        """生成默认诊断响应数据（原有逻辑）"""
        service_id = request_data[0]
        
        # 模拟一些基础的UDS服务响应
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
            return bytes([0x7E]) + request_data[1:]
        
        # 默认返回否定响应
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
        
        print(f"Sent DoIP message: Type=0x{payload_type:04X}, Length={len(payload_data)}")
    
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
        
        # 关闭服务器socket
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        
        print("DoIP server stopped")

def main():
    """主函数"""
    server = DoIPServer(
        host='127.0.0.1',
        port=13400,
        server_addr=0x1001,
        client_addr=0x0E80
    )
    
    try:
        server.start_server()
    except KeyboardInterrupt:
        print("\nReceived interrupt signal")
    finally:
        server.stop_server()

if __name__ == '__main__':
    main()