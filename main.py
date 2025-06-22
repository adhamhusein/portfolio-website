from flask import Flask, render_template, request, send_file, send_from_directory, jsonify
import os
from threading import Thread
import time
from datetime import datetime
from app.utils.dxf_converter import handle_project_001
from app.utils.project_004_processor import create_session_processor
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__, 
            template_folder='app/templates', 
            static_folder='app/static')

app.url_map.strict_slashes = False
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def delete_old_files():
    """Function to delete files older than 6 hours in the uploads folder."""
    while True:
        current_time = time.time()
        
        # Iterate through files in the uploads folder
        for filename in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            
            if os.path.exists(file_path):
                file_mod_time = os.path.getmtime(file_path)

                # If file is older than 6 hours, delete it
                if current_time - file_mod_time > 6 * 60 * 60: 
                    try:
                        os.remove(file_path)
                        print(f"Deleted file: {file_path}")
                    except Exception as e:
                        print(f"Error deleting file {file_path}: {e}")
        
        # Wait for 1 hour before checking again
        time.sleep(60 * 60)

def start_cleanup_thread():
    """Start the background thread for periodic cleanup."""
    cleanup_thread = Thread(target=delete_old_files, daemon=True)
    cleanup_thread.start()

# Start the cleanup thread when the app starts
start_cleanup_thread()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/project')
def project():
    return render_template('project.html')

@app.route('/project/project_002')
@app.route('/project/project_002/')
def project_002():
    return render_template('project_002.html')

@app.route('/project/project_004')
def project_004():
    return render_template('project_004.html')

@app.route('/project/project_004_2')
def project_004_2():
    return render_template('project_004_2.html')

@app.route('/project/project_004_cleanup/<session_id>', methods=['POST'])
def project_004_cleanup(session_id):
    """Clean up session-specific processed files."""
    try:
        # Find and delete session-specific files
        deleted_files = []
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            if filename.startswith(f"session_{session_id}"):
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                try:
                    os.remove(file_path)
                    deleted_files.append(filename)
                    print(f"Cleaned up session file: {filename}")
                except Exception as e:
                    print(f"Error deleting session file {filename}: {e}")
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'deleted_files': deleted_files
        })
        
    except Exception as e:
        print(f"Error cleaning up session {session_id}: {str(e)}")
        return jsonify({'error': f'Cleanup failed: {str(e)}'}), 500

@app.route('/project/project_004_start', methods=['POST'])
def project_004_start():
    """Handle starting the visualization with uploaded files and process them."""
    data = request.get_json()
    position_file = data.get('position_file')
    map_file = data.get('map_file')
    
    if not position_file or not map_file:
        return jsonify({'error': 'Both position and map files are required'}), 400
    
    # Verify files exist in uploads folder
    position_path = os.path.join(app.config['UPLOAD_FOLDER'], position_file['filename'])
    map_path = os.path.join(app.config['UPLOAD_FOLDER'], map_file['filename'])
    
    if not os.path.exists(position_path) or not os.path.exists(map_path):
        return jsonify({'error': 'Uploaded files not found'}), 404
    
    try:
        # Create session processor and process files
        processor = create_session_processor(app.config['UPLOAD_FOLDER'])
        processed_files = processor.process_files(position_file, map_file)
        
        # Verify processed files were created
        processed_position_path = processed_files['processed_position']['path']
        geojson_path = processed_files['geojson']['path']
        
        if not os.path.exists(processed_position_path):
            raise FileNotFoundError(f"Processed position file not created: {processed_position_path}")
        
        if not os.path.exists(geojson_path):
            raise FileNotFoundError(f"GeoJSON file not created: {geojson_path}")
        
        return jsonify({
            'success': True,
            'session_id': processed_files['session_id'],
            'position_file': position_file,
            'map_file': map_file,
            'processed_files': {
                'position_processed': processed_files['processed_position']['filename'],
                'geojson': processed_files['geojson']['filename']
            },
            'processing_info': {
                'processed_at': processed_files['processed_at'],
                'vehicle_data_rows': processed_files['vehicle_data_rows']
            }
        })
        
    except Exception as e:
        print(f"Error processing files: {str(e)}")
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

@app.route('/project/project_001', methods=['GET', 'POST'])
def project_001():
    return handle_project_001(request, app.config['UPLOAD_FOLDER'])

@app.route('/download/geojson')
def download_geojson():
    path = request.args.get('path')
    if os.path.exists(path):
        return send_file(path, as_attachment=True, download_name='converted.geojson')
    return "File not found", 404

@app.route('/upload/<path:filename>')
def serve_upload_file(filename):
    """Serve files from the uploads directory."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/project/project_004_files/<filename>')
def serve_project_004_file(filename):
    """Serve uploaded files for project 004."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/project/project_004_processed/<filename>')
def serve_project_004_processed_file(filename):
    """Serve processed files for project 004 with session-based access."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/project/project_004_upload', methods=['POST'])
def project_004_upload():
    """Handle file uploads for project 004 with progress tracking."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    file_type = request.form.get('file_type', 'unknown')  # 'position' or 'map'
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Validate file size (max 50MB)
    file.seek(0, 2)  # Seek to end
    file_size = file.tell()
    file.seek(0)  # Reset to beginning
    
    max_size = 50 * 1024 * 1024  # 50MB
    if file_size > max_size:
        return jsonify({'error': 'File size too large. Maximum size is 50MB.'}), 400
    
    # Validate file extension
    allowed_extensions = {'.csv'}
    file_extension = os.path.splitext(file.filename)[1].lower()
    
    if file_extension not in allowed_extensions:
        return jsonify({'error': f'Invalid file type. Only CSV files are allowed.'}), 400
    
    if file:
        # Generate unique filename to avoid conflicts
        original_filename = secure_filename(file.filename)
        unique_filename = f"{file_type}_{uuid.uuid4().hex}{file_extension}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        # Save the file
        file.save(file_path)
        
        return jsonify({
            'success': True,
            'filename': unique_filename,
            'original_name': original_filename,
            'file_path': file_path
        })
    
    return jsonify({'error': 'File upload failed'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5500)
