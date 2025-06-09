# 🚀 GUÍA DE DEPLOYMENT EN RAILWAY

## ✅ ARCHIVOS PREPARADOS

Los siguientes archivos han sido creados para Railway:
- `requirements.txt` - Dependencias de Python
- `Procfile` - Comando de inicio
- `railway.json` - Configuración específica
- `api_server_railway.py` - Adaptador para Railway
- `env.example` - Variables de entorno de ejemplo

## 📋 PASOS PARA SUBIR A RAILWAY

### 1. **Crear cuenta en Railway**
1. Ve a https://railway.app
2. Regístrate con GitHub (recomendado)
3. Verifica tu email

### 2. **Crear repositorio en GitHub**
1. Ve a https://github.com/new
2. Nombre: `sistema-inmobiliario`
3. Descripción: `Sistema inmobiliario completo con gestión de propiedades, usuarios y WhatsApp`
4. Público o Privado (tu elección)
5. ✅ Crear repositorio

### 3. **Subir código a GitHub**
```bash
# En tu terminal, en la carpeta del proyecto:
cd /Users/pabloravel/Proyectos/facebook_scraper

# Inicializar git (si no está ya)
git init

# Agregar archivos
git add .

# Hacer commit
git commit -m "🚀 Sistema inmobiliario completo para Railway"

# Conectar con tu repositorio (reemplaza TU_USUARIO)
git remote add origin https://github.com/TU_USUARIO/sistema-inmobiliario.git

# Subir código
git branch -M main
git push -u origin main
```

### 4. **Crear proyecto en Railway**
1. En Railway, click "New Project"
2. Selecciona "Deploy from GitHub repo"
3. Conecta tu cuenta de GitHub si no está conectada
4. Selecciona el repositorio `sistema-inmobiliario`
5. Click "Deploy Now"

### 5. **Configurar variables de entorno (opcional)**
En Railway, ve a tu proyecto → Variables:
- `WHATSAPP_TOKEN`: Tu token de WhatsApp Business (opcional)
- `PHONE_NUMBER_ID`: Tu Phone Number ID de WhatsApp (opcional)
- `JWT_SECRET`: Un secreto para JWT (opcional, se genera automáticamente)

### 6. **¡Listo! 🎉**
- Railway detectará automáticamente que es una app Python
- Instalará las dependencias de `requirements.txt`
- Ejecutará el comando del `Procfile`
- Te dará una URL como: `https://tu-proyecto.railway.app`

## 🌟 FUNCIONALIDADES INCLUIDAS

✅ **4,270 propiedades** cargadas y listas
✅ **Sistema de administración** de usuarios y asesores
✅ **Envío por WhatsApp** con formato profesional
✅ **Sistema de favoritos** y gestión de contactos
✅ **Autenticación completa** con JWT
✅ **API REST** con documentación
✅ **Frontend responsive** incluido
✅ **Base de datos SQLite** auto-gestionada
✅ **Sistema de backup** automático

## 📱 URLs IMPORTANTES

Una vez desplegado, tendrás acceso a:

- 🏠 **Frontend principal**: `https://tu-proyecto.railway.app/frontend_desarrollo.html`
- 🔌 **API Health**: `https://tu-proyecto.railway.app/health`
- 📊 **Estadísticas**: `https://tu-proyecto.railway.app/api/estadisticas`
- 👥 **Sistema de usuarios**: Registro y login incluidos
- 📱 **WhatsApp**: Configuración en el panel de administración

## 🔧 MANTENIMIENTO

Railway maneja automáticamente:
- ✅ Escalamiento automático
- ✅ HTTPS certificado
- ✅ Monitoreo de salud
- ✅ Logs en tiempo real
- ✅ Backups automáticos

## 💰 COSTOS

- **Tier gratuito**: $5 USD de crédito mensual
- **Perfecto para pruebas** y sitios pequeños-medianos
- **Escalamiento bajo demanda**

## 🆘 SOPORTE

Si tienes problemas:
1. Revisa los logs en Railway Dashboard
2. Verifica que todos los archivos estén en GitHub
3. Comprueba las variables de entorno

¡Tu sistema inmobiliario estará disponible 24/7! 🚀 