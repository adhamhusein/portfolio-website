from flask import Flask, render_template

app = Flask(__name__, 
            template_folder='app/templates', 
            static_folder='app/static')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/project')
def project():
    return render_template('project.html')

if __name__ == '__main__':
    app.run(debug=True, port=5500)
