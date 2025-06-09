import os
from flask import Flask

app = Flask(__name__)

@app.route("/")
def hello():
    return "Hello from App Platform!"

@app.route("/health")
def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

application = app 