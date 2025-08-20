
# === app_extended.py ===
"""
Extended Flask App - Integrates web interface with real networking
Author: Assistant
Description: Enhanced version of the original Flask app with real VPN networking
"""

from flask import Flask, render_template, jsonify, request, send_file, abort
from datetime import datetime
import threading
import time
import os
from werkzeug.utils import secure_filename
from vpn_logic import VPNSimulator
from file_manager import FileManager
from logger import setup_logger, log_event
from network_integration import NetworkVPNIntegration

app = Flask(__name__)
app.secret_key = 'vpn_simulator_extended_secret_key'

# File upload configuration
UPLOAD_FOLDER = 'vpn_files'
MAX_FILE_SIZE = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'zip', 'rar', 'mp3', 'mp4', 'avi'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Create directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('downloads', exist_ok=True)

# Initialize components
vpn = VPNSimulator()
file_manager = FileManager(UPLOAD_FOLDER)
network_integration = NetworkVPNIntegration(vpn)
logger = setup_logger()

@app.route('/')
def home():
    """Main dashboard page"""
    return render_template('home_extended.html')

@app.route('/network')
def network():
    """Network VPN page"""
    return render_template('network.html')

# Real Network VPN Routes
@app.route('/network/connect', methods=['POST'])
def network_connect():
    """Connect to real VPN server"""
    try:
        data = request.json
        host = data.get('host', 'localhost')
        port = int(data.get('port', 5000))
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'success': False, 'message': 'Username and password required'})
        
        success = network_integration.connect_to_real_server(host, port, username, password)
        
        if success:
            # Also connect the simulator
            vpn.connect(f"Real Server ({host}:{port})")
            log_event(f"Connected to real VPN server: {host}:{port} as {username}")
            
            return jsonify({
                'success': True,
                'message': f'Connected to real VPN server at {host}:{port}',
                'host': host,
                'port': port,
                'username': username
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to connect to VPN server'})
            
    except Exception as e:
        logger.error(f"Network connection error: {str(e)}")
        return jsonify({'success': False, 'message': f'Connection error: {str(e)}'})

@app.route('/network/disconnect', methods=['POST'])
def network_disconnect():
    """Disconnect from real VPN server"""
    try:
        network_integration.disconnect_from_server()
        vpn.disconnect()
        log_event("Disconnected from real VPN server")
        
        return jsonify({'success': True, 'message': 'Disconnected from VPN server'})
        
    except Exception as e:
        logger.error(f"Network disconnection error: {str(e)}")
        return jsonify({'success': False, 'message': f'Disconnection error: {str(e)}'})

@app.route('/network/status')
def network_status():
    """Get network connection status"""
    try:
        status = network_integration.get_network_status()
        vpn_status = {
            'connected': vpn.is_connected(),
            'server': vpn.current_server,
            'duration': vpn.get_session_duration(),
            'data_usage': vpn.get_data_usage()
        }
        
        return jsonify({
            'network': status,
            'simulator': vpn_status
        })
        
    except Exception as e:
        logger.error(f"Network status error: {str(e)}")
        return jsonify({'error': 'Status unavailable'})

@app.route('/network/send_message', methods=['POST'])
def network_send_message():
    """Send message through real VPN"""
    try:
        data = request.json
        message = data.get('message')
        
        if not message:
            return jsonify({'success': False, 'message': 'No message provided'})
        
        success = network_integration.send_message_to_server(message)
        
        if success:
            log_event(f"Message sent through VPN: {message[:50]}...")
            return jsonify({'success': True, 'message': 'Message sent successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to send message'})
            
    except Exception as e:
        logger.error(f"Message send error: {str(e)}")
        return jsonify({'success': False, 'message': f'Send error: {str(e)}'})

@app.route('/network/upload_file', methods=['POST'])
def network_upload_file():
    """Upload file through real VPN"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file selected'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            temp_path = os.path.join('temp', filename)
            
            # Create temp directory
            os.makedirs('temp', exist_ok=True)
            
            # Save file temporarily
            file.save(temp_path)
            
            # Upload through network
            success = network_integration.upload_file_to_server(temp_path)
            
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            if success:
                log_event(f"File uploaded through VPN: {filename}")
                return jsonify({'success': True, 'message': f'File "{filename}" uploaded to VPN server'})
            else:
                return jsonify({'success': False, 'error': 'Failed to upload file to VPN server'})
        else:
            return jsonify({'success': False, 'error': 'File type not allowed'})
            
    except Exception as e:
        logger.error(f"Network upload error: {str(e)}")
        return jsonify({'success': False, 'error': f'Upload error: {str(e)}'})

# Keep all existing routes from original app.py
@app.route('/connect', methods=['POST'])
def connect():
    """Handle VPN connection request (simulator)"""
    try:
        server = request.json.get('server', 'USA')
        
        if vpn.is_connected():
            return jsonify({'success': False, 'message': 'Already connected'})
        
        success = vpn.connect(server)
        
        if success:
            log_event(f"Connected to {server}")
            return jsonify({
                'success': True, 
                'message': f'Connected to {server}',
                'server': server
            })
        else:
            return jsonify({'success': False, 'message': 'Connection failed'})
            
    except Exception as e:
        logger.error(f"Connection error: {str(e)}")
        return jsonify({'success': False, 'message': 'Connection error'})

@app.route('/disconnect', methods=['POST'])
def disconnect():
    """Handle VPN disconnection request (simulator)"""
    try:
        if not vpn.is_connected():
            return jsonify({'success': False, 'message': 'Not connected'})
        
        duration = vpn.get_session_duration()
        data_used = vpn.get_data_usage()
        server = vpn.current_server
        
        vpn.disconnect()
        log_event(f"Disconnected from {server} - Duration: {duration}s, Data: {data_used:.2f}MB")
        
        return jsonify({
            'success': True,
            'message': 'Disconnected',
            'session_stats': {
                'duration': duration,
                'data_used': data_used,
                'server': server
            }
        })
        
    except Exception as e:
        logger.error(f"Disconnection error: {str(e)}")
        return jsonify({'success': False, 'message': 'Disconnection error'})

@app.route('/status')
def status():
    """Get current VPN status"""
    try:
        return jsonify({
            'connected': vpn.is_connected(),
            'server': vpn.current_server,
            'duration': vpn.get_session_duration(),
            'data_usage': vpn.get_data_usage(),
            'start_time': vpn.start_time.isoformat() if vpn.start_time else None
        })
    except Exception as e:
        logger.error(f"Status error: {str(e)}")
        return jsonify({'error': 'Status unavailable'})

@app.route('/files')
def files():
    """File sharing dashboard"""
    return render_template('files.html')

@app.route('/logs')
def logs():
    """View session logs page"""
    return render_template('logs.html')

@app.route('/api/logs')
def api_logs():
    """Get logs as JSON for AJAX"""
    try:
        with open('vpn_simulator.log', 'r') as f:
            logs = f.readlines()
        return jsonify({'logs': logs[-100:]})
    except Exception as e:
        return jsonify({'logs': [], 'error': 'Could not read logs'})

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

if __name__ == '__main__':
    print(" Starting Extended VPN Client Simulator...")
    print(" Web interface: http://localhost:5000")
    print(" Network VPN: http://localhost:5000/network")
    app.run(debug=True, host='0.0.0.0', port=5000)