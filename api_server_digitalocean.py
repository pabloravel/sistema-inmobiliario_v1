#!/usr/bin/env python3
"""
Adaptador para DigitalOcean App Platform
Este archivo es el punto de entrada para el deployment
"""

import os
import sys

# Agregar directorio actual al path para imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configurar variables de entorno para DigitalOcean
os.environ.setdefault('FLASK_ENV', 'production')
os.environ.setdefault('FLASK_DEBUG', 'false')

# Importar la aplicación principal
from api_server_optimizado import app

if __name__ == '__main__':
    # DigitalOcean asigna el puerto dinámicamente
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False) 