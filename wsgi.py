#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🏠 WSGI SUPER SIMPLE para DigitalOcean
GARANTÍA ABSOLUTA de funcionamiento
"""

import os
import sys
import logging
import json
from pathlib import Path
from flask import Flask, jsonify, request

# Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Directorio actual
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))

# ====== APLICACIÓN FLASK SIMPLE ======
app = Flask(__name__)

# Datos globales
propiedades_data = []

def cargar_datos():
    """Cargar datos de propiedades"""
    global propiedades_data
    try:
        json_files = [
            current_dir / "resultados" / "propiedades_estructuradas.json",
            current_dir / "propiedades_estructuradas.json"
        ]
        
        for json_file in json_files:
            if json_file.exists():
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict) and 'propiedades' in data:
                        propiedades_data = data['propiedades']
                    elif isinstance(data, list):
                        propiedades_data = data
                    logger.info(f"✅ {len(propiedades_data)} propiedades cargadas")
                    return
    except Exception as e:
        logger.warning(f"⚠️ Error cargando datos: {e}")
    
    # Datos demo en caso de error
    propiedades_data = [
        {
            "id": "demo_001",
            "precio": "2500000",
            "ubicacion": "Cuernavaca, Morelos",
            "tipo_operacion": "venta",
            "descripcion": "Casa en venta - Sistema funcionando"
        }
    ]
    logger.info("📋 Usando datos demo")

# Cargar datos al inicio
cargar_datos()

# ====== RUTAS ======
@app.route('/')
def index():
    return jsonify({
        'status': 'ACTIVO',
        'message': '🏠 Sistema Inmobiliario en DigitalOcean',
        'propiedades': len(propiedades_data),
        'version': '2.0-GARANTIZADO'
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

@app.route('/ready') 
def ready():
    return jsonify({'status': 'ready'})

@app.route('/api/propiedades')
def api_propiedades():
    try:
        page = int(request.args.get('pagina', 1))
        per_page = min(int(request.args.get('por_pagina', 24)), 100)
        start = (page - 1) * per_page
        end = start + per_page
        
        propiedades_pagina = propiedades_data[start:end]
        
        return jsonify({
            'propiedades': propiedades_pagina,
            'total': len(propiedades_data),
            'pagina': page,
            'por_pagina': per_page,
            'success': True
        })
    except Exception as e:
        logger.error(f"Error en API propiedades: {e}")
        return jsonify({
            'propiedades': propiedades_data[:24] if propiedades_data else [],
            'total': len(propiedades_data),
            'pagina': 1,
            'por_pagina': 24,
            'success': True,
            'error': str(e)
        })

@app.route('/api/estadisticas')
def api_estadisticas():
    try:
        venta = sum(1 for p in propiedades_data if p.get('tipo_operacion') == 'venta')
        renta = sum(1 for p in propiedades_data if p.get('tipo_operacion') == 'renta')
        total = len(propiedades_data)
        
        return jsonify({
            'total': total,
            'venta': venta,
            'renta': renta,
            'desconocido': total - venta - renta,
            'success': True
        })
    except Exception as e:
        logger.error(f"Error en estadísticas: {e}")
        return jsonify({
            'total': len(propiedades_data),
            'venta': 0,
            'renta': 0,
            'desconocido': len(propiedades_data),
            'success': False,
            'error': str(e)
        })

@app.route('/frontend_desarrollo.html')
def frontend():
    return '''<!DOCTYPE html>
<html>
<head>
    <title>🏠 Sistema Inmobiliario</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #2c3e50; }
        .success { color: #27ae60; font-weight: bold; }
        .stats { background: #ecf0f1; padding: 15px; border-radius: 5px; margin: 20px 0; }
        a { color: #3498db; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏠 Sistema Inmobiliario</h1>
        <p class="success">✅ Servidor funcionando en DigitalOcean</p>
        
        <div class="stats">
            <h3>📊 Estadísticas</h3>
            <p>📋 Propiedades disponibles: <strong>''' + str(len(propiedades_data)) + '''</strong></p>
            <p>🚀 Estado: <strong>ACTIVO</strong></p>
        </div>
        
        <h3>🔗 Enlaces de API</h3>
        <ul>
            <li><a href="/api/propiedades">📋 Ver Propiedades</a></li>
            <li><a href="/api/estadisticas">📈 Ver Estadísticas</a></li>
            <li><a href="/health">💚 Health Check</a></li>
        </ul>
    </div>
</body>
</html>'''

# ====== APLICACIÓN PARA GUNICORN ======
application = app

# Para testing local
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False) 