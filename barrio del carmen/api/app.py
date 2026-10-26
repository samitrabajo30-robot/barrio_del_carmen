# -*- coding: utf-8 -*-
"""Servidor Principal de API - Barrio Del Carmen
Compatible con Vercel Serverless Functions y reforzado con cabeceras de seguridad.
"""

from flask import Flask, jsonify, request

import config
import db
import rutas_admin
import rutas_auth
import rutas_vecinales


def crear_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = config.SECRET_KEY
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=config.COOKIE_SECURE,
        SESSION_COOKIE_SAMESITE=config.COOKIE_SAMESITE,
        PERMANENT_SESSION_LIFETIME=86400 * 7,  # 7 días
    )

    # Middleware de Seguridad y CORS Restringido
    @app.after_request
    def agregar_headers_seguridad(response):
        req_origin = request.headers.get('Origin')
        origenes_permitidos = config.CORS_ORIGINS

        # Solo autorizar CORS si el origen está explícitamente en la lista permitida o es Vercel / localhost
        if req_origin:
            es_valido = (
                '*' in origenes_permitidos or
                req_origin in origenes_permitidos or
                req_origin.endswith('.vercel.app') or
                'localhost' in req_origin or
                '127.0.0.1' in req_origin
            )
            if es_valido:
                response.headers['Access-Control-Allow-Origin'] = req_origin
                response.headers['Access-Control-Allow-Credentials'] = 'true'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
                response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PATCH, PUT, DELETE, OPTIONS'

        # Cabeceras de protección defensiva OWASP
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response

    @app.route('/api/<path:subpath>', methods=['OPTIONS'])
    def cors_preflight(subpath):
        return jsonify(ok=True)

    # Inicializar tablas en Turso automáticamente si no existen
    try:
        db.inicializar_tablas()
    except Exception as e:
        print(f"[AVISO DB] Auto-inicialización: {e}")

    # Registrar rutas
    app.register_blueprint(rutas_auth.bp)
    app.register_blueprint(rutas_admin.bp)
    app.register_blueprint(rutas_vecinales.bp)

    @app.get('/api/health')
    def health():
        return jsonify(
            estado='activo',
            motor='Turso Cloud (libSQL)' if db.es_turso_activo() else 'SQLite Local',
            roles_disponibles=config.ROLES,
            areas_disponibles=config.AREAS_POR_DEFECTO,
        )

    return app


app = crear_app()

if __name__ == '__main__':
    print(f"Servidor API Barrio Del Carmen activo en http://localhost:{config.PORT}/")
    app.run(host=config.HOST, port=config.PORT, debug=True)
