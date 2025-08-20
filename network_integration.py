# === network_integration.py ===
"""
Network Integration Module - Bridges web app with real VPN networking
Author: Assistant
Description: Integrates the existing Flask web app with real networking capabilities
"""

import threading
import time
from client import VPNClient
from loguru import logger

class NetworkVPNIntegration:
    """Integrates web VPN simulator with real networking"""
    
    def __init__(self, vpn_simulator):
        self.vpn_simulator = vpn_simulator
        self.network_client = VPNClient()
        self.network_connected = False
        self.integration_active = False
        
    def connect_to_real_server(self, host, port, username, password):
        """Connect to real VPN server"""
        try:
            success = self.network_client.connect_to_server(host, port, username, password)
            
            if success:
                self.network_connected = True
                self.integration_active = True
                
                # Start integration thread
                integration_thread = threading.Thread(target=self.sync_with_simulator)
                integration_thread.daemon = True
                integration_thread.start()
                
                logger.info(f"Network integration active - connected to {host}:{port}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Network integration error: {e}")
            return False
    
    def sync_with_simulator(self):
        """Sync web simulator with real network connection"""
        while self.integration_active and self.network_connected:
            try:
                # If web simulator shows connected but network is not, sync it
                if self.vpn_simulator.is_connected() and not self.network_connected:
                    self.vpn_simulator.disconnect()
                
                # Send periodic pings to maintain connection
                if self.network_connected:
                    self.network_client.send_ping()
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Sync error: {e}")
                break
    
    def upload_file_to_server(self, file_path):
        """Upload file through real network connection"""
        if self.network_connected:
            return self.network_client.upload_file(file_path)
        return False
    
    def download_file_from_server(self, filename, save_path=None):
        """Download file through real network connection"""
        if self.network_connected:
            return self.network_client.download_file(filename, save_path)
        return False
    
    def send_message_to_server(self, message):
        """Send message through real network connection"""
        if self.network_connected:
            return self.network_client.send_text_message(message)
        return False
    
    def disconnect_from_server(self):
        """Disconnect from real VPN server"""
        self.integration_active = False
        self.network_connected = False
        
        if self.network_client:
            self.network_client.disconnect()
        
        logger.info("Network integration disconnected")
    
    def get_network_status(self):
        """Get network connection status"""
        return {
            'network_connected': self.network_connected,
            'integration_active': self.integration_active,
            'server_host': getattr(self.network_client, 'server_host', None),
            'server_port': getattr(self.network_client, 'server_port', None),
            'username': getattr(self.network_client, 'username', None)
        }
