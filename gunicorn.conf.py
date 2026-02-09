# Gunicorn configuration for Render.com
# Optimized for free tier (512MB RAM)

# Bind to the port provided by Render
bind = "0.0.0.0:10000"

# Use 1 worker to save memory (free tier has limited RAM)
workers = 1

# Use sync worker (gevent uses more memory)
worker_class = "sync"

# Increase timeout for long AI processing (5 minutes)
timeout = 300

# Graceful timeout
graceful_timeout = 120

# Keep alive
keepalive = 5

# Preload app to save memory
preload_app = True

# Log level
loglevel = "info"

# Access log
accesslog = "-"

# Error log
errorlog = "-"
