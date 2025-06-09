#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WSGI Configuration for DigitalOcean App Platform
"""
import os

try:
    # Intentar importar desde api_server_optimizado
    from api_server_optimizado import app
    print("✅ Importado desde api_server_optimizado")
except ImportError:
    # Fallback a aplicación básica
    from flask import Flask
    app = Flask(__name__)
    
    @app.route("/")
    def hello():
        return "Hello from App Platform!"
    
    @app.route("/health")
    def health():
        return {"status": "healthy"}
    
    print("⚠️ Usando aplicación básica de fallback")

# Configuración para desarrollo local
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

# Variable requerida por Gunicorn
application = app 