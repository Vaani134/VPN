# === client.py ===
"""
VPN Client - Connects to VPN server with encryption
Author: Assistant
Description: Real VPN client that connects to the server and handles secure communication
"""

import socket
import json
import base64
import os
import threading
import time
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class VPNClient:
    def __init__(self):
        self.socket = None
        self.cipher = None
        self.connected = False
        self.username = None
        self.server_host = None
        self.server_port = None
        self.running = False
    
    def generate_key(self, password: str, salt: bytes) -> bytes:
        """Generate encryption key from password and salt"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def connect_to_server(self, host, port, username, password):
        """Connect to VPN server"""
        try:
            print(f"🔗 Connecting to VPN server at {host}:{port}...")
            
            # Create socket and connect
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            
            # Send authentication
            auth_request = {
                'username': username,
                'password': password
            }
            self.socket.send(json.dumps(auth_request).encode())
            
            # Receive authentication response
            response_data = self.socket.recv(1024)
            response = json.loads(response_data.decode())
            
            if response.get('status') == 'success':
                # Generate encryption key
                salt = base64.b64decode(response['salt'])
                key = self.generate_key(password, salt)
                self.cipher = Fernet(key)
                
                self.connected = True
                self.username = username
                self.server_host = host
                self.server_port = port
                
                print(f"✅ Connected to VPN server as '{username}'")
                print(f"🔐 Secure encrypted tunnel established")
                
                # Start receiving messages
                self.running = True
                receive_thread = threading.Thread(target=self.receive_messages)
                receive_thread.daemon = True
                receive_thread.start()
                
                return True
            else:
                print(f"❌ Authentication failed: {response.get('message')}")
                self.socket.close()
                return False
                
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def receive_messages(self):
        """Receive and process messages from server"""
        while self.running and self.connected:
            try:
                encrypted_data = self.socket.recv(4096)
                if not encrypted_data:
                    break
                
                # Decrypt message
                decrypted_data = self.cipher.decrypt(encrypted_data)
                message = json.loads(decrypted_data.decode())
                
                self.process_server_message(message)
                
            except socket.timeout:
                continue
            except Exception as e:
                print(f"❌ Error receiving message: {e}")
                break
        
        self.disconnect()
    
    def process_server_message(self, message):
        """Process messages received from server"""
        msg_type = message.get('type')
        
        if msg_type == 'welcome':
            print(f"📧 Server: {message.get('message')}")
        
        elif msg_type == 'pong':
            print(f"🏓 Pong received - Server is alive")
        
        elif msg_type == 'text_response':
            print(f"📧 Server: {message.get('message')}")
        
        elif msg_type == 'file_upload_success':
            print(f"📤 File upload successful: {message.get('message')}")
        
        elif msg_type == 'file_list_response':
            self.display_file_list(message.get('files', []))
        
        elif msg_type == 'file_download_response':
            self.handle_file_download(message)
        
        elif msg_type == 'server_info_response':
            self.display_server_info(message)
        
        elif msg_type == 'error':
            print(f"❌ Server error: {message.get('message')}")
        
        else:
            print(f"📧 Unknown message: {message}")
    
    def send_message(self, message):
        """Send encrypted message to server"""
        try:
            if not self.connected:
                print("❌ Not connected to server")
                return False
            
            json_data = json.dumps(message)
            encrypted_data = self.cipher.encrypt(json_data.encode())
            self.socket.send(encrypted_data)
            return True
            
        except Exception as e:
            print(f"❌ Error sending message: {e}")
            return False
    
    def send_text_message(self, content):
        """Send text message to server"""
        message = {
            'type': 'text_message',
            'content': content,
            'timestamp': datetime.now().isoformat()
        }
        return self.send_message(message)
    
    def send_ping(self):
        """Send ping to server"""
        message = {
            'type': 'ping',
            'timestamp': datetime.now().isoformat()
        }
        return self.send_message(message)
    
    def upload_file(self, file_path):
        """Upload file to server"""
        try:
            if not os.path.exists(file_path):
                print(f"❌ File not found: {file_path}")
                return False
            
            filename = os.path.basename(file_path)
            
            # Read file and encode
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            file_data_b64 = base64.b64encode(file_data).decode()
            
            message = {
                'type': 'file_upload',
                'filename': filename,
                'data': file_data_b64,
                'size': len(file_data),
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"📤 Uploading file: {filename} ({len(file_data)} bytes)")
            return self.send_message(message)
            
        except Exception as e:
            print(f"❌ File upload error: {e}")
            return False
    
    def request_file_list(self):
        """Request list of files from server"""
        message = {
            'type': 'file_list',
            'timestamp': datetime.now().isoformat()
        }
        return self.send_message(message)
    
    def download_file(self, filename, save_path=None):
        """Download file from server"""
        if save_path is None:
            save_path = f"downloaded_{filename}"
        
        self.download_save_path = save_path
        
        message = {
            'type': 'file_download',
            'filename': filename,
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"📥 Requesting file: {filename}")
        return self.send_message(message)
    
    def handle_file_download(self, message):
        """Handle file download response"""
        try:
            filename = message.get('filename')
            file_data_b64 = message.get('data')
            file_size = message.get('size')
            
            # Decode file data
            file_data = base64.b64decode(file_data_b64)
            
            # Save file
            save_path = getattr(self, 'download_save_path', f"downloaded_{filename}")
            with open(save_path, 'wb') as f:
                f.write(file_data)
            
            print(f"📥 File downloaded: {save_path} ({file_size} bytes)")
            
        except Exception as e:
            print(f"❌ File download error: {e}")
    
    def display_file_list(self, files):
        """Display list of server files"""
        print("\n📁 Server Files:")
        print("-" * 50)
        
        if not files:
            print("No files on server")
        else:
            for file_info in files:
                filename = file_info.get('filename')
                size = file_info.get('size')
                modified = file_info.get('modified', 'Unknown')
                print(f"📄 {filename} ({size} bytes) - Modified: {modified}")
        
        print("-" * 50)
    
    def request_server_info(self):
        """Request server information"""
        message = {
            'type': 'server_info',
            'timestamp': datetime.now().isoformat()
        }
        return self.send_message(message)
    
    def display_server_info(self, info):
        """Display server information"""
        print(f"\n🖥️  Server Information:")
        print(f"   Name: {info.get('server_name')}")
        print(f"   Version: {info.get('version')}")
        print(f"   Connected Clients: {info.get('connected_clients')}")
        print(f"   Connected Users: {', '.join(info.get('connected_users', []))}")
        print(f"   Max Clients: {info.get('max_clients')}")
    
    def disconnect(self):
        """Disconnect from server"""
        self.running = False
        self.connected = False
        
        if self.socket:
            self.socket.close()
        
        print("🔌 Disconnected from VPN server")

def main():
    """Main client function"""
    print("🔐 VPN Client - Starting...")
    
    client = VPNClient()
    
    # Get connection details
    print("\n📡 VPN Connection Setup")
    host = input("Server IP/hostname (default: localhost): ").strip() or 'localhost'
    port = input("Server port (default: 5000): ").strip() or '5000'
    port = int(port)
    
    username = input("Username: ").strip()
    password = input("Password: ").strip()
    
    # Connect to server
    if client.connect_to_server(host, port, username, password):
        print("\n🎯 VPN Client Connected!")
        print("Available commands:")
        print("  'ping' - Send ping to server")
        print("  'msg <text>' - Send text message")
        print("  'upload <file_path>' - Upload file")
        print("  'files' - List server files")
        print("  'download <filename>' - Download file")
        print("  'info' - Get server info")
        print("  'quit' - Disconnect and exit")
        print("-" * 50)
        
        # Command loop
        try:
            while client.connected:
                command = input(f"[{username}@VPN] ").strip()
                
                if command == 'quit':
                    break
                elif command == 'ping':
                    client.send_ping()
                elif command.startswith('msg '):
                    message = command[4:]
                    client.send_text_message(message)
                elif command.startswith('upload '):
                    file_path = command[7:]
                    client.upload_file(file_path)
                elif command == 'files':
                    client.request_file_list()
                elif command.startswith('download '):
                    filename = command[9:]
                    client.download_file(filename)
                elif command == 'info':
                    client.request_server_info()
                elif command == 'help':
                    print("Available commands: ping, msg, upload, files, download, info, quit")
                else:
                    print("Unknown command. Type 'help' for available commands.")
                    
                time.sleep(0.1)  # Small delay
        
        except KeyboardInterrupt:
            print("\n🛑 Interrupted by user")
        
        finally:
            client.disconnect()
    
    else:
        print("❌ Failed to connect to VPN server")

if __name__ == "__main__":
    main()
