from flask import Flask, render_template, request, send_file, send_from_directory, jsonify, Response
from werkzeug.exceptions import RequestEntityTooLarge
import os
from threading import Thread
import time
from datetime import datetime
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from app.utils.dxf_converter import handle_project_001
from app.utils.project_004_processor import create_session_processor
from werkzeug.utils import secure_filename
import uuid

load_dotenv()

app = Flask(__name__, 
            template_folder='app/templates', 
            static_folder='app/static')

app.url_map.strict_slashes = False

# Configure file upload limits
app.config['MAX_CONTENT_LENGTH'] = 250 * 1024 * 1024  # 250MB limit (slightly higher than frontend 200MB)
app.config['UPLOAD_EXTENSIONS'] = ['.csv']
app.config['UPLOAD_PATH'] = 'uploads'

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Error handler for large file uploads
@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    return jsonify({'error': 'File size too large. Maximum size is 200MB.'}), 413

def delete_old_files():
    """Function to delete files older than 6 hours in the uploads folder."""
    while True:
        current_time = time.time()
        
        # Iterate through files in the uploads folder
        for filename in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, filename)

            # Only delete regular files; skip directories.
            if not os.path.isfile(file_path):
                continue
            
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
    print("=== Starting visualization processing ===")
    
    try:
        data = request.get_json()
        print(f"Received data: {data}")
        
        position_file = data.get('position_file')
        map_file = data.get('map_file')
        
        print(f"Position file info: {position_file}")
        print(f"Map file info: {map_file}")
        
        if not position_file or not map_file:
            print("Missing position or map file")
            return jsonify({'error': 'Both position and map files are required'}), 400
        
        # Verify files exist in uploads folder
        position_path = os.path.join(app.config['UPLOAD_FOLDER'], position_file['filename'])
        map_path = os.path.join(app.config['UPLOAD_FOLDER'], map_file['filename'])
        
        print(f"Position file path: {position_path}")
        print(f"Map file path: {map_path}")
        
        if not os.path.exists(position_path):
            print(f"Position file not found: {position_path}")
            return jsonify({'error': f'Position file not found: {position_file["filename"]}'}), 404
        
        if not os.path.exists(map_path):
            print(f"Map file not found: {map_path}")
            return jsonify({'error': f'Map file not found: {map_file["filename"]}'}), 404
        
        print("Both files exist, starting processing...")
        
        # Create session processor and process files
        try:
            processor = create_session_processor(app.config['UPLOAD_FOLDER'])
            print("Session processor created successfully")
            
            processed_files = processor.process_files(position_file, map_file)
            print(f"Processing completed. Session ID: {processed_files['session_id']}")
            
        except Exception as processing_error:
            print(f"Error during file processing: {str(processing_error)}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'File processing failed: {str(processing_error)}'}), 500
        
        # Verify processed files were created
        processed_position_path = processed_files['processed_position']['path']
        geojson_path = processed_files['geojson']['path']
        
        print(f"Checking processed position file: {processed_position_path}")
        print(f"Checking GeoJSON file: {geojson_path}")
        
        if not os.path.exists(processed_position_path):
            error_msg = f"Processed position file not created: {processed_position_path}"
            print(error_msg)
            raise FileNotFoundError(error_msg)
        
        if not os.path.exists(geojson_path):
            error_msg = f"GeoJSON file not created: {geojson_path}"
            print(error_msg)
            raise FileNotFoundError(error_msg)
        
        print("All processed files verified successfully")
        
        response_data = {
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
        }
        
        print(f"Returning success response: {response_data}")
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Unexpected error in project_004_start: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

@app.route('/project/project_001', methods=['GET', 'POST'])
def project_001():
    return handle_project_001(request, app.config['UPLOAD_FOLDER'])

@app.route('/api/property_detil', methods=['GET'])
def property_detil():
    """Return all rows from public.property_detil as one streamed JSON response."""
    try:
        db_password = os.getenv('PROPERTY_DB_PASSWORD')
        if not db_password:
            return jsonify({'error': 'Database password is not configured'}), 500

        conn = psycopg2.connect(
            host='68.168.218.105',
            database='property',
            user='postgres',
            password=db_password
        )
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            SELECT *
            FROM public.property_detil
            """
        )

        def generate_rows():
            try:
                first_item = True
                yield '['
                while True:
                    batch = cur.fetchmany(1000)
                    if not batch:
                        break

                    for row in batch:
                        if not first_item:
                            yield ','
                        yield json.dumps(row, default=str)
                        first_item = False
                yield ']'
            finally:
                cur.close()
                conn.close()

        return Response(generate_rows(), mimetype='application/json')

    except Exception as e:
        return jsonify({'error': f'Failed to fetch property_detil: {str(e)}'}), 500

@app.route('/api/property_address', methods=['GET'])
def property_address():
    """Return rows from public.property_address as one streamed JSON response."""
    try:
        db_password = os.getenv('PROPERTY_DB_PASSWORD')
        if not db_password:
            return jsonify({'error': 'Database password is not configured'}), 500

        conn = psycopg2.connect(
            host='68.168.218.105',
            database='property',
            user='postgres',
            password=db_password
        )
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            SELECT *
            FROM public.property_address
            """
        )

        def generate_rows():
            try:
                first_item = True
                yield '['
                while True:
                    batch = cur.fetchmany(1000)
                    if not batch:
                        break

                    for row in batch:
                        if not first_item:
                            yield ','
                        yield json.dumps(row, default=str)
                        first_item = False
                yield ']'
            finally:
                cur.close()
                conn.close()

        return Response(generate_rows(), mimetype='application/json')

    except Exception as e:
        return jsonify({'error': f'Failed to fetch property_address: {str(e)}'}), 500

@app.route('/download/geojson')
def download_geojson():
    path = request.args.get('path')
    if path and os.path.exists(path):
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

@app.route('/project/project_004_test_upload', methods=['GET'])
def project_004_test_upload():
    """Test route to check upload configuration."""
    return jsonify({
        'max_content_length': app.config.get('MAX_CONTENT_LENGTH', 'Not set'),
        'max_content_length_mb': app.config.get('MAX_CONTENT_LENGTH', 0) / (1024 * 1024) if app.config.get('MAX_CONTENT_LENGTH') else 0,
        'upload_folder': app.config.get('UPLOAD_FOLDER'),
        'upload_extensions': app.config.get('UPLOAD_EXTENSIONS', []),
        'upload_path': app.config.get('UPLOAD_PATH')
    })

@app.route('/project/project_004_upload', methods=['POST'])
def project_004_upload():
    """Handle file uploads for project 004 with progress tracking."""
    print(f"Upload request received - Content-Type: {request.content_type}")
    print(f"Request files: {list(request.files.keys())}")
    
    if 'file' not in request.files:
        print("No file in request.files")
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    filename = file.filename or ''
    file_type = request.form.get('file_type', 'unknown')  # 'position' or 'map'
    
    print(f"Processing file: {filename}, type: {file_type}")
    
    if filename == '':
        print("Empty filename")
        return jsonify({'error': 'No file selected'}), 400
    
    # Validate file size (max 200MB to match frontend)
    file.seek(0, 2)  # Seek to end
    file_size = file.tell()
    file.seek(0)  # Reset to beginning
    
    print(f"File size: {file_size} bytes ({file_size / (1024*1024):.2f} MB)")
    
    max_size = 200 * 1024 * 1024  # 200MB to match frontend
    if file_size > max_size:
        print(f"File too large: {file_size} > {max_size}")
        return jsonify({'error': 'File size too large. Maximum size is 200MB.'}), 400
    
    # Validate file extension
    allowed_extensions = {'.csv'}
    file_extension = os.path.splitext(filename)[1].lower()
    
    print(f"File extension: {file_extension}")
    
    if file_extension not in allowed_extensions:
        print(f"Invalid file extension: {file_extension}")
        return jsonify({'error': f'Invalid file type. Only CSV files are allowed.'}), 400
    
    try:
        if file:
            # Generate unique filename to avoid conflicts
            original_filename = secure_filename(filename)
            unique_filename = f"{file_type}_{uuid.uuid4().hex}{file_extension}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            
            print(f"Saving file to: {file_path}")
            
            # Save the file
            file.save(file_path)
            
            # Verify file was saved
            if os.path.exists(file_path):
                actual_size = os.path.getsize(file_path)
                print(f"File saved successfully. Actual size: {actual_size} bytes")
            else:
                print("File was not saved properly")
                return jsonify({'error': 'File was not saved properly'}), 500
            
            return jsonify({
                'success': True,
                'filename': unique_filename,
                'original_name': original_filename,
                'file_path': file_path,
                'file_size': file_size
            })
    except Exception as e:
        print(f"Error saving file {file.filename}: {str(e)}")
        return jsonify({'error': f'File upload failed: {str(e)}'}), 500
    
    return jsonify({'error': 'File upload failed'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5500)
