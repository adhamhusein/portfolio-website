from flask import Flask, render_template, request
from flask import send_file
import os
from app.utils.dxf_converter import handle_project_001

app = Flask(__name__, 
            template_folder='app/templates', 
            static_folder='app/static')

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/project')
def project():
    return render_template('project.html')

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
