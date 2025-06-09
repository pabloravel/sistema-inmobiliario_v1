from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return {'message': 'Hello from DigitalOcean App Platform!'}

@app.route('/health')
def health():
    return {'status': 'healthy'}

application = app 