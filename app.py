# === app.py ===
"""
VPN Client Simulator - Main Flask Application
Author: Assistant
Description: A web-based VPN simulator with real-time monitoring and logging
"""

from flask import Flask, render_template, jsonify, request, redirect, url_for, send_file, abort
from datetime import datetime
import threading
import time
import os
from werkzeug.utils import secure_filename
from vpn_logic import VPNSimulator
from file_manager import FileManager
from logger import setup_logger, log_event

app = Flask(__name__)
app.secret_key = 'vpn_simulator_secret_key'

# File upload configuration
UPLOAD_FOLDER = 'vpn_files'
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'zip', 'rar', 'mp3', 'mp4', 'avi'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Create upload directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize VPN simulator, file manager, and logger
vpn = VPNSimulator()
file_manager = FileManager(UPLOAD_FOLDER)
logger = setup_logger()

@app.route('/')
def home():
    """Main dashboard page"""
    return render_template('home.html')

@app.route('/connect', methods=['POST'])
def connect():
    """Handle VPN connection request"""
    try:
        server = request.json.get('server', 'USA')
        
        if vpn.is_connected():
            return jsonify({'success': False, 'message': 'Already connected'})
        
        # Start VPN connection
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
    """Handle VPN disconnection request"""
    try:
        if not vpn.is_connected():
            return jsonify({'success': False, 'message': 'Not connected'})
        
        # Get session stats before disconnecting
        duration = vpn.get_session_duration()
        data_used = vpn.get_data_usage()
        server = vpn.current_server
        
        # Disconnect
        vpn.disconnect()
        
        # Log the session
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
    """Get current VPN status (for AJAX updates)"""
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
        
        # Return last 100 log entries
        return jsonify({'logs': logs[-100:]})
    except Exception as e:
        return jsonify({'logs': [], 'error': 'Could not read logs'})

# File Sharing Routes
@app.route('/files')
def files():
    """File sharing dashboard"""
    return render_template('files.html')

@app.route('/api/files')
def api_files():
    """Get list of shared files"""
    try:
        files = file_manager.get_file_list()
        return jsonify({'success': True, 'files': files})
    except Exception as e:
        logger.error(f"Error getting file list: {str(e)}")
        return jsonify({'success': False, 'error': 'Could not retrieve files'})

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload"""
    try:
        # Check if VPN is connected
        if not vpn.is_connected():
            return jsonify({'success': False, 'error': 'VPN must be connected to share files'})
        
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file selected'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            
            # Check if file already exists
            if file_manager.file_exists(filename):
                # Add timestamp to filename to make it unique
                name, ext = os.path.splitext(filename)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{name}_{timestamp}{ext}"
            
            # Save file and get metadata
            file_info = file_manager.save_file(file, filename)
            
            if file_info:
                log_event(f"File uploaded: {filename} ({file_info['size_mb']} MB) via {vpn.current_server}")
                return jsonify({
                    'success': True, 
                    'message': f'File "{filename}" uploaded successfully',
                    'file_info': file_info
                })
            else:
                return jsonify({'success': False, 'error': 'File upload failed'})
        else:
            return jsonify({'success': False, 'error': 'File type not allowed'})
            
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({'success': False, 'error': 'Upload failed'})

@app.route('/download/<filename>')
def download_file(filename):
    """Handle file download"""
    try:
        # Check if VPN is connected
        if not vpn.is_connected():
            abort(403, description="VPN must be connected to download files")
        
        # Sanitize filename
        filename = secure_filename(filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        if not os.path.exists(file_path):
            abort(404, description="File not found")
        
        # Log download
        file_info = file_manager.get_file_info(filename)
        log_event(f"File downloaded: {filename} ({file_info['size_mb']} MB) via {vpn.current_server}")
        
        # Simulate VPN transfer (add to data usage)
        vpn.add_transfer_data(file_info['size'])
        
        return send_file(file_path, as_attachment=True)
        
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        abort(500, description="Download failed")

@app.route('/delete/<filename>', methods=['DELETE'])
def delete_file(filename):
    """Handle file deletion"""
    try:
        # Check if VPN is connected
        if not vpn.is_connected():
            return jsonify({'success': False, 'error': 'VPN must be connected to manage files'})
        
        filename = secure_filename(filename)
        
        if file_manager.delete_file(filename):
            log_event(f"File deleted: {filename} via {vpn.current_server}")
            return jsonify({'success': True, 'message': f'File "{filename}" deleted successfully'})
        else:
            return jsonify({'success': False, 'error': 'File not found or deletion failed'})
            
    except Exception as e:
        logger.error(f"Delete error: {str(e)}")
        return jsonify({'success': False, 'error': 'Deletion failed'})

@app.route('/api/transfer-stats')
def transfer_stats():
    """Get file transfer statistics"""
    try:
        stats = file_manager.get_transfer_stats()
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        logger.error(f"Stats error: {str(e)}")
        return jsonify({'success': False, 'error': 'Could not get stats'})

if __name__ == '__main__':
    print(" Starting VPN Client Simulator...")
    print("Server will be available at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)

