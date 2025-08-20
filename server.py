
# === server.py ===
"""
VPN Server - Handles multiple client connections with encryption
Author: Assistant
Description: Real VPN server that accepts client connections and handles secure communication==================================================
"""

import socket
import threading
import json
import os
import base64
import hashlib
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from loguru import logger
import time

class VPNServer:
    def __init__(self, host='0.0.0.0', port=5000):
        self.host = host
        self.port = port
        self.socket = None
        self.clients = {}  # {client_id: {'socket': socket, 'username': str, 'cipher': Fernet}}
        self.users = {  # Simple user database
            'admin': 'admin123',
            'user1': 'password123',
            'user2': 'mypassword',
            'guest': 'guest123'
        }
        self.running = False
        self.client_counter = 0
        
        # Setup logging
        logger.add("vpn_server.log", rotation="10 MB", retention="1 week")
        
        # Create server files directory
        os.makedirs('server_files', exist_ok=True)
    
    def generate_key(self, password: str, salt: bytes = None) -> bytes:
        """Generate encryption key from password"""
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key, salt
    
    def start_server(self):
        """Start the VPN server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.listen(5)
            self.running = True
            
            logger.info(f" VPN Server started on {self.host}:{self.port}")
            print(f" VPN Server listening on {self.host}:{self.port}")
            print(f" Server files directory: ./server_files/")
            print(f" Registered users: {list(self.users.keys())}")
            print("="*50)
            
            while self.running:
                try:
                    client_socket, address = self.socket.accept()
                    self.client_counter += 1
                    client_id = f"client_{self.client_counter}"
                    
                    logger.info(f"New connection from {address} (ID: {client_id})")
                    print(f"🔗 New connection: {address} (ID: {client_id})")
                    
                    # Handle client in separate thread
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, address, client_id)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                except socket.error as e:
                    if self.running:
                        logger.error(f"Socket error: {e}")
                        
        except Exception as e:
            logger.error(f"Server start error: {e}")
            print(f" Server error: {e}")
    
    def handle_client(self, client_socket, address, client_id):
        """Handle individual client connection"""
        try:
            # Authentication phase
            auth_success, username, cipher = self.authenticate_client(client_socket)
            
            if not auth_success:
                logger.warning(f"Authentication failed for {address}")
                client_socket.close()
                return
            
            # Store client info
            self.clients[client_id] = {
                'socket': client_socket,
                'username': username,
                'cipher': cipher,
                'address': address,
                'connected_at': datetime.now()
            }
            
            logger.info(f"User '{username}' authenticated successfully from {address}")
            print(f" User '{username}' connected from {address}")
            
            # Send welcome message
            welcome_msg = {
                'type': 'welcome',
                'message': f'Welcome to VPN Server, {username}!',
                'server_time': datetime.now().isoformat(),
                'client_id': client_id
            }
            self.send_encrypted_message(client_socket, cipher, welcome_msg)
            
            # Handle client messages
            while self.running:
                try:
                    # Receive encrypted message
                    encrypted_data = client_socket.recv(4096)
                    if not encrypted_data:
                        break
                    
                    # Decrypt and process message
                    decrypted_data = cipher.decrypt(encrypted_data)
                    message = json.loads(decrypted_data.decode())
                    
                    logger.info(f"Message from {username}: {message.get('type', 'unknown')}")
                    self.process_client_message(client_socket, cipher, username, message)
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"Error handling message from {username}: {e}")
                    break
        
        except Exception as e:
            logger.error(f"Client handling error: {e}")
        
        finally:
            # Cleanup
            if client_id in self.clients:
                del self.clients[client_id]
            client_socket.close()
            logger.info(f"Client {username} ({address}) disconnected")
            print(f"🔌 User '{username}' disconnected from {address}")
    
    def authenticate_client(self, client_socket):
        """Authenticate client with username/password"""
        try:
            # Set timeout for authentication
            client_socket.settimeout(30)
            
            # Receive authentication request
            auth_data = client_socket.recv(1024)
            auth_request = json.loads(auth_data.decode())
            
            username = auth_request.get('username')
            password = auth_request.get('password')
            
            # Verify credentials
            if username in self.users and self.users[username] == password:
                # Generate encryption key from password
                key, salt = self.generate_key(password)
                cipher = Fernet(key)
                
                # Send success response with salt
                response = {
                    'status': 'success',
                    'message': 'Authentication successful',
                    'salt': base64.b64encode(salt).decode()
                }
                client_socket.send(json.dumps(response).encode())
                
                # Set normal timeout
                client_socket.settimeout(60)
                
                return True, username, cipher
            else:
                # Send failure response
                response = {
                    'status': 'failed',
                    'message': 'Invalid username or password'
                }
                client_socket.send(json.dumps(response).encode())
                return False, None, None
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False, None, None
    
    def process_client_message(self, client_socket, cipher, username, message):
        """Process different types of client messages"""
        msg_type = message.get('type')
        
        if msg_type == 'ping':
            # Respond to ping
            response = {
                'type': 'pong',
                'timestamp': datetime.now().isoformat(),
                'server_status': 'online'
            }
            self.send_encrypted_message(client_socket, cipher, response)
        
        elif msg_type == 'text_message':
            # Echo text message
            response = {
                'type': 'text_response',
                'message': f"Server received: {message.get('content', '')}",
                'timestamp': datetime.now().isoformat()
            }
            self.send_encrypted_message(client_socket, cipher, response)
            logger.info(f"Text message from {username}: {message.get('content', '')}")
        
        elif msg_type == 'file_upload':
            # Handle file upload
            self.handle_file_upload(client_socket, cipher, username, message)
        
        elif msg_type == 'file_list':
            # Send list of server files
            self.send_file_list(client_socket, cipher, username)
        
        elif msg_type == 'file_download':
            # Handle file download request
            self.handle_file_download(client_socket, cipher, username, message)
        
        elif msg_type == 'server_info':
            # Send server information
            self.send_server_info(client_socket, cipher)
        
        else:
            # Unknown message type
            response = {
                'type': 'error',
                'message': f"Unknown message type: {msg_type}"
            }
            self.send_encrypted_message(client_socket, cipher, response)
    
    def handle_file_upload(self, client_socket, cipher, username, message):
        """Handle file upload from client"""
        try:
            filename = message.get('filename')
            file_data = message.get('data')  # Base64 encoded
            
            if not filename or not file_data:
                response = {'type': 'error', 'message': 'Invalid file data'}
                self.send_encrypted_message(client_socket, cipher, response)
                return
            
            # Decode file data
            file_bytes = base64.b64decode(file_data)
            
            # Save file with username prefix
            safe_filename = f"{username}_{filename}"
            file_path = os.path.join('server_files', safe_filename)
            
            with open(file_path, 'wb') as f:
                f.write(file_bytes)
            
            file_size = len(file_bytes)
            logger.info(f"File uploaded by {username}: {filename} ({file_size} bytes)")
            
            response = {
                'type': 'file_upload_success',
                'message': f'File "{filename}" uploaded successfully',
                'filename': safe_filename,
                'size': file_size
            }
            self.send_encrypted_message(client_socket, cipher, response)
            
        except Exception as e:
            logger.error(f"File upload error: {e}")
            response = {'type': 'error', 'message': f'File upload failed: {str(e)}'}
            self.send_encrypted_message(client_socket, cipher, response)
    
    def send_file_list(self, client_socket, cipher, username):
        """Send list of files on server"""
        try:
            files = []
            server_files_dir = 'server_files'
            
            if os.path.exists(server_files_dir):
                for filename in os.listdir(server_files_dir):
                    file_path = os.path.join(server_files_dir, filename)
                    if os.path.isfile(file_path):
                        file_stats = os.stat(file_path)
                        files.append({
                            'filename': filename,
                            'size': file_stats.st_size,
                            'modified': datetime.fromtimestamp(file_stats.st_mtime).isoformat()
                        })
            
            response = {
                'type': 'file_list_response',
                'files': files,
                'total_files': len(files)
            }
            self.send_encrypted_message(client_socket, cipher, response)
            
        except Exception as e:
            logger.error(f"File list error: {e}")
            response = {'type': 'error', 'message': f'Could not get file list: {str(e)}'}
            self.send_encrypted_message(client_socket, cipher, response)
    
    def handle_file_download(self, client_socket, cipher, username, message):
        """Handle file download request"""
        try:
            filename = message.get('filename')
            
            if not filename:
                response = {'type': 'error', 'message': 'No filename specified'}
                self.send_encrypted_message(client_socket, cipher, response)
                return
            
            file_path = os.path.join('server_files', filename)
            
            if not os.path.exists(file_path):
                response = {'type': 'error', 'message': 'File not found'}
                self.send_encrypted_message(client_socket, cipher, response)
                return
            
            # Read file and encode
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            file_data_b64 = base64.b64encode(file_data).decode()
            
            response = {
                'type': 'file_download_response',
                'filename': filename,
                'data': file_data_b64,
                'size': len(file_data)
            }
            self.send_encrypted_message(client_socket, cipher, response)
            
            logger.info(f"File downloaded by {username}: {filename} ({len(file_data)} bytes)")
            
        except Exception as e:
            logger.error(f"File download error: {e}")
            response = {'type': 'error', 'message': f'File download failed: {str(e)}'}
            self.send_encrypted_message(client_socket, cipher, response)
    
    def send_server_info(self, client_socket, cipher):
        """Send server information"""
        try:
            connected_users = [client['username'] for client in self.clients.values()]
            
            info = {
                'type': 'server_info_response',
                'server_name': 'VPN Simulator Server',
                'version': '1.0.0',
                'uptime': str(datetime.now() - datetime.now()),  # Simplified
                'connected_clients': len(self.clients),
                'connected_users': connected_users,
                'max_clients': 50
            }
            self.send_encrypted_message(client_socket, cipher, info)
            
        except Exception as e:
            logger.error(f"Server info error: {e}")
    
    def send_encrypted_message(self, client_socket, cipher, message):
        """Send encrypted message to client"""
        try:
            json_data = json.dumps(message)
            encrypted_data = cipher.encrypt(json_data.encode())
            client_socket.send(encrypted_data)
        except Exception as e:
            logger.error(f"Send message error: {e}")
    
    def stop_server(self):
        """Stop the VPN server"""
        self.running = False
        if self.socket:
            self.socket.close()
        logger.info("VPN Server stopped")

def main():
    """Main server function"""
    print(" VPN Server - Starting...")
    print("Press Ctrl+C to stop the server")
    
    server = VPNServer()
    
    try:
        server.start_server()
    except KeyboardInterrupt:
        print("\n Shutting down server...")
        server.stop_server()
    except Exception as e:
        print(f" Server error: {e}")
        logger.error(f"Server error: {e}")

if __name__ == "__main__":
    main()
