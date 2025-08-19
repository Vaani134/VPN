
# === vpn_logic.py ===
"""
VPN Logic Module - Handles all VPN simulation functionality
"""

import random
import time
from datetime import datetime
from threading import Thread, Lock
import threading

class VPNSimulator:
    """Simulates VPN connection logic and monitoring"""
    
    def __init__(self):
        self.connected = False
        self.current_server = None
        self.start_time = None
        self.data_usage = 0.0  # In MB
        self.lock = Lock()
        self.data_thread = None
        self.running = False
        
        # Available servers
        self.servers = [
            'USA - New York',
            'USA - Los Angeles', 
            'Germany - Berlin',
            'Singapore - Central',
            'UK - London',
            'Canada - Toronto',
            'Japan - Tokyo',
            'Australia - Sydney'
        ]
    
    def connect(self, server):
        """Simulate VPN connection"""
        with self.lock:
            if self.connected:
                return False
            
            # Simulate connection delay
            time.sleep(random.uniform(0.5, 2.0))
            
            self.connected = True
            self.current_server = server
            self.start_time = datetime.now()
            self.data_usage = 0.0
            self.running = True
            
            # Start data usage simulation thread
            self.data_thread = Thread(target=self._simulate_data_usage, daemon=True)
            self.data_thread.start()
            
            return True
    
    def disconnect(self):
        """Simulate VPN disconnection"""
        with self.lock:
            if not self.connected:
                return False
            
            self.connected = False
            self.running = False
            self.current_server = None
            
            # Stop data simulation thread
            if self.data_thread and self.data_thread.is_alive():
                self.data_thread.join(timeout=1.0)
            
            return True
    
    def is_connected(self):
        """Check if VPN is connected"""
        return self.connected
    
    def get_session_duration(self):
        """Get current session duration in seconds"""
        if not self.connected or not self.start_time:
            return 0
        
        return int((datetime.now() - self.start_time).total_seconds())
    
    def get_data_usage(self):
        """Get current data usage in MB"""
        return round(self.data_usage, 2)
    
    def _simulate_data_usage(self):
        """Simulate increasing data usage while connected"""
        while self.running and self.connected:
            # Simulate data usage increase (0.1 to 2.0 MB per second)
            usage_increment = random.uniform(0.1, 2.0)
            
            with self.lock:
                self.data_usage += usage_increment
            
            time.sleep(1)  # Update every second
    
    def get_available_servers(self):
        """Get list of available servers"""
        return self.servers

