# -*- coding: utf-8 -*-
"""Configuración del Sistema - Barrio Del Carmen
Carga variables de entorno para Turso y Vercel.
"""

import os
from pathlib import Path

# Intentar cargar python-dotenv si está disponible localmente
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
except ImportError:
    pass

# Base de datos Turso Cloud
TURSO_DATABASE_URL = os.environ.get('TURSO_DATABASE_URL', '').strip()
TURSO_AUTH_TOKEN = os.environ.get('TURSO_AUTH_TOKEN', '').strip()

# Clave secreta para firmar cookies de sesión en Vercel
SECRET_KEY = os.environ.get('SECRET_KEY', 'barrio-del-carmen-secret-key-super-segura-2026')

# Seguridad de cookies (True en producción con HTTPS en Vercel)
COOKIE_SECURE = os.environ.get('COOKIE_SECURE', 'true').lower() in ('1', 'true', 'yes')
COOKIE_SAMESITE = os.environ.get('COOKIE_SAMESITE', 'Lax')

# Puerto y Host para pruebas locales
PORT = int(os.environ.get('PORT', 5000))
HOST = os.environ.get('HOST', '0.0.0.0')

# Orígenes CORS permitidos
CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
CORS_ORIGINS = [o.strip() for o in CORS_ORIGINS if o.strip()]

# Roles de usuario
ROLES = ('admin', 'operador', 'consulta')

# Áreas vecinales
AREAS_POR_DEFECTO = [
    {'id': 'junta', 'label': 'Junta Vecinal'},
    {'id': 'servicios', 'label': 'Obras y Servicios Públicos'},
    {'id': 'eventos', 'label': 'Cultura y Eventos'},
    {'id': 'administracion', 'label': 'Administración General'},
]
