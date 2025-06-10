#!/usr/bin/env python3
"""
Archivo de entrada alternativo para DigitalOcean App Platform
"""
import os
from wsgi import application

# Alias adicional por si DigitalOcean busca diferentes nombres
app = application

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    application.run(host="0.0.0.0", port=port) 
"""
Archivo de entrada alternativo para DigitalOcean App Platform
"""
import os
from wsgi import application

# Alias adicional por si DigitalOcean busca diferentes nombres
app = application

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    application.run(host="0.0.0.0", port=port) 