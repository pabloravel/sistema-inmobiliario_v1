#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Punto de entrada para Render.com
Importa la aplicación Flask desde api_server_optimizado (versión con cache busting y nuevas funcionalidades)
"""

from api_server_optimizado import app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False) 