# 🏠 Sistema Inmobiliario Estable v2.5.0

Sistema inmobiliario completo con **modales flotantes** para autenticación y funcionalidades avanzadas.

## ✅ Funcionalidades Confirmadas

### 🔐 Autenticación
- **Modales flotantes** para login y registro (NO botones visibles)
- Sistema JWT completo
- Gestión de perfiles de usuario
- Control de permisos por rol

### 👥 Sistema Colaborativo
- Gestión de equipos colaborativos
- Favoritos compartidos
- Notificaciones en tiempo real
- Sistema de roles

### 📱 WhatsApp Business API
- Integración completa con WhatsApp Business API
- Envío automático de propiedades
- Configuración visual en Panel Admin
- Formateo inteligente de mensajes con imágenes
- Fallback a WhatsApp Web cuando API no está configurada

### 🏢 Gestión de Contactos
- Base de datos SQLite de vendedores
- Asociación propiedades-contactos
- Historial de interacciones
- API CRUD completa

### 📊 Panel de Administración
- Control total del sistema
- Gestión de usuarios
- Configuración WhatsApp
- Estadísticas detalladas

### 🏠 Catálogo de Propiedades
- **4,270 propiedades** verificadas
- Filtros por 32+ características reales
- Búsqueda por texto optimizada
- Paginación eficiente
- Galería de imágenes

## 🚀 Deployment Railway

### Archivos Esenciales
```
app.py                              # Punto de entrada
api_server_optimizado.py           # Servidor principal
frontend_desarrollo.html           # Frontend con modales
requirements.txt                   # Dependencias
Procfile                           # Railway config
render.yaml                        # Config alternativo
```

### Archivos de Datos
```
sistema_colaborativo.db            # BD colaborativa
contactos_vendedores.db            # BD contactos
resultados/                        # Imágenes de propiedades
resultados/propiedades_estructuradas.json  # Catálogo principal
```

### Configuración WhatsApp
- Variables de entorno: `WHATSAPP_TOKEN`, `PHONE_NUMBER_ID`
- Archivos ejemplo: `configuracion_whatsapp.example`

## 🔧 Ejecutar Localmente

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar servidor
python3 api_server_optimizado.py

# O usar el punto de entrada
python3 app.py
```

## 🌐 Endpoints Principales

- `http://localhost:5001/frontend_desarrollo.html` - Frontend completo
- `http://localhost:5001/api/version` - Info del sistema
- `http://localhost:5001/api/propiedades` - Catálogo
- `http://localhost:5001/api/auth/*` - Autenticación
- `http://localhost:5001/api/equipos/*` - Sistema colaborativo
- `http://localhost:5001/api/whatsapp/*` - WhatsApp Business

## 📁 Archivos Organizados

Los archivos no esenciales para deployment están en:
- `archived_files/` - Archivos de desarrollo
- `src/` - Código fuente de scraping
- `respaldos*/` - Backups automáticos
- `legacy*/` - Versiones anteriores

## 🎯 Estado Actual

✅ **FUNCIONANDO CORRECTAMENTE**
- Servidor ejecutándose en puerto 5001
- Todas las funcionalidades activas
- Modales flotantes confirmados
- Base de datos intacta
- WhatsApp Business configurado
- Listo para Railway deployment 