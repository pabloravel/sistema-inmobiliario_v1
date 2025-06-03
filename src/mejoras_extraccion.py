#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import json
from typing import Dict, List, Union, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

# Constantes y configuración
PRECIO_MIN_VENTA = 500_000  # 500 mil pesos
PRECIO_MAX_VENTA = 50_000_000  # 50 millones
PRECIO_MIN_RENTA = 3_000  # 3 mil pesos
PRECIO_MAX_RENTA = 150_000  # 150 mil pesos
SUPERFICIE_MIN = 30  # 30 m²
SUPERFICIE_MAX = 10_000  # 10,000 m²
CONSTRUCCION_MIN = 30  # 30 m²
CONSTRUCCION_MAX = 5_000  # 5,000 m²

class TipoOperacion(Enum):
    VENTA = "venta"
    RENTA = "renta"
    DESCONOCIDO = "desconocido"

class TipoPropiedad(Enum):
    CASA = "casa"
    DEPARTAMENTO = "departamento"
    TERRENO = "terreno"
    LOCAL = "local"
    OFICINA = "oficina"
    BODEGA = "bodega"
    OTRO = "otro"

@dataclass
class Score:
    completitud: float = 0.0
    coherencia: float = 0.0
    calidad_datos: float = 0.0
    
    @property
    def total(self) -> float:
        return (self.completitud + self.coherencia + self.calidad_datos) / 3

class ExtractorMejorado:
    def __init__(self):
        # Cargar catálogo de colonias
        self.colonias = self._cargar_catalogo_colonias()
        self.errores = []
        
    def _cargar_catalogo_colonias(self) -> Dict[str, Dict[str, str]]:
        """Carga el catálogo de colonias desde un archivo JSON"""
        try:
            with open('catalogos/colonias.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # Catálogo básico si no existe el archivo
            return {
                "cuernavaca": {
                    "chipitlan": "Chipitlán",
                    "reforma": "Reforma",
                    "vista hermosa": "Vista Hermosa",
                    # ... más colonias
                }
            }

    def normalizar_precio(self, texto: str) -> Tuple[float, str, bool]:
        """
        Normaliza el precio extraído del texto.
        Retorna: (precio_normalizado, moneda, es_valido)
        """
        try:
            if not texto:
                return 0.0, "MXN", False
            
            # Limpiar el texto
            texto = texto.lower().strip()
            
            # Detectar moneda
            moneda = "MXN"
            if any(term in texto for term in ['usd', 'dolar', 'dólar', '$us']):
                moneda = "USD"
            
            # Extraer números
            numeros = re.findall(r'[\d,.]+', texto)
            if not numeros:
                return 0.0, moneda, False
            
            # Tomar el primer número encontrado
            numero = numeros[0]
            
            # Manejar diferentes formatos de números
            if ',' in numero and '.' in numero:
                # Formato: 1,234.56 o 1.234,56
                if numero.find(',') < numero.find('.'):
                    numero = numero.replace(',', '')  # Formato americano
                else:
                    numero = numero.replace('.', '').replace(',', '.')  # Formato europeo
            elif ',' in numero:
                # Si solo hay comas, asumimos formato mexicano (1,234)
                if len(numero.split(',')[-1]) == 3:  # Si la parte después de la coma tiene 3 dígitos
                    numero = numero.replace(',', '')
                else:
                    numero = numero.replace(',', '.')
            elif '.' in numero:
                # Si solo hay puntos, asumimos formato americano (1.234)
                if len(numero.split('.')[-1]) == 3:  # Si la parte después del punto tiene 3 dígitos
                    numero = numero.replace('.', '')
            
            # Convertir a float
            precio = float(numero)
            
            # Aplicar multiplicadores
            if any(term in texto for term in ['k', 'mil']):
                precio *= 1_000
            elif any(term in texto for term in ['m', 'millon', 'millón']):
                precio *= 1_000_000
            
            # Si es USD, convertir a MXN para validación
            if moneda == "USD":
                precio *= 17.5  # Tasa de conversión aproximada
            
            # Validar rangos según tipo de operación
            if self.tipo_operacion == TipoOperacion.VENTA:
                if PRECIO_MIN_VENTA <= precio <= PRECIO_MAX_VENTA:
                    return precio, moneda, True
            elif self.tipo_operacion == TipoOperacion.RENTA:
                if PRECIO_MIN_RENTA <= precio <= PRECIO_MAX_RENTA:
                    return precio, moneda, True
                
            # Si el precio está fuera de rango pero es un número válido,
            # intentamos ajustarlo
            if precio < PRECIO_MIN_VENTA and self.tipo_operacion == TipoOperacion.VENTA:
                # Si el precio es muy bajo para venta, multiplicar por 1000
                precio *= 1000
                if PRECIO_MIN_VENTA <= precio <= PRECIO_MAX_VENTA:
                    return precio, moneda, True
                
            if precio > PRECIO_MAX_RENTA and self.tipo_operacion == TipoOperacion.RENTA:
                # Si el precio es muy alto para renta, dividir por 1000
                precio /= 1000
                if PRECIO_MIN_RENTA <= precio <= PRECIO_MAX_RENTA:
                    return precio, moneda, True
                
            # Si llegamos aquí, el precio está fuera de rango
            return precio, moneda, False
        
        except (ValueError, TypeError):
            return 0.0, "MXN", False

    def extraer_ubicacion(self, texto: str) -> Dict[str, Union[str, List[str]]]:
        """
        Extrae y normaliza la información de ubicación.
        """
        ubicacion = {
            "ciudad": "",
            "colonia": "",
            "calle": "",
            "referencias": [],
            "coordenadas": {"lat": None, "lng": None}
        }
        
        texto = texto.lower()
        
        # Detectar ciudad
        ciudades = ["cuernavaca", "jiutepec", "temixco", "zapata", "xochitepec"]
        for ciudad in ciudades:
            if ciudad in texto:
                ubicacion["ciudad"] = ciudad.title()
                break
        
        # Buscar colonia en el catálogo
        if ubicacion["ciudad"].lower() in self.colonias:
            colonias_ciudad = self.colonias[ubicacion["ciudad"].lower()]
            for col_key, col_nombre in colonias_ciudad.items():
                if col_key in texto:
                    ubicacion["colonia"] = col_nombre
                    break
        
        # Extraer calle
        patrones_calle = [
            r"(?:calle|av\.|avenida|boulevard|blvd\.|camino)\s+([a-zá-úñ\s]+(?:\s+#?\d+)?)",
            r"sobre\s+([a-zá-úñ\s]+(?:\s+#?\d+)?)"
        ]
        
        for patron in patrones_calle:
            if match := re.search(patron, texto):
                ubicacion["calle"] = match.group(1).strip().title()
                break
        
        # Extraer referencias
        referencias = []
        patrones_ref = [
            r"cerca\s+(?:de|del|dela|a)\s+([^,\.]+)",
            r"junto\s+(?:a|al|ala)\s+([^,\.]+)",
            r"a\s+(?:\d+\s+)?(?:minutos|cuadras|metros)\s+(?:de|del|dela)\s+([^,\.]+)"
        ]
        
        for patron in patrones_ref:
            if matches := re.finditer(patron, texto):
                for match in matches:
                    ref = match.group(1).strip()
                    if len(ref) > 3 and ref not in referencias:  # Evitar referencias muy cortas o duplicadas
                        referencias.append(ref)
        
        ubicacion["referencias"] = referencias
        
        return ubicacion

    def extraer_caracteristicas(self, texto: str) -> Dict[str, Union[int, float, str]]:
        """
        Extrae características detalladas de la propiedad.
        """
        caract = {
            "tipo_propiedad": "",
            "tipo_operacion": "",
            "superficie_terreno": 0,
            "superficie_construccion": 0,
            "recamaras": 0,
            "banos": 0,
            "estacionamientos": 0,
            "niveles": 0,
            "edad_propiedad": 0,
            "estado_conservacion": "",
            "orientacion": "",
            "amenidades": []
        }
        
        texto = texto.lower()
        
        # Detectar tipo de propiedad
        tipos_prop = {
            TipoPropiedad.CASA: [r"casa", r"chalet", r"residencia"],
            TipoPropiedad.DEPARTAMENTO: [r"departamento", r"depto", r"flat"],
            TipoPropiedad.TERRENO: [r"terreno", r"lote", r"predio"],
            TipoPropiedad.LOCAL: [r"local", r"comercial"],
            TipoPropiedad.OFICINA: [r"oficina", r"consultorio"],
            TipoPropiedad.BODEGA: [r"bodega", r"nave"]
        }
        
        for tipo, patrones in tipos_prop.items():
            if any(re.search(p, texto) for p in patrones):
                caract["tipo_propiedad"] = tipo.value
                break
        
        # Extraer superficies
        if match := re.search(r"terreno\s*(?:de)?\s*(\d+)\s*m?2?", texto):
            sup = int(match.group(1))
            if SUPERFICIE_MIN <= sup <= SUPERFICIE_MAX:
                caract["superficie_terreno"] = sup
                
        if match := re.search(r"construc(?:ción|cion)\s*(?:de)?\s*(\d+)\s*m?2?", texto):
            sup = int(match.group(1))
            if CONSTRUCCION_MIN <= sup <= CONSTRUCCION_MAX:
                caract["superficie_construccion"] = sup
        
        # Extraer recámaras y baños
        if match := re.search(r"(\d+)\s*(?:recámaras?|recamaras?|habitaciones?)", texto):
            caract["recamaras"] = int(match.group(1))
            
        if match := re.search(r"(\d+)\s*(?:baños?|banos?)", texto):
            caract["banos"] = int(match.group(1))
        
        # Extraer estacionamientos
        if match := re.search(r"(\d+)\s*(?:estacionamientos?|cajones?|lugares?)", texto):
            caract["estacionamientos"] = int(match.group(1))
        
        # Extraer niveles
        if match := re.search(r"(\d+)\s*(?:niveles?|pisos?|plantas?)", texto):
            caract["niveles"] = int(match.group(1))
        
        # Detectar amenidades
        amenidades_patrones = {
            "alberca": [r"alberca", r"piscina"],
            "jardin": [r"jardín", r"jardin", r"área verde"],
            "seguridad": [r"seguridad", r"vigilancia", r"24/7"],
            "gimnasio": [r"gimnasio", r"gym"],
            "terraza": [r"terraza", r"roof garden"],
            "aire_acondicionado": [r"aire acondicionado", r"clima"],
            "cocina_equipada": [r"cocina equipada", r"cocina integral"]
        }
        
        for amenidad, patrones in amenidades_patrones.items():
            if any(re.search(p, texto) for p in patrones):
                caract["amenidades"].append(amenidad)
        
        return caract

    def validar_propiedad(self, propiedad: Dict) -> Tuple[bool, List[str]]:
        """
        Valida que una propiedad tenga todos los campos requeridos y valores válidos.
        """
        errores = []
        
        # Validar campos requeridos
        campos_requeridos = ["id", "url", "tipo_propiedad", "tipo_operacion", "precio", "ubicacion"]
        for campo in campos_requeridos:
            if not propiedad.get(campo):
                errores.append(f"Falta el campo requerido: {campo}")
            
        # Validar precio
        precio = propiedad.get("precio", {}).get("valor", 0)
        if isinstance(precio, (int, float)):
            if propiedad["tipo_operacion"] == TipoOperacion.VENTA.value:
                if not (PRECIO_MIN_VENTA <= precio <= PRECIO_MAX_VENTA):
                    errores.append(f"Precio de venta fuera de rango: {precio}")
            elif propiedad["tipo_operacion"] == TipoOperacion.RENTA.value:
                if not (PRECIO_MIN_RENTA <= precio <= PRECIO_MAX_RENTA):
                    errores.append(f"Precio de renta fuera de rango: {precio}")
        else:
            errores.append("Precio inválido")
        
        # Validar ubicación
        ubicacion = propiedad.get("ubicacion", {})
        if not ubicacion.get("ciudad"):
            errores.append("Falta la ciudad en la ubicación")
        
        # Validar características
        caracteristicas = propiedad.get("caracteristicas", {})
        if not caracteristicas.get("tipo_propiedad"):
            errores.append("Falta el tipo de propiedad")
        
        return len(errores) == 0, errores

    def calcular_score_calidad(self, propiedad: Dict) -> Score:
        """
        Calcula un score de calidad para los datos de la propiedad.
        """
        score = Score()
        
        # Evaluar completitud (40%)
        campos_criticos = [
            "tipo_propiedad", "tipo_operacion", "precio",
            "superficie_terreno", "ubicacion"
        ]
        campos_importantes = [
            "superficie_construccion", "recamaras", "banos",
            "estacionamientos", "niveles"
        ]
        
        completitud = 0
        for campo in campos_criticos:
            if campo in propiedad and propiedad[campo]:
                completitud += 2  # Peso doble para campos críticos
        for campo in campos_importantes:
            if campo in propiedad and propiedad[campo]:
                completitud += 1
                
        score.completitud = (completitud / (len(campos_criticos) * 2 + len(campos_importantes))) * 100
        
        # Evaluar coherencia (30%)
        coherencia = 100
        if propiedad.get("superficie_construccion", 0) > propiedad.get("superficie_terreno", 0):
            coherencia -= 30
        if propiedad.get("niveles", 0) > 0 and not propiedad.get("superficie_construccion"):
            coherencia -= 20
        if propiedad.get("recamaras", 0) > propiedad.get("niveles", 1) * 5:
            coherencia -= 20
            
        score.coherencia = max(0, coherencia)
        
        # Evaluar calidad de datos (30%)
        calidad = 100
        ubicacion = propiedad.get("ubicacion", {})
        if not ubicacion.get("colonia"):
            calidad -= 20
        if not ubicacion.get("referencias"):
            calidad -= 10
        if not propiedad.get("amenidades"):
            calidad -= 10
        if not propiedad.get("estado_conservacion"):
            calidad -= 10
            
        score.calidad_datos = max(0, calidad)
        
        return score

    def procesar_propiedad(self, id_prop: str, datos: Dict) -> Optional[Dict]:
        """
        Procesa una propiedad completa con validación y scoring.
        """
        try:
            # Extraer texto de descripción
            if isinstance(datos.get("descripcion"), dict):
                texto_descripcion = str(datos["descripcion"].get("texto_original", "")) or str(datos["descripcion"].get("texto_limpio", ""))
            else:
                texto_descripcion = str(datos.get("descripcion", ""))
            
            titulo = str(datos.get("titulo", ""))
            texto_completo = f"{titulo}\n{texto_descripcion}"
            
            # Verificar si es una propiedad válida
            if not self.es_propiedad_valida(texto_completo):
                self.errores.append(f"Propiedad {id_prop}: No parece ser una propiedad inmobiliaria")
                return None
            
            # Determinar tipo de operación
            self.tipo_operacion = self.extraer_tipo_operacion(texto_completo)
            
            # Normalizar precio
            precio_datos = datos.get("precio", {})
            if isinstance(precio_datos, dict):
                precio_texto = str(precio_datos.get("texto_original", "")) or str(precio_datos.get("valor", ""))
            else:
                precio_texto = str(precio_datos)
            
            precio, moneda, precio_valido = self.normalizar_precio(precio_texto)
            
            if not precio_valido:
                # Intentar extraer precio de la descripción
                match = re.search(r'\$[\d,.]+[kKmM]?', texto_completo)
                if match:
                    precio, moneda, precio_valido = self.normalizar_precio(match.group())
                
            if not precio_valido:
                self.errores.append(f"Propiedad {id_prop}: Precio inválido")
                return None
            
            # Extraer ubicación
            ubicacion = datos.get("ubicacion", {})
            if not isinstance(ubicacion, dict):
                ubicacion = {}
            
            if not ubicacion.get("ciudad"):
                ubicacion = self.extraer_ubicacion(texto_completo)
            
            if not ubicacion.get("ciudad"):
                self.errores.append(f"Propiedad {id_prop}: No se pudo determinar la ciudad")
                return None
            
            # Extraer características
            caracteristicas = datos.get("caracteristicas", {})
            if not isinstance(caracteristicas, dict):
                caracteristicas = {}
            
            if not caracteristicas:
                caracteristicas = self.extraer_caracteristicas(texto_completo)
            
            # Determinar niveles
            caracteristicas["niveles"] = self.extraer_niveles(texto_completo)
            
            # Extraer datos del vendedor
            vendedor = self.extraer_datos_vendedor(datos)
            
            # Si no hay datos del vendedor, intentar extraerlos del texto
            if not vendedor.get("nombre") and not vendedor.get("perfil"):
                # Buscar patrones de contacto
                contacto_match = re.search(r'(?:informes?|contacto|mayores?\s+informes?|tel(?:éfono)?|cel(?:ular)?|whats(?:app)?|llamar?)[\s:]+([^\.]+)', texto_completo, re.I)
                if contacto_match:
                    vendedor["nombre"] = contacto_match.group(1).strip()
                    vendedor["tipo"] = "particular"
                else:
                    # Buscar nombres propios (palabras capitalizadas)
                    nombres = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}\b', texto_completo)
                    if nombres:
                        vendedor["nombre"] = nombres[0]
                        vendedor["tipo"] = "particular"
            
            # Construir objeto de propiedad
            propiedad = {
                "id": id_prop,
                "url": datos.get("url", "") or datos.get("link", ""),
                "fecha_extraccion": datos.get("fecha_extraccion", datetime.now().isoformat()),
                "tipo_propiedad": caracteristicas.get("tipo_propiedad", ""),
                "tipo_operacion": self.tipo_operacion.value,
                "precio": {
                    "valor": precio,
                    "moneda": moneda,
                    "original": precio_texto
                },
                "ubicacion": ubicacion,
                "caracteristicas": caracteristicas,
                "descripcion_original": texto_completo,
                "metadata": {
                    "vendedor": vendedor,
                    "estado_listado": datos.get("metadata", {}).get("estado_listado", "activo"),
                    "ultima_actualizacion": datos.get("metadata", {}).get("ultima_actualizacion", "")
                }
            }
            
            # Validar campos
            errores = self.validar_campos(propiedad)
            if errores:
                self.errores.extend([f"Propiedad {id_prop}: {error}" for error in errores])
                return None
            
            # Calcular score de calidad
            score = self.calcular_score_calidad(propiedad)
            propiedad["metadata"]["score_calidad"] = {
                "total": score.total,
                "detalle": {
                    "completitud": score.completitud,
                    "coherencia": score.coherencia,
                    "calidad_datos": score.calidad_datos
                }
            }
            
            return propiedad
            
        except Exception as e:
            self.errores.append(f"Error procesando propiedad {id_prop}: {str(e)}")
            return None

    def extraer_tipo_operacion(self, texto: str) -> TipoOperacion:
        """
        Extrae el tipo de operación (venta/renta) del texto.
        """
        texto = texto.lower()
        
        # Patrones de venta
        patrones_venta = [
            r'\b(?:en\s+)?venta\b',
            r'\bvendo\b',
            r'\bse\s+vende\b',
            r'\bprecio\s+de\s+venta\b',
            r'\bprecio\s+final\b',
            r'\bprecio\s+total\b',
            r'\bprecio\s+negociable\b',
            r'\bprecio\s+a\s+tratar\b',
            r'\bprecio\s+de\s+oportunidad\b',
            r'\bremato\b',
            r'\boportunidad\b',
            r'\binversión\b',
            r'\binversion\b',
            r'\bescrituras?\b',
            r'\bcreditos?\s+(?:hipotecarios?|bancarios?|infonavit|fovissste)\b'
        ]
        
        # Patrones de renta
        patrones_renta = [
            r'\b(?:en\s+)?renta\b',
            r'\balquiler\b',
            r'\barriendo\b',
            r'\bse\s+renta\b',
            r'\bse\s+alquila\b',
            r'\brento\b',
            r'\bprecio\s+mensual\b',
            r'\bpor\s+mes\b',
            r'\b/\s*mes\b',
            r'\bmensual(?:es|idad)?\b',
            r'\bdeposito\s+(?:en\s+)?garantia\b',
            r'\bfianza\b',
            r'\baval\b',
            r'\bcontrato\s+(?:minimo|de\s+arrendamiento)\b'
        ]
        
        # Buscar patrones de venta
        for patron in patrones_venta:
            if re.search(patron, texto):
                return TipoOperacion.VENTA
            
        # Buscar patrones de renta
        for patron in patrones_renta:
            if re.search(patron, texto):
                return TipoOperacion.RENTA
            
        # Si no se encontró un patrón claro, intentar inferir por el precio
        precio_match = re.search(r'[\$]?\s*([\d,.]+)(?:k|m|mil|millon(?:es)?)?', texto)
        if precio_match:
            precio_str = precio_match.group(1).replace(',', '').replace('.', '')
            try:
                precio = float(precio_str)
                # Si el precio es alto, probablemente es venta
                if precio >= 500000:
                    return TipoOperacion.VENTA
                # Si el precio está en rango típico de renta
                elif 3000 <= precio <= 50000:
                    return TipoOperacion.RENTA
            except ValueError:
                pass
            
        # Por defecto, asumimos venta
        return TipoOperacion.VENTA

    def extraer_tipo_propiedad(self, texto: str) -> str:
        """
        Extrae el tipo de propiedad del texto.
        """
        texto = texto.lower()
        
        # Patrones para cada tipo de propiedad
        patrones = {
            "Casa": [
                r'\bcasa\b',
                r'\bchalet\b',
                r'\bvilla\b',
                r'\bresidencia\b'
            ],
            "Departamento": [
                r'\bdepartamento\b',
                r'\bdepto\b',
                r'\bapartamento\b',
                r'\bapto\b',
                r'\bmonoambiente\b',
                r'\bpent\s*house\b',
                r'\bloft\b'
            ],
            "Terreno": [
                r'\bterreno\b',
                r'\blote\b',
                r'\bparcela\b',
                r'\bpredio\b'
            ],
            "Local": [
                r'\blocal\b',
                r'\bcomercial\b',
                r'\btienda\b',
                r'\bbodega\b',
                r'\balmacén\b'
            ],
            "Oficina": [
                r'\boficina\b',
                r'\bconsultorio\b',
                r'\bdespacho\b'
            ]
        }
        
        # Buscar patrones
        for tipo, lista_patrones in patrones.items():
            for patron in lista_patrones:
                if re.search(patron, texto):
                    return tipo
                
        # Si no encontramos ningún patrón específico,
        # intentamos inferir por otras características
        if any(term in texto for term in ['recámara', 'recamara', 'habitación', 'habitacion', 'baño', 'cocina']):
            return "Casa"  # Por defecto asumimos casa si tiene características de vivienda
        
        return ""  # Si no podemos determinar el tipo

    def es_propiedad_valida(self, texto: str) -> bool:
        """
        Determina si una publicación es realmente una propiedad inmobiliaria.
        """
        texto = texto.lower()
        
        # Palabras clave que indican que NO es una propiedad
        no_propiedad = [
            # Vehículos
            r'\b(?:auto(?:movil)?|carro|coche|camioneta|moto(?:cicleta)?|camion|trailer)\b',
            
            # Electrónicos
            r'\b(?:celular|telefono|smartphone|tablet|laptop|computadora|pc|tv|television)\b',
            
            # Muebles individuales (solo si están solos)
            r'^\s*(?:sillon|mesa|silla|cama|sofa|comedor)\s*$',
            
            # Ropa y accesorios
            r'\b(?:ropa|zapatos?|tenis|playera|pantalon|vestido|bolsa|reloj)\b',
            
            # Electrodomésticos (solo si están solos)
            r'^\s*(?:refrigerador|lavadora|secadora|estufa|microondas|licuadora)\s*$',
            
            # Otros productos
            r'\b(?:juguetes?|cosmeticos?|perfumes?|maquillaje|herramientas?)\b'
        ]
        
        # Si encuentra alguna palabra clave de no propiedad, verificar que no sea parte de una descripción de propiedad
        for patron in no_propiedad:
            if re.search(patron, texto):
                # Verificar si también tiene palabras clave de propiedad
                if not any(re.search(p, texto) for p in [
                    r'\b(?:casa|depa(?:rtamento)?|terreno|local|oficina|bodega|inmueble)\b',
                    r'\b(?:recamara|habitacion|dormitorio)\b',
                    r'\b(?:baño|sanitario|wc)\b',
                    r'\b(?:metros?(?:\s*2|\s+cuadrados)?|m2)\b'
                ]):
                    return False
        
        # Palabras clave que indican que SÍ es una propiedad
        palabras_propiedad = [
            r'\b(?:casa|depa(?:rtamento)?|terreno|local|oficina|bodega|inmueble)\b',
            r'\b(?:recamara|habitacion|dormitorio)\b',
            r'\b(?:baño|sanitario|wc)\b',
            r'\b(?:sala|comedor|cocina)\b',
            r'\b(?:metros?(?:\s*2|\s+cuadrados)?|m2)\b',
            r'\b(?:construccion|terreno|superficie)\b',
            r'\b(?:estacionamiento|cochera|garage)\b',
            r'\b(?:venta|renta|alquiler)\b',
            r'\b(?:propiedad|inmueble|finca)\b',
            r'\b(?:escrituras?|credito|infonavit|fovissste)\b',
            r'\b(?:fraccionamiento|condominio|privada)\b',
            r'\b(?:alberca|jardin|terraza)\b'
        ]
        
        # Debe contener al menos 1 palabra clave de propiedad
        palabras_encontradas = sum(1 for patron in palabras_propiedad if re.search(patron, texto))
        if palabras_encontradas < 1:
            return False
        
        # Verificar si tiene características típicas de una propiedad
        tiene_precio = bool(re.search(r'\$[\d,.]+', texto))
        tiene_ubicacion = bool(re.search(r'\b(?:ubicad[oa]|cerca\s+de|colonia|fraccionamiento|calle)\b', texto))
        tiene_medidas = bool(re.search(r'\d+\s*(?:m2|metros?(?:\s+cuadrados)?)', texto))
        
        # Debe cumplir al menos 1 de las 3 características
        caracteristicas_cumplidas = sum([tiene_precio, tiene_ubicacion, tiene_medidas])
        return caracteristicas_cumplidas >= 1

    def extraer_datos_vendedor(self, datos: Dict) -> Dict:
        """
        Extrae y normaliza los datos del vendedor.
        """
        vendedor = {
            "nombre": "",
            "perfil": "",
            "tipo": "desconocido",
            "telefono": "",
            "correo": ""
        }
        
        # Extraer del campo metadata si existe
        if "metadata" in datos and "vendedor" in datos["metadata"]:
            metadata_vendedor = datos["metadata"]["vendedor"]
            vendedor["nombre"] = metadata_vendedor.get("nombre", "").strip()
            vendedor["perfil"] = metadata_vendedor.get("perfil", "").strip()
            vendedor["tipo"] = metadata_vendedor.get("tipo", "desconocido")
            
        # Si el perfil es un link corto de Facebook, expandirlo
        if vendedor["perfil"] and "l.facebook.com" in vendedor["perfil"]:
            vendedor["perfil"] = vendedor["perfil"].replace("l.facebook.com/l.php?", "www.facebook.com")
            
        # Determinar tipo de vendedor
        texto_completo = (
            datos.get("titulo", "") + " " +
            datos.get("descripcion", "") + " " +
            vendedor["nombre"]
        ).lower()
        
        # Patrones para identificar inmobiliarias
        patrones_inmobiliaria = [
            r'\b(?:inmobiliari[ao]|bienes\s+raices|real\s+estate)\b',
            r'\b(?:asesor(?:es)?|broker|agente(?:s)?)\b',
            r'\b(?:propiedades|realty|realtors?)\b',
            r'\b(?:century\s*21|coldwell|remax|keller\s*williams)\b'
        ]
        
        # Patrones para identificar particulares
        patrones_particular = [
            r'\b(?:dueño|propietario|particular)\b',
            r'\b(?:vendo|rento)\s+(?:mi|directo)\b',
            r'\btrato\s+directo\b',
            r'\bsin\s+intermediarios\b'
        ]
        
        # Verificar patrones
        for patron in patrones_inmobiliaria:
            if re.search(patron, texto_completo):
                vendedor["tipo"] = "inmobiliaria"
                break
            
        for patron in patrones_particular:
            if re.search(patron, texto_completo):
                vendedor["tipo"] = "particular"
                break
            
        # Extraer teléfono si existe
        telefono_match = re.search(r'(?:tel(?:efono)?|cel(?:ular)?|whats(?:app)?|contacto)?\s*[:\s]?\s*((?:\+?52\s*)?(?:1\s*)?[0-9]{3}[\s-]*[0-9]{3}[\s-]*[0-9]{4})', texto_completo)
        if telefono_match:
            vendedor["telefono"] = telefono_match.group(1).strip()
        
        # Extraer correo si existe
        correo_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', texto_completo)
        if correo_match:
            vendedor["correo"] = correo_match.group().strip()
        
        return vendedor

    def extraer_niveles(self, texto: str) -> int:
        """
        Determina el número de niveles/plantas de una propiedad.
        """
        texto = texto.lower()
        
        # Patrones que NO indican niveles
        no_niveles = [
            r'(?:excelente|buen|alto|mejor)\s+nivel',
            r'nivel\s+(?:social|economico|alto|medio|bajo)',
            r'nivel\s+de\s+(?:acabados|calidad|vida)',
            r'primer\s+nivel\s+de\s+calidad'
        ]
        
        # Si encuentra patrones que no indican niveles, ignorarlos
        for patron in no_niveles:
            texto = re.sub(patron, '', texto)
        
        # Patrones específicos de niveles
        patrones_niveles = [
            # Menciones explícitas
            (r'(?:de|con|en)\s+(\d+)\s+(?:nivele?s?|plantas?|pisos?)', lambda m: int(m.group(1))),
            (r'(\d+)\s+(?:nivele?s?|plantas?|pisos?)', lambda m: int(m.group(1))),
            
            # Referencias a plantas específicas
            (r'planta\s+(?:baja|principal).*planta\s+alta', lambda m: 2),
            (r'primer\s+piso.*segundo\s+piso', lambda m: 2),
            (r'p\.?b\.?.*p\.?a\.?', lambda m: 2),  # PB y PA
            
            # Referencias a escaleras/escalones
            (r'escaleras?\s+(?:a|hacia|para)\s+(?:segundo|2do)', lambda m: 2),
            (r'escaleras?\s+(?:interiores?|principales?)', lambda m: 2),
            
            # Referencias a áreas en diferentes niveles
            (r'(?:recamaras?|habitaciones?)\s+(?:en|arriba|planta\s+alta)', lambda m: 2),
            (r'(?:sala|comedor|cocina)\s+(?:abajo|planta\s+baja)', lambda m: 2)
        ]
        
        # Buscar patrones específicos
        for patron, extractor in patrones_niveles:
            if match := re.search(patron, texto):
                return extractor(match)
        
        # Buscar referencias indirectas
        referencias_dos_niveles = [
            r'arriba.*abajo',
            r'planta\s+(?:baja|principal)',  # Si menciona planta baja, implica más de un nivel
            r'primer\s+piso',  # Similar a planta baja
            r'segundo\s+piso',
            r'planta\s+alta',
            r'tapanco',
            r'mezanine',
            r'duplex',
            r'dos\s+plantas'
        ]
        
        for patron in referencias_dos_niveles:
            if re.search(patron, texto):
                return 2
            
        # Si no hay indicadores claros, asumimos un nivel
        return 1

    def validar_campos(self, propiedad: Dict) -> List[str]:
        """
        Valida todos los campos extraídos y retorna una lista de errores encontrados.
        """
        errores = []
        
        # Validar campos requeridos
        campos_requeridos = ["id", "tipo_propiedad", "tipo_operacion", "precio", "ubicacion"]
        for campo in campos_requeridos:
            if campo not in propiedad:
                errores.append(f"Falta el campo requerido: {campo}")
            
        # Validar precio
        precio = propiedad.get("precio", {})
        if not isinstance(precio, dict):
            errores.append("El precio debe ser un diccionario")
        else:
            if "valor" not in precio:
                errores.append("Falta el valor del precio")
            elif not isinstance(precio["valor"], (int, float)) or precio["valor"] <= 0:
                errores.append("El valor del precio es inválido")
            
            if "moneda" not in precio:
                errores.append("Falta la moneda del precio")
            elif precio["moneda"] not in ["MXN", "USD"]:
                errores.append("Moneda inválida")
            
        # Validar ubicación
        ubicacion = propiedad.get("ubicacion", {})
        if not isinstance(ubicacion, dict):
            errores.append("La ubicación debe ser un diccionario")
        else:
            if not ubicacion.get("ciudad"):
                errores.append("Falta la ciudad")
            
        # Validar características
        caracteristicas = propiedad.get("caracteristicas", {})
        if not isinstance(caracteristicas, dict):
            errores.append("Las características deben ser un diccionario")
        else:
            # Validar recámaras
            recamaras = caracteristicas.get("recamaras", 0)
            if not isinstance(recamaras, (int, float)) or recamaras < 0:
                errores.append("Número de recámaras inválido")
            elif recamaras > 10:  # Valor máximo razonable
                errores.append("Número de recámaras sospechosamente alto")
            
            # Validar baños
            banos = caracteristicas.get("banos", 0)
            if not isinstance(banos, (int, float)) or banos < 0:
                errores.append("Número de baños inválido")
            elif banos > 10:  # Valor máximo razonable
                errores.append("Número de baños sospechosamente alto")
            
            # Validar superficies
            terreno = caracteristicas.get("superficie_terreno", 0)
            construccion = caracteristicas.get("superficie_construccion", 0)
            if terreno > 0 and construccion > terreno:
                errores.append("La superficie de construcción no puede ser mayor que la del terreno")
            
            # Validar niveles
            niveles = caracteristicas.get("niveles", 0)
            if niveles <= 0:
                caracteristicas["niveles"] = self.extraer_niveles(propiedad.get("descripcion_original", ""))
            
        # Validar vendedor
        vendedor = propiedad.get("metadata", {}).get("vendedor", {})
        if not isinstance(vendedor, dict):
            errores.append("Los datos del vendedor deben ser un diccionario")
        else:
            if not vendedor.get("nombre") and not vendedor.get("perfil"):
                errores.append("Faltan datos del vendedor")
            
        # Validar coherencia de datos
        if propiedad.get("tipo_operacion") == "venta":
            precio_min = 300_000
            precio_max = 50_000_000
        else:  # renta
            precio_min = 3_000
            precio_max = 500_000
        
        valor_precio = precio.get("valor", 0)
        if valor_precio < precio_min or valor_precio > precio_max:
            errores.append(f"Precio fuera de rango para {propiedad['tipo_operacion']}")
        
        return errores

def procesar_repositorio(ruta_entrada: str = "resultados/repositorio_propiedades.json",
                        ruta_salida: str = "resultados/propiedades_procesadas.json") -> None:
    """
    Procesa el repositorio completo de propiedades.
    """
    try:
        # Cargar repositorio
        with open(ruta_entrada, 'r', encoding='utf-8') as f:
            repositorio = json.load(f)
            
        extractor = ExtractorMejorado()
        propiedades_procesadas = []
        stats = {
            "total": len(repositorio),
            "procesadas": 0,
            "errores": 0,
            "score_promedio": 0.0
        }
        
        # Procesar cada propiedad
        for id_prop, datos in repositorio.items():
            if propiedad := extractor.procesar_propiedad(id_prop, datos):
                propiedades_procesadas.append(propiedad)
                stats["procesadas"] += 1
                stats["score_promedio"] += propiedad["metadata"]["score_calidad"]["total"]
            else:
                stats["errores"] += 1
        
        # Calcular estadísticas finales
        if stats["procesadas"] > 0:
            stats["score_promedio"] /= stats["procesadas"]
        
        # Guardar resultados
        resultado = {
            "propiedades": propiedades_procesadas,
            "estadisticas": stats,
            "errores": extractor.errores,
            "fecha_procesamiento": datetime.now().isoformat()
        }
        
        with open(ruta_salida, 'w', encoding='utf-8') as f:
            json.dump(resultado, f, ensure_ascii=False, indent=2)
            
        print(f"\nProcesamiento completado:")
        print(f"- Total de propiedades: {stats['total']}")
        print(f"- Propiedades procesadas: {stats['procesadas']}")
        print(f"- Errores encontrados: {stats['errores']}")
        print(f"- Score promedio: {stats['score_promedio']:.2f}")
        
    except Exception as e:
        print(f"Error durante el procesamiento: {str(e)}")
        raise

if __name__ == "__main__":
    procesar_repositorio() 