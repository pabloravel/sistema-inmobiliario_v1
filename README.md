# Facebook Property Scraper

Scraper y procesador de propiedades inmobiliarias de Facebook Marketplace.

## Características

- Extracción automática de propiedades de Facebook Marketplace
- Procesamiento y estructuración de datos
- Detección automática de tipo de operación (venta/renta)
- Análisis de precios y características
- Interfaz web para visualización de resultados

## Estructura del Proyecto

```
facebook_scraper/
├── src/                    # Código fuente principal
├── tests/                  # Pruebas unitarias
├── docs/                   # Documentación
├── resultados/            # Resultados procesados
└── index.html            # Interfaz web
```

## Requisitos

- Python 3.8+
- Dependencias listadas en requirements.txt

## Instalación

1. Clonar el repositorio:
```bash
git clone [URL_DEL_REPOSITORIO]
cd facebook_scraper
```

2. Crear y activar entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

## Uso

1. Extraer datos:
```bash
python src/extrae_html_con_operacion.py
```

2. Procesar datos:
```bash
python src/procesa_datos_propiedades.py
```

3. Abrir interfaz web:
```bash
open index.html
```

## Licencia

Este proyecto es privado y confidencial.

## Autor

Pablo Ravel 