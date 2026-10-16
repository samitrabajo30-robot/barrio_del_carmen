# -*- coding: utf-8 -*-
"""Punto de entrada WSGI para Vercel Serverless Functions."""

import os
import sys

# Asegurar que el directorio de api esté en el path de Python
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app

# Vercel Serverless busca la variable 'app'
