#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SERVIDOR API OPTIMIZADO PARA 50K PROPIEDADES
==========================================

Características:
- Paginación eficiente
- Cache de consultas frecuentes
- Filtrado por ciudad/tipo/precio
- Búsqueda de texto
- Compresión de respuestas
- Logs optimizados

"""

import json
import gzip
import logging
import threading
from flask import Flask, request, jsonify, Response, send_file, redirect
from flask_cors import CORS
from functools import lru_cache
from typing import Dict, List, Optional
import os
from datetime import datetime, timedelta

# Importar sistema de prevención
try:
    from sistema_prevencion_corrupciones import PreventorCorrupciones
    SISTEMA_PREVENCION_DISPONIBLE = True
except ImportError:
    SISTEMA_PREVENCION_DISPONIBLE = False

# Configuración
app = Flask(__name__)
CORS(app)

# Cache en memoria (para desarrollo, en producción usar Redis)
CACHE = {}
CACHE_TTL = {}
CACHE_DURATION = 300  # 5 minutos

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PropiedadesManager:
    def __init__(self, archivo_json: str):
        """Inicializa el gestor de propiedades."""
        self.archivo_json = archivo_json
        self.propiedades = []
        self.indices = {
            'ciudad': {},
            'tipo_propiedad': {},
            'tipo_operacion': {},
            'precio_rango': {}
        }
        self.cargar_datos()
        self.crear_indices()
    
    def cargar_datos(self):
        """Carga propiedades desde JSON."""
        try:
            logger.info(f"Cargando propiedades desde: {self.archivo_json}")
            with open(self.archivo_json, 'r', encoding='utf-8') as f:
                datos = json.load(f)
                # Verificar si es directamente una lista o tiene estructura {"propiedades": [...]}
                if isinstance(datos, list):
                    self.propiedades = datos
                else:
                    self.propiedades = datos.get('propiedades', [])
            logger.info(f"Cargadas {len(self.propiedades)} propiedades")
        except Exception as e:
            logger.error(f"Error cargando propiedades: {e}")
            self.propiedades = []
    
    def crear_indices(self):
        """Crea índices para búsquedas rápidas."""
        logger.info("Creando índices...")
        
        for i, prop in enumerate(self.propiedades):
            # Índice por ciudad
            ciudad = prop.get('ubicacion', {}).get('ciudad', 'Sin ciudad')
            if ciudad not in self.indices['ciudad']:
                self.indices['ciudad'][ciudad] = []
            self.indices['ciudad'][ciudad].append(i)
            
            # Índice por tipo de propiedad
            tipo_prop = prop.get('propiedad', {}).get('tipo_propiedad', 'Sin tipo')
            if tipo_prop not in self.indices['tipo_propiedad']:
                self.indices['tipo_propiedad'][tipo_prop] = []
            self.indices['tipo_propiedad'][tipo_prop].append(i)
            
            # Índice por tipo de operación - verificar ambas ubicaciones
            tipo_op = prop.get('operacion') or prop.get('propiedad', {}).get('tipo_operacion', 'Sin operación')
            if tipo_op not in self.indices['tipo_operacion']:
                self.indices['tipo_operacion'][tipo_op] = []
            self.indices['tipo_operacion'][tipo_op].append(i)
            
            # Índice por rango de precios
            precio = prop.get('propiedad', {}).get('precio', {}).get('valor', 0)
            rango = self.obtener_rango_precio(precio)
            if rango not in self.indices['precio_rango']:
                self.indices['precio_rango'][rango] = []
            self.indices['precio_rango'][rango].append(i)
        
        logger.info("Índices creados exitosamente")
    
    def obtener_rango_precio(self, precio: float) -> str:
        """Obtiene el rango de precio de una propiedad."""
        if precio < 500000:
            return "0-500k"
        elif precio < 1000000:
            return "500k-1M"
        elif precio < 2000000:
            return "1M-2M"
        elif precio < 5000000:
            return "2M-5M"
        else:
            return "5M+"
    
    def filtrar_propiedades(self, filtros: Dict) -> List[int]:
        """Filtra propiedades usando índices."""
        # Comenzar con todas las propiedades
        indices_validos = set(range(len(self.propiedades)))
        
        # Filtrar por ciudades múltiples
        if filtros.get('ciudades'):
            ciudades_indices = set()
            for ciudad in filtros['ciudades']:
                ciudades_indices.update(self.indices['ciudad'].get(ciudad, []))
            indices_validos = indices_validos.intersection(ciudades_indices)
        elif filtros.get('ciudad'):  # Compatibilidad con formato anterior
            ciudad_indices = set(self.indices['ciudad'].get(filtros['ciudad'], []))
            indices_validos = indices_validos.intersection(ciudad_indices)
        
        # Filtrar por tipos múltiples
        if filtros.get('tipos'):
            tipos_indices = set()
            for tipo in filtros['tipos']:
                tipos_indices.update(self.indices['tipo_propiedad'].get(tipo, []))
            indices_validos = indices_validos.intersection(tipos_indices)
        elif filtros.get('tipo_propiedad'):  # Compatibilidad con formato anterior
            tipo_indices = set(self.indices['tipo_propiedad'].get(filtros['tipo_propiedad'], []))
            indices_validos = indices_validos.intersection(tipo_indices)
        
        # Filtrar por operaciones múltiples
        if filtros.get('operaciones'):
            operaciones_indices = set()
            for operacion in filtros['operaciones']:
                operaciones_indices.update(self.indices['tipo_operacion'].get(operacion, []))
            indices_validos = indices_validos.intersection(operaciones_indices)
        elif filtros.get('tipo_operacion'):  # Compatibilidad con formato anterior
            op_indices = set(self.indices['tipo_operacion'].get(filtros['tipo_operacion'], []))
            indices_validos = indices_validos.intersection(op_indices)
        
        # Filtrar por rango de precio
        if filtros.get('precio_min') or filtros.get('precio_max'):
            precio_min = float(filtros.get('precio_min', 0))
            precio_max = float(filtros.get('precio_max', float('inf')))
            
            precio_indices = set()
            for i in indices_validos:
                prop = self.propiedades[i]
                precio = prop.get('propiedad', {}).get('precio', {}).get('valor', 0)
                if precio_min <= precio <= precio_max:
                    precio_indices.add(i)
            indices_validos = indices_validos.intersection(precio_indices)
        
        # Filtrar por amenidades
        if filtros.get('amenidades'):
            amenidades_indices = set()
            for i in indices_validos:
                prop = self.propiedades[i]
                amenidades_prop = prop.get('amenidades', {})
                
                # Verificar si tiene las amenidades solicitadas
                tiene_amenidades = True
                for amenidad in filtros['amenidades']:
                    if amenidad == 'alberca':
                        if not amenidades_prop.get('alberca', {}).get('presente', False):
                            tiene_amenidades = False
                            break
                    elif amenidad == 'jardin':
                        if not amenidades_prop.get('jardin', {}).get('presente', False):
                            tiene_amenidades = False
                            break
                    elif amenidad == 'seguridad':
                        # Buscar en descripción si menciona seguridad
                        desc = prop.get('descripcion_original', '').lower()
                        if 'seguridad' not in desc and 'vigilancia' not in desc:
                            tiene_amenidades = False
                            break
                    elif amenidad == 'area_comun':
                        desc = prop.get('descripcion_original', '').lower()
                        if 'área común' not in desc and 'areas comunes' not in desc:
                            tiene_amenidades = False
                            break
                
                if tiene_amenidades:
                    amenidades_indices.add(i)
            indices_validos = indices_validos.intersection(amenidades_indices)
        
        # Filtrar por características arquitectónicas
        if filtros.get('arquitectura'):
            arq_indices = set()
            for i in indices_validos:
                prop = self.propiedades[i]
                desc = prop.get('descripcion_original', '').lower()
                caracteristicas = prop.get('caracteristicas', [])
                
                tiene_caracteristicas = True
                for arq in filtros['arquitectura']:
                    if arq == 'un_nivel':
                        # Buscar directamente en características
                        if 'un_nivel' not in caracteristicas:
                            tiene_caracteristicas = False
                            break
                    elif arq == 'recamara_en_pb':
                        # Buscar en características (puede ser recamara_en_pb o recamara_planta_baja)
                        if ('recamara_en_pb' not in caracteristicas and 
                            'recamara_planta_baja' not in caracteristicas):
                            tiene_caracteristicas = False
                            break
                    elif arq == 'cisterna':
                        # Buscar cisterna en características
                        if 'cisterna' not in caracteristicas:
                            tiene_caracteristicas = False
                            break
                    elif arq == 'opcion_crecer':
                        # Buscar opción de crecer en características
                        if 'opcion_crecer' not in caracteristicas:
                            tiene_caracteristicas = False
                            break
                
                if tiene_caracteristicas:
                    arq_indices.add(i)
            indices_validos = indices_validos.intersection(arq_indices)
        
        # Filtrar por documentación legal
        if filtros.get('legal'):
            legal_indices = set()
            for i in indices_validos:
                prop = self.propiedades[i]
                legal_info = prop.get('legal', {})
                
                tiene_documentacion = False
                for doc_tipo in filtros['legal']:
                    if doc_tipo == 'escrituras' and legal_info.get('escrituras', False):
                        tiene_documentacion = True
                        break
                    elif doc_tipo == 'cesion' and legal_info.get('cesion_derechos', False):
                        tiene_documentacion = True
                        break
                
                if tiene_documentacion:
                    legal_indices.add(i)
            
            indices_validos = indices_validos.intersection(legal_indices)
        
        # Filtrar por búsqueda de texto
        if filtros.get('busqueda'):
            termino_busqueda = filtros['busqueda'].lower()
            busqueda_indices = set()
            
            for i in indices_validos:
                prop = self.propiedades[i]
                descripcion = prop.get('descripcion_original', '').lower()
                direccion_completa = prop.get('ubicacion', {}).get('direccion_completa', '').lower()
                
                if termino_busqueda in descripcion or termino_busqueda in direccion_completa:
                    busqueda_indices.add(i)
            
            indices_validos = indices_validos.intersection(busqueda_indices)
        
        return list(indices_validos)
    
    def obtener_propiedad_simplificada(self, indice: int) -> Dict:
        """Obtiene una versión simplificada de la propiedad para listados."""
        prop = self.propiedades[indice]
        return {
            'id': prop.get('id'),
            'titulo': prop.get('titulo', '')[:100],  # Limitar título
            'url': prop.get('link'),  # URL original del anuncio
            'descripcion': prop.get('descripcion_original', ''),  # Descripción completa
            'precio': prop.get('propiedad', {}).get('precio', {}),
            'tipo_propiedad': prop.get('propiedad', {}).get('tipo_propiedad'),
            'tipo_operacion': prop.get('propiedad', {}).get('tipo_operacion'),
            'operacion': prop.get('operacion') or prop.get('propiedad', {}).get('tipo_operacion'),  # Campo operacion corregido
            'ciudad': prop.get('ubicacion', {}).get('ciudad'),
            'colonia': prop.get('ubicacion', {}).get('colonia'),
            'ubicacion': prop.get('ubicacion', {}),  # Incluir ubicación completa
            'imagen_portada': prop.get('imagen_portada', {}),
            'caracteristicas': prop.get('caracteristicas', [])
        }

# REINICIALIZAR COMPLETAMENTE - SOLUCIÓN TEMPORAL  
logger.info("🔄 REINICIALIZANDO PropiedadesManager para reflejar correcciones...")

# Limpiar referencias anteriores
import gc
gc.collect()

# Crear nueva instancia
propiedades_manager = PropiedadesManager('resultados/propiedades_estructuradas.json')

# Verificar datos cargados
logger.info(f"✅ Verificación post-inicialización:")
for op, indices in propiedades_manager.indices['tipo_operacion'].items():
    logger.info(f"   • {op}: {len(indices)} propiedades")

def is_cache_valid(cache_key: str) -> bool:
    """Verifica si el cache sigue vigente."""
    if cache_key not in CACHE_TTL:
        return False
    return datetime.now() < CACHE_TTL[cache_key]

def set_cache(cache_key: str, data):
    """Guarda datos en cache."""
    CACHE[cache_key] = data
    CACHE_TTL[cache_key] = datetime.now() + timedelta(seconds=CACHE_DURATION)

def get_cache(cache_key: str):
    """Obtiene datos del cache."""
    if is_cache_valid(cache_key):
        return CACHE[cache_key]
    return None

def comprimir_respuesta(data) -> Response:
    """Comprime la respuesta JSON."""
    json_str = json.dumps(data, ensure_ascii=False)
    compressed = gzip.compress(json_str.encode('utf-8'))
    
    response = Response(compressed)
    response.headers['Content-Type'] = 'application/json'
    response.headers['Content-Encoding'] = 'gzip'
    return response

def ordenar_por_precio(indices: List[int], orden: str) -> List[int]:
    """Ordena los índices de propiedades por precio."""
    try:
        def obtener_precio(indice):
            prop = propiedades_manager.propiedades[indice]
            precio_obj = prop.get('propiedad', {}).get('precio', {})
            return precio_obj.get('valor', 0) if precio_obj else 0
        
        if orden == 'mayor_menor':
            return sorted(indices, key=obtener_precio, reverse=True)
        elif orden == 'menor_mayor':
            return sorted(indices, key=obtener_precio, reverse=False)
        else:
            return indices
    except Exception as e:
        logger.error(f"Error al ordenar por precio: {e}")
        return indices

@app.route('/api/propiedades', methods=['GET'])
def obtener_propiedades():
    """Endpoint principal para obtener propiedades con paginación."""
    try:
        # Parámetros de paginación
        pagina = int(request.args.get('pagina', 1))
        por_pagina_param = request.args.get('por_pagina', 20)
        if por_pagina_param == 'all':
            por_pagina = len(propiedades_manager.propiedades)  # Todas las propiedades
        else:
            por_pagina = min(int(por_pagina_param), 500)  # Máximo 500
        
        # Filtros (manejar tanto formatos múltiples como individuales)
        filtros = {}
        
        # Manejar filtros múltiples desde frontend con checkboxes
        if request.args.get('ciudades'):
            filtros['ciudades'] = request.args.get('ciudades').split(',')
        elif request.args.get('ciudad'):
            filtros['ciudad'] = request.args.get('ciudad')
            
        if request.args.get('tipos'):
            filtros['tipos'] = request.args.get('tipos').split(',')
        elif request.args.get('tipo_propiedad'):
            filtros['tipo_propiedad'] = request.args.get('tipo_propiedad')
            
        if request.args.get('operaciones'):
            filtros['operaciones'] = request.args.get('operaciones').split(',')
        elif request.args.get('tipo_operacion'):
            filtros['tipo_operacion'] = request.args.get('tipo_operacion')
        
        # Filtros de precio
        if request.args.get('precio_min'):
            filtros['precio_min'] = request.args.get('precio_min', type=float)
        if request.args.get('precio_max'):
            filtros['precio_max'] = request.args.get('precio_max', type=float)
        
        # Nuevos filtros
        if request.args.get('amenidades'):
            filtros['amenidades'] = request.args.get('amenidades').split(',')
        if request.args.get('arquitectura'):
            filtros['arquitectura'] = request.args.get('arquitectura').split(',')
        if request.args.get('legal'):
            filtros['legal'] = request.args.get('legal').split(',')
        
        # Filtro de búsqueda por texto
        if request.args.get('q'):
            filtros['busqueda'] = request.args.get('q')
        
        # Ordenamiento por precio
        orden_precio = request.args.get('orden_precio')
        
        # Crear clave de cache incluyendo ordenamiento
        cache_key = f"propiedades_{pagina}_{por_pagina}_{orden_precio}_{hash(str(filtros))}"
        
        # Intentar obtener del cache
        cached_result = get_cache(cache_key)
        if cached_result:
            return comprimir_respuesta(cached_result)
        
        # Filtrar propiedades
        indices_filtrados = propiedades_manager.filtrar_propiedades(filtros)
        
        # Aplicar ordenamiento por precio si se solicita
        if orden_precio:
            indices_filtrados = ordenar_por_precio(indices_filtrados, orden_precio)
        
        total = len(indices_filtrados)
        
        # Calcular paginación
        inicio = (pagina - 1) * por_pagina
        fin = inicio + por_pagina
        indices_pagina = indices_filtrados[inicio:fin]
        
        # Obtener propiedades simplificadas
        propiedades = [
            propiedades_manager.obtener_propiedad_simplificada(i) 
            for i in indices_pagina
        ]
        
        resultado = {
            'propiedades': propiedades,
            'total': total,
            'pagina': pagina,
            'por_pagina': por_pagina,
            'total_paginas': (total + por_pagina - 1) // por_pagina,
            'tiene_siguiente': fin < total,
            'tiene_anterior': pagina > 1
        }
        
        # Guardar en cache
        set_cache(cache_key, resultado)
        
        return comprimir_respuesta(resultado)
        
    except Exception as e:
        logger.error(f"Error en obtener_propiedades: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/api/propiedades/<propiedad_id>', methods=['GET'])
def obtener_propiedad_detalle(propiedad_id: str):
    """Obtiene los detalles completos de una propiedad."""
    try:
        # Buscar propiedad por ID
        for prop in propiedades_manager.propiedades:
            if prop.get('id') == propiedad_id:
                return comprimir_respuesta(prop)
        
        return jsonify({'error': 'Propiedad no encontrada'}), 404
        
    except Exception as e:
        logger.error(f"Error en obtener_propiedad_detalle: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/api/estadisticas', methods=['GET'])
def obtener_estadisticas():
    """Obtiene estadísticas generales del catálogo."""
    try:
        # LECTURA DIRECTA DEL ARCHIVO - BYPASS COMPLETO DE CLASES
        logger.info("🔄 Leyendo archivo directamente...")
        with open('resultados/propiedades_estructuradas.json', 'r', encoding='utf-8') as f:
            datos = json.load(f)
            # Verificar si es directamente una lista o tiene estructura {"propiedades": [...]}
            if isinstance(datos, list):
                propiedades = datos
            else:
                propiedades = datos.get('propiedades', [])
        
        logger.info(f"📊 Archivo leído: {len(propiedades)} propiedades")
        
        # Contar operaciones directamente
        operaciones = {}
        ciudades = {}
        tipos = {}
        rangos_precio = {}
        
        for prop in propiedades:
            # Operaciones - verificar ambas ubicaciones
            op = prop.get('operacion') or prop.get('propiedad', {}).get('tipo_operacion', 'sin tipo')
            operaciones[op] = operaciones.get(op, 0) + 1
            
            # Ciudades
            ciudad = prop.get('ubicacion', {}).get('ciudad', 'Sin ciudad')
            ciudades[ciudad] = ciudades.get(ciudad, 0) + 1
            
            # Tipos
            tipo = prop.get('propiedad', {}).get('tipo_propiedad', 'Sin tipo')
            tipos[tipo] = tipos.get(tipo, 0) + 1
            
            # Rangos de precio
            precio = prop.get('propiedad', {}).get('precio', {}).get('valor', 0)
            if precio < 500000:
                rango = "0-500k"
            elif precio < 1000000:
                rango = "500k-1M"
            elif precio < 2000000:
                rango = "1M-2M"
            elif precio < 5000000:
                rango = "2M-5M"
            else:
                rango = "5M+"
            rangos_precio[rango] = rangos_precio.get(rango, 0) + 1
        
        logger.info("📊 Distribución calculada directamente:")
        for op, count in operaciones.items():
            logger.info(f"   • {op}: {count}")
        
        stats = {
            'total_propiedades': len(propiedades),
            'por_ciudad': ciudades,
            'por_tipo': tipos,
            'por_operacion': operaciones,
            'por_rango_precio': rangos_precio
        }
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error en obtener_estadisticas: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/api/buscar', methods=['GET'])
def buscar_propiedades():
    """Búsqueda de texto en propiedades."""
    try:
        termino = request.args.get('q', '').lower()
        if not termino or len(termino) < 2:
            return jsonify({'error': 'Término de búsqueda muy corto'}), 400
        
        pagina = int(request.args.get('pagina', 1))
        por_pagina_param = request.args.get('por_pagina', 20)
        if por_pagina_param == 'all':
            por_pagina = len(propiedades_manager.propiedades)
        else:
            por_pagina = min(int(por_pagina_param), 500)
        
        # Buscar en descripciones y direcciones completas
        resultados = []
        for i, prop in enumerate(propiedades_manager.propiedades):
            descripcion = prop.get('descripcion_original', '').lower()
            direccion_completa = prop.get('ubicacion', {}).get('direccion_completa', '').lower()
            
            if termino in descripcion or termino in direccion_completa:
                resultados.append(i)
        
        # Paginar resultados
        total = len(resultados)
        inicio = (pagina - 1) * por_pagina
        fin = inicio + por_pagina
        indices_pagina = resultados[inicio:fin]
        
        propiedades = [
            propiedades_manager.obtener_propiedad_simplificada(i) 
            for i in indices_pagina
        ]
        
        resultado = {
            'propiedades': propiedades,
            'total': total,
            'pagina': pagina,
            'por_pagina': por_pagina,
            'total_paginas': (total + por_pagina - 1) // por_pagina,
            'termino': termino
        }
        
        return comprimir_respuesta(resultado)
        
    except Exception as e:
        logger.error(f"Error en buscar_propiedades: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/Imagen_no_disponible.jpg')
def servir_imagen_defecto():
    """Sirve la imagen por defecto."""
    try:
        imagen_default = 'Imagen_no_disponible.jpg'
        if os.path.exists(imagen_default):
            return send_file(imagen_default)
        else:
            logger.warning("Imagen por defecto no encontrada")
            return '', 404
    except Exception as e:
        logger.error(f"Error sirviendo imagen por defecto: {e}")
        return '', 404

@app.route('/resultados/<path:filename>')
def servir_imagen(filename):
    """Sirve imágenes desde el directorio de resultados."""
    try:
        archivo_path = os.path.join('resultados', filename)
        if os.path.exists(archivo_path):
            return send_file(archivo_path)
        else:
            # Redirigir a imagen por defecto
            imagen_default = 'Imagen_no_disponible.jpg'
            if os.path.exists(imagen_default):
                return send_file(imagen_default)
            else:
                logger.warning(f"Imagen no encontrada: {filename}")
                return '', 404
    except Exception as e:
        logger.error(f"Error sirviendo imagen {filename}: {e}")
        return '', 404

@app.route('/api/estadisticas-debug', methods=['GET'])
def obtener_estadisticas_debug():
    """DEBUG: Lee directamente el archivo sin cache ni clases."""
    try:
        import json
        with open('resultados/propiedades_estructuradas.json', 'r', encoding='utf-8') as f:
            datos = json.load(f)
            # Verificar si es directamente una lista o tiene estructura {"propiedades": [...]}
            if isinstance(datos, list):
                propiedades = datos
            else:
                propiedades = datos.get('propiedades', [])
        
        # Contar operaciones directamente
        operaciones = {}
        for prop in propiedades:
            op = prop.get('operacion') or prop.get('propiedad', {}).get('tipo_operacion', 'sin tipo')
            operaciones[op] = operaciones.get(op, 0) + 1
        
        return jsonify({
            'total_propiedades': len(propiedades),
            'por_operacion': operaciones,
            'debug': 'Lectura directa del archivo'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de salud del servicio."""
    return jsonify({
        'status': 'healthy',
        'propiedades_cargadas': len(propiedades_manager.propiedades),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/frontend_desarrollo.html')
def servir_frontend():
    """Sirve el archivo HTML del frontend"""
    try:
        return send_file('frontend_desarrollo.html', mimetype='text/html')
    except Exception as e:
        logger.error(f"Error sirviendo frontend: {e}")
        return f"Error sirviendo frontend: {str(e)}", 500

@app.route('/')
def index():
    """Redirige al frontend"""
    try:
        return redirect('/frontend_desarrollo.html')
    except Exception as e:
        logger.error(f"Error en redirección: {e}")
        return "Error interno del servidor", 500

if __name__ == '__main__':
    # Inicializar sistema de prevención
    preventor = None
    if SISTEMA_PREVENCION_DISPONIBLE:
        try:
            preventor = PreventorCorrupciones()
            preventor.iniciar_monitoreo()
            logger.info("🛡️  Sistema de prevención de corrupciones activado")
        except Exception as e:
            logger.warning(f"No se pudo iniciar sistema de prevención: {e}")
    
    try:
        # Configuración para deployment y desarrollo
        import os
        port = int(os.environ.get('PORT', 8080))  # Usar 8080 como default para DigitalOcean
        app.run(host='0.0.0.0', port=port, debug=False)
    except KeyboardInterrupt:
        logger.info("Servidor detenido por el usuario")
        if preventor:
            preventor.detener_monitoreo()
    except Exception as e:
        logger.error(f"Error iniciando servidor: {e}")
        if preventor:
            preventor.detener_monitoreo() 