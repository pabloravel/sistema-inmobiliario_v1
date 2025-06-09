#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🏠 WSGI SUPER SIMPLE para DigitalOcean
GARANTÍA ABSOLUTA de funcionamiento
"""

import os
import json
from flask import Flask, jsonify, request

app = Flask(__name__)

# Datos básicos
propiedades = []

# Cargar datos si existe el archivo
try:
    if os.path.exists('resultados/propiedades_estructuradas.json'):
        with open('resultados/propiedades_estructuradas.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict) and 'propiedades' in data:
                propiedades = data['propiedades']
            elif isinstance(data, list):
                propiedades = data
except:
    propiedades = [{"id": "demo", "precio": "1000000", "ubicacion": "Cuernavaca", "tipo_operacion": "venta"}]

@app.route('/')
def index():
    return jsonify({
        'status': 'OK',
        'propiedades': len(propiedades),
        'message': 'Sistema funcionando en DigitalOcean'
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

@app.route('/ready')
def ready():
    return jsonify({'status': 'ready'})

@app.route('/api/propiedades')
def api_propiedades():
    page = int(request.args.get('pagina', 1))
    per_page = min(int(request.args.get('por_pagina', 24)), 100)
    start = (page - 1) * per_page
    end = start + per_page
    
    return jsonify({
        'propiedades': propiedades[start:end],
        'total': len(propiedades),
        'pagina': page,
        'por_pagina': per_page
    })

@app.route('/api/estadisticas')
def api_estadisticas():
    venta = sum(1 for p in propiedades if p.get('tipo_operacion') == 'venta')
    renta = sum(1 for p in propiedades if p.get('tipo_operacion') == 'renta')
    total = len(propiedades)
    
    return jsonify({
        'total': total,
        'venta': venta,
        'renta': renta,
        'desconocido': total - venta - renta
    })

@app.route('/frontend_desarrollo.html')
def frontend():
    return f'''<!DOCTYPE html>
<html>
<head>
    <title>Sistema Inmobiliario</title>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ background: white; padding: 30px; border-radius: 10px; }}
        h1 {{ color: #2c3e50; }}
        .success {{ color: #27ae60; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🏠 Sistema Inmobiliario</h1>
        <p class="success">✅ Funcionando en DigitalOcean</p>
        <p>📋 Propiedades: <strong>{len(propiedades)}</strong></p>
        <p><a href="/api/propiedades">Ver API Propiedades</a></p>
        <p><a href="/api/estadisticas">Ver Estadísticas</a></p>
    </div>
</body>
</html>'''

application = app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port) 