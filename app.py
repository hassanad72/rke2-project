import os
import socket

from flask import Flask, jsonify

app = Flask(__name__)

APP_NAME = os.getenv("APP_NAME", "rke2-project")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
HOSTNAME = socket.gethostname()


@app.get("/")
def home():
    return jsonify(
        application=APP_NAME,
        version=APP_VERSION,
        hostname=HOSTNAME,
        message="Hello from publics-3",
    )


@app.get("/health")
def health():
    return jsonify(status="healthy", version=APP_VERSION)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
