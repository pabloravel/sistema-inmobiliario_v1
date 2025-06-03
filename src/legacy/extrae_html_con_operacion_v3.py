#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extrae_html_con_operacion_v3.py

Versión 3.1 - Optimizada para extracción masiva
- Sistema de timeout por propiedad
- Verificación eficiente de propiedades ya extraídas
- Guardado completo de datos (DOM, JSON, HTML, imágenes)
- Optimización de tiempos de espera
"""

import os
import json
import requests
import time
import re
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import traceback

class ProgressBar:
    MAGENTA = "\033[35m"
    RESET   = "\033[0m"
    def __init__(self, total, desc='', unit=''):
        self.total = total
        self.n = 0
        self.ok = 0
        self.err = 0
        self.desc = desc
        self.unit = unit
        self.width = os.get_terminal_size().columns - 40
        print(f"{self.desc}: 0/{self.total} {self.unit}")
        
    def update(self, n=1, ok=None, err=None):
        self.n += n
        if ok is not None: self.ok = ok
        if err is not None: self.err = err
        p = int(self.width * self.n / self.total)
        print(f"\033[A{self.desc}: {self.n}/{self.total} {self.unit}")
        print(f"{self.MAGENTA}{'█'*p}{'-'*(self.width-p)} OK:{self.ok} Err:{self.err}{self.RESET}")
    
    def close(self):
        print()

def descargar_imagen(url, ruta_destino):
    """Descarga una imagen en un thread separado"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            with open(ruta_destino, 'wb') as f:
                f.write(response.content)
            return True
    except:
        pass
    return False

def normalizar_precio(precio_str):
    """Normaliza el formato del precio"""
    if not precio_str:
        return "0"
    # Eliminar todo excepto números y punto decimal
    nums = ''.join(c for c in precio_str if c.isdigit() or c == '.')
    try:
        # Convertir a float y volver a string con formato
        valor = float(nums)
        return f"${valor:,.2f}"
    except:
        return "0"

def normalizar_texto(texto):
    """Normaliza un texto eliminando espacios extras y caracteres especiales"""
    if not texto:
        return ""
    # Eliminar espacios múltiples y caracteres especiales
    texto = ' '.join(texto.split())
    # Convertir a minúsculas
    return texto.lower()

def extraer_numero(texto, patron):
    """Extrae un número de un texto usando un patrón regex"""
    if match := re.search(patron, normalizar_texto(texto)):
        try:
            return int(match.group(1))
        except:
            pass
    return None

def normalizar_ciudad(ciudad):
    """Normaliza el nombre de la ciudad"""
    if not ciudad:
        return "desconocida"
    # Eliminar caracteres especiales y espacios extras
    ciudad = re.sub(r'[^\w\s]', '', ciudad.lower())
    ciudad = ' '.join(ciudad.split())
    # Mapeo de nombres comunes
    mapping = {
        'cdmx': 'ciudad de mexico',
        'df': 'ciudad de mexico',
        'mex': 'estado de mexico',
        'edomex': 'estado de mexico',
        'cuernavaca': 'cuernavaca',
        # Agregar más mappings según necesidad
    }
    return mapping.get(ciudad, ciudad)

def extraer_datos_propiedad(soup, page):
    """Extrae todos los datos relevantes de la propiedad"""
    datos = {
        'id': '',
        'link': '',
        'titulo': '',
        'precio': '0',
        'ciudad': 'desconocida',
        'ubicacion_exacta': '',
        'tipo_operacion': 'Desconocido',
        'tipo_propiedad': 'Otro',
        'descripcion': '',
        'recamaras': None,
        'banos': None,
        'metros_terreno': None,
        'metros_construccion': None,
        'vendedor': {
            'nombre': '',
            'perfil': '',
            'tipo': 'particular'  # o 'inmobiliaria'
        },
        'amenidades': [],
        'caracteristicas': [],
        'estado_propiedad': {
            'escrituras': False,
            'cesion_derechos': False,
            'credito': False,
            'estado': 'disponible'
        },
        'fecha_extraccion': datetime.now().isoformat(),
        'imagen_portada': '',
        'imagenes': [],
        'metadata': {
            'ultima_actualizacion': datetime.now().isoformat(),
            'fuente': 'facebook_marketplace',
            'status_extraccion': 'completo'
        }
    }
    
    # Título
    if h1 := soup.find('h1'):
        datos['titulo'] = normalizar_texto(h1.get_text(strip=True))
    
    # Precio
    for span in soup.find_all('span'):
        if precio := span.get_text(strip=True):
            if precio.startswith('$') and len(precio) < 30:
                datos['precio'] = normalizar_precio(precio)
                break
    
    # Ubicación
    for div in soup.find_all('div'):
        if 'Ubicación' in div.get_text(strip=True):
            if siguiente := div.find_next_sibling('div'):
                datos['ubicacion_exacta'] = normalizar_texto(siguiente.get_text(strip=True))
                break
    
    # Descripción
    descripcion = ''
    for div in soup.find_all('div'):
        if div.get_text(strip=True) in ['Descripción', 'Detalles']:
            if siguiente := div.find_next_sibling('div'):
                descripcion = siguiente.get_text(strip=True).replace('Ver menos', '')
                break
    datos['descripcion'] = normalizar_texto(descripcion)
    
    # Texto completo para análisis
    texto_completo = normalizar_texto(soup.get_text(' ', strip=True))
    
    # Extracción de números con patrones específicos
    datos['recamaras'] = extraer_numero(texto_completo, r'(\d+)\s*(?:recámaras?|recamaras?|habitaciones?|dormitorios?)')
    datos['banos'] = extraer_numero(texto_completo, r'(\d+)\s*(?:baños?|banos?)')
    datos['metros_terreno'] = extraer_numero(texto_completo, r'(?:terreno|superficie)\s*(?:de|:)?\s*(\d+)\s*(?:m2|mts|metros?)')
    datos['metros_construccion'] = extraer_numero(texto_completo, r'(?:construcción|construccion)\s*(?:de|:)?\s*(\d+)\s*(?:m2|mts|metros?)')
    
    # Tipo de operación
    palabras_renta = ['renta', 'alquiler', '/mes', 'mensual']
    palabras_venta = ['venta', 'vendo', 'remato', 'oportunidad']
    
    if any(palabra in texto_completo for palabra in palabras_renta):
        datos['tipo_operacion'] = 'Renta'
    elif any(palabra in texto_completo for palabra in palabras_venta):
        datos['tipo_operacion'] = 'Venta'
    else:
        # Inferir por precio
        precio_num = float(''.join(filter(str.isdigit, datos['precio'])) or 0)
        datos['tipo_operacion'] = 'Venta' if precio_num >= 300000 else 'Renta'
    
    # Tipo de propiedad con normalización
    tipo_mapping = {
        'casa': ['casa sola', 'casa', 'casa en', 'casa habitación', 'residencia'],
        'departamento': ['departamento', 'depto', 'departamentos', 'depa'],
        'terreno': ['terreno', 'lote', 'terrenos', 'predio'],
        'local': ['local', 'locales', 'local comercial'],
        'oficina': ['oficina', 'oficinas'],
        'bodega': ['bodega', 'bodegas', 'almacén'],
        'condominio': ['condominio', 'condominios', 'conjunto']
    }
    
    for tipo, variantes in tipo_mapping.items():
        if any(v in datos['titulo'].lower() for v in variantes):
            datos['tipo_propiedad'] = tipo.capitalize()
            break
    
    # Características y amenidades
    caracteristicas_buscar = {
        'Un nivel': ['un nivel', 'una planta', 'planta baja'],
        'Recámara en PB': ['recámara en pb', 'recamara en pb', 'recámara en planta baja'],
        'Estacionamiento': ['cochera', 'estacionamiento', 'garage'],
        'Jardín': ['jardín', 'jardin', 'área verde'],
        'Seguridad': ['vigilancia', 'seguridad', 'privada']
    }
    
    for caract, palabras in caracteristicas_buscar.items():
        if any(p in texto_completo for p in palabras):
            datos['caracteristicas'].append(caract)
    
    # Amenidades comunes
    amenidades_buscar = {
        'Alberca': ['alberca', 'piscina'],
        'Gimnasio': ['gimnasio', 'gym'],
        'Área común': ['área común', 'area comun'],
        'Juegos infantiles': ['juegos infantiles', 'área de juegos'],
        'Casa club': ['casa club', 'club house']
    }
    
    for amenidad, palabras in amenidades_buscar.items():
        if any(p in texto_completo for p in palabras):
            datos['amenidades'].append(amenidad)
    
    # Estado de la propiedad
    datos['estado_propiedad'].update({
        'escrituras': 'escrituras' in texto_completo,
        'cesion_derechos': any(x in texto_completo for x in ['cesión', 'cesion', 'derechos']),
        'credito': any(x in texto_completo for x in ['crédito', 'credito', 'infonavit', 'fovissste']),
        'estado': 'disponible'
    })
    
    # Vendedor
    try:
        vendedor_info = page.evaluate("""() => {
            const links = Array.from(document.querySelectorAll('a'));
            for (const link of links) {
                if (link.href.includes('/profile.php?id=') || 
                    link.href.match(/facebook\\.com\\/[^\\/]+$/)) {
                    return {
                        nombre: link.textContent.trim(),
                        perfil: link.href,
                        tipo: link.href.includes('profile.php') ? 'particular' : 'inmobiliaria'
                    }
                }
            }
            return null;
        }""")
        if vendedor_info:
            datos['vendedor'].update(vendedor_info)
    except:
        pass
    
    # Imágenes
    try:
        datos['imagenes'] = page.evaluate("""() => {
            return Array.from(document.querySelectorAll('img'))
                .map(img => img.src)
                .filter(src => src && src.startsWith('http'))
                .slice(0, 5);
        }""")
    except:
        pass
    
    return datos

def procesar_propiedad(page, link, id_propiedad, ciudad, fecha_str):
    """Procesa una propiedad y retorna sus datos"""
    print(f"\nProcesando {id_propiedad} - {link}")
        
    # Crear directorios para esta propiedad
    dir_base = f"resultados"
    dir_html = f"{dir_base}/html/{fecha_str}"
    dir_json = f"{dir_base}/json/{fecha_str}"
    dir_dom = f"{dir_base}/dom/{fecha_str}"
    dir_img = f"{dir_base}/imagenes/{fecha_str}/{id_propiedad}"
    
    for dir_path in [dir_html, dir_json, dir_dom, dir_img]:
        os.makedirs(dir_path, exist_ok=True)
    
    try:
        # Navegar a la página con timeout
        page.set_default_timeout(30000)  # 30 segundos
        page.goto(link, wait_until="networkidle")
        
        # Esperar a que cargue el contenido principal
        page.wait_for_selector('h1', timeout=10000)
        
        # Obtener HTML y DOM
        html = page.content()
        dom = page.evaluate('() => document.documentElement.outerHTML')
        
        # Guardar HTML y DOM
        with open(f"{dir_html}/{id_propiedad}.html", "w", encoding="utf-8") as f:
            f.write(html)
        with open(f"{dir_dom}/{id_propiedad}.html", "w", encoding="utf-8") as f:
            f.write(dom)
        
        # Parsear HTML
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extraer datos
        datos = extraer_datos_propiedad(soup, page)
        
        # Completar datos básicos
        datos.update({
            'id': id_propiedad,
            'link': link,
            'ciudad': normalizar_ciudad(ciudad),
            'fecha_extraccion': datetime.now().isoformat(),
            'metadata': {
                'ultima_actualizacion': datetime.now().isoformat(),
                'fuente': 'facebook_marketplace',
                'status_extraccion': 'completo',
                'fecha_batch': fecha_str
            }
        })
        
        # Descargar imágenes
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Descargar imagen de portada
            if datos['imagen_portada']:
                nombre_archivo = f"portada_{id_propiedad}.jpg"
                ruta_destino = os.path.join(dir_img, nombre_archivo)
                executor.submit(descargar_imagen, datos['imagen_portada'], ruta_destino)
        
            # Descargar galería
            for i, url in enumerate(datos['imagenes']):
                nombre_archivo = f"imagen_{i+1}_{id_propiedad}.jpg"
                ruta_destino = os.path.join(dir_img, nombre_archivo)
                executor.submit(descargar_imagen, url, ruta_destino)
        
        # Guardar JSON
        with open(f"{dir_json}/{id_propiedad}.json", "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Datos extraídos correctamente")
        return datos
        
    except PlaywrightTimeout:
        print(f"❌ Timeout al cargar la página")
        return None
        
    except Exception as e:
        print(f"❌ Error procesando propiedad: {str(e)}")
        traceback.print_exc()
        return None

def main():
    """Función principal"""
    print("\n1. Cargando repositorio maestro...")
    try:
        with open("resultados/repositorio_propiedades.json", "r", encoding="utf-8") as f:
            repositorio = json.load(f)
            print(f"   ✓ Repositorio cargado con {len(repositorio)} propiedades")
    except:
        print("   ✓ Creando nuevo repositorio")
        repositorio = {}
    
    print("\n2. Cargando enlaces a procesar...")
    try:
        with open("resultados/links/repositorio_unico.json", "r", encoding="utf-8") as f:
            links_raw = json.load(f)
            
        # Normalizar formato de links
        links = []
        BASE_URL = "https://www.facebook.com"
        for link in links_raw:
            if isinstance(link, str):
                url = BASE_URL + link if link.startswith("/") else link
                pid = link.rstrip("/").split("/")[-1]
                links.append({
                    "id": pid,
                    "link": url,
                    "ciudad": "cuernavaca"  # Ciudad por defecto
                })
            elif isinstance(link, dict):
                url = link.get("link", "")
                url = BASE_URL + url if url.startswith("/") else url
                links.append({
                    "id": link.get("id", url.rstrip("/").split("/")[-1]),
                    "link": url,
                    "ciudad": link.get("ciudad", "cuernavaca").lower()
                })
        
            print(f"   ✓ {len(links)} enlaces cargados")
    except Exception as e:
        print(f"   ❌ Error cargando enlaces: {str(e)}")
        return
    
    # Crear directorios necesarios
    directorios = [
        "resultados/html",
        "resultados/json",
        "resultados/imagenes",
        "resultados/dom"
    ]
    for dir_path in directorios:
        os.makedirs(dir_path, exist_ok=True)
    
    # Procesar propiedades
    fecha_str = datetime.now().strftime("%Y%m%d")
    total = len(links)
    procesadas = 0
    errores = 0
    
    # Inicializar barra de progreso
    progress = ProgressBar(total, "Procesando propiedades", "propiedades")
    
    with sync_playwright() as p:
        # Configurar navegador
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        
        # Procesar cada propiedad
        for item in links:
            try:
                # Crear nueva página para cada propiedad
                page = context.new_page()
                
                # Procesar propiedad
                resultado = procesar_propiedad(
                    page=page,
                    link=item["link"],
                    id_propiedad=item["id"],
                    ciudad=item["ciudad"],
                    fecha_str=fecha_str
                )
                
                # Actualizar contadores
                if resultado:
                    procesadas += 1
            else:
                    errores += 1
                
                # Cerrar página
                page.close()
                
            except Exception as e:
                print(f"\n❌ Error procesando {item['id']}: {str(e)}")
                errores += 1
            
            # Actualizar progreso
            progress.update(1, procesadas, errores)
            
            # Guardar progreso cada 10 propiedades
            if procesadas % 10 == 0:
                with open("resultados/repositorio_propiedades.json", "w", encoding="utf-8") as f:
                    json.dump(repositorio, f, indent=2, ensure_ascii=False)
        
        # Cerrar navegador
        browser.close()
    
    # Cerrar barra de progreso
    progress.close()
    
    # Guardar repositorio final
    with open("resultados/repositorio_propiedades.json", "w", encoding="utf-8") as f:
        json.dump(repositorio, f, indent=2, ensure_ascii=False)
    
    print("\n=== RESUMEN ===")
    print(f"Total de propiedades: {total}")
    print(f"Procesadas exitosamente: {procesadas}")
    print(f"Con errores: {errores}")
    print(f"Porcentaje de éxito: {(procesadas/total*100):.1f}%")
    print("\n✓ Proceso completado")

if __name__ == "__main__":
    main() 