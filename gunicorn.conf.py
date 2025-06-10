# Configuración de Gunicorn para Render.com
import os

# Bind to PORT environment variable
bind = f"0.0.0.0:{os.environ.get('PORT', '5001')}"

# Worker processes
workers = 1
worker_class = "sync"
worker_connections = 1000

# Timeout
timeout = 120
keepalive = 2

# Logging
loglevel = "info"
accesslog = "-"
errorlog = "-"

# Preload app
preload_app = True

# Max requests per worker
max_requests = 1000
max_requests_jitter = 100 