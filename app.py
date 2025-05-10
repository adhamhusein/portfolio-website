from flask import Flask, render_template, request, send_file, send_from_directory
import os
from threading import Thread
import time
from datetime import datetime
from app.utils.dxf_converter import handle_project_001

app = Flask(__name__, 
            template_folder='app/templates', 
            static_folder='app/static')

app.url_map.strict_slashes = False
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def delete_old_files():
    """Function to delete files older than 5 minutes in the uploads folder."""
    while True:
        current_time = time.time()
        
        # Iterate through files in the uploads folder
        for filename in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            
            if os.path.exists(file_path):
                file_mod_time = os.path.getmtime(file_path)

                # If file is older than 5 minutes, delete it
                if current_time - file_mod_time > 5 * 60:  # 5 minutes = 5 * 60 seconds
                    try:
                        os.remove(file_path)
                        print(f"Deleted file: {file_path}")
                    except Exception as e:
                        print(f"Error deleting file {file_path}: {e}")
        
        # Wait for 1 minute before checking again
        time.sleep(600)

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
# @app.route('/project/project_002/')
def project_002():
    return render_template('project_002.html')


@app.route('/project/project_001', methods=['GET', 'POST'])
def project_001():
    return handle_project_001(request, app.config['UPLOAD_FOLDER'])

@app.route('/download/geojson')
def download_geojson():
    path = request.args.get('path')
    if os.path.exists(path):
        return send_file(path, as_attachment=True, download_name='converted.geojson')
    return "File not found", 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5500)
