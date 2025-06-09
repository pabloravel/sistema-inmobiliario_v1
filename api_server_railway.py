#!/usr/bin/env python3
"""
🏠 SISTEMA INMOBILIARIO COMPLETO - VERSIÓN RAILWAY
Sistema inmobiliario con funcionalidades de administración, WhatsApp, favoritos, etc.
Adaptado para deployment en Railway
"""

import os
import sys

# Configurar puerto dinámico para Railway
PORT = int(os.environ.get('PORT', 5001))
HOST = '0.0.0.0'

# Agregar directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importar el app original
from api_server_optimizado import app, logger

if __name__ == '__main__':
    try:
        logger.info(f"🚀 [RAILWAY] Iniciando servidor en {HOST}:{PORT}")
        app.run(host=HOST, port=PORT, debug=False)
    except Exception as e:
        logger.error(f"❌ Error iniciando servidor: {e}")
        sys.exit(1) 