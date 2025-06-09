#!/usr/bin/env python3
"""
WSGI Configuration for DigitalOcean App Platform
Patrón oficial: https://docs.digitalocean.com/products/app-platform/how-to/deploy-flask-app/
"""
import os
import sys

# Debugging para DigitalOcean
print("🔍 DEBUG: Iniciando wsgi.py")
print(f"🔍 DEBUG: Python version: {sys.version}")
print(f"🔍 DEBUG: Current working directory: {os.getcwd()}")
print(f"🔍 DEBUG: Python path: {sys.path}")
print(f"🔍 DEBUG: Environment PORT: {os.environ.get('PORT', 'NOT SET')}")

try:
    # Intentar importar la aplicación principal
    from api_server_optimizado import app
    print("✅ SUCCESS: Importado desde api_server_optimizado")
    
    # Verificar que la app sea válida
    if hasattr(app, 'wsgi_app'):
        print("✅ SUCCESS: Flask app válida detectada")
    else:
        print("⚠️ WARNING: App no tiene wsgi_app")
        
except ImportError as e:
    print(f"❌ ERROR: No se pudo importar api_server_optimizado: {e}")
    print("🔄 FALLBACK: Creando aplicación básica")
    
    # Crear aplicación básica de emergencia
    from flask import Flask
    app = Flask(__name__)
    
    @app.route("/")
    def hello():
        return "Hello from DigitalOcean App Platform!"
    
    @app.route("/health")
    def health():
        return {"status": "healthy", "message": "Fallback app running"}
    
    print("✅ SUCCESS: Aplicación básica creada")

# Configurar para producción
if os.environ.get('FLASK_ENV') == 'production':
    app.config['DEBUG'] = False
    print("🔧 CONFIG: Modo producción activado")

# Esta es la variable que Gunicorn busca
application = app

print(f"🚀 READY: application = {application}")
print(f"🚀 READY: application type = {type(application)}")

# Para desarrollo local
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🏠 LOCAL: Ejecutando en puerto {port}")
    app.run(host="0.0.0.0", port=port, debug=False) 