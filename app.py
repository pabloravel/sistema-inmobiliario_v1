#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏠 SISTEMA INMOBILIARIO ESTABLE - Punto de entrada para Railway
Servidor que ejecuta el sistema inmobiliario completo con todas las funcionalidades

✅ FUNCIONALIDADES COMPLETAS:
- 🔐 Autenticación JWT con modales flotantes
- 👥 Sistema colaborativo de equipos
- 📱 Integración WhatsApp Business API
- 🏢 Gestión de contactos de vendedores
- 📊 Panel de administración
- 🏠 Catálogo de 4,270 propiedades
- 🛡️ Sistema de prevención de corrupción de datos

🚀 VERSIÓN: 2.5.0 - Sistema Inmobiliario Completo
📅 Última actualización: 2025-06-08
🎯 PROYECTO ESTABLE CON MODALES FLOTANTES

Para Railway deployment
"""

import os
import sys

# Asegurar que el directorio actual esté en el path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Importar y ejecutar el servidor optimizado
if __name__ == "__main__":
    try:
        # Importar el módulo del servidor
        import api_server_optimizado
        print("🚀 Iniciando Sistema Inmobiliario Estable v2.5.0...")
        print("📱 Con modales flotantes para autenticación")
        print("🌐 Listo para Railway deployment")
    except ImportError as e:
        print(f"❌ Error importando servidor: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error ejecutando servidor: {e}")
        sys.exit(1) 