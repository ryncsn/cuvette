"""
Config file for gunicorn
"""
workers = 1
worker_class = 'aiohttp.GunicornWebWorker'
