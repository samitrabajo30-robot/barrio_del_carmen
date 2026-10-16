# -*- coding: utf-8 -*-
"""Rutas Vecinales: Reclamos y Contenido de la Página Web con Validaciones y Seguridad."""

import re
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request

import auditoria
import sesiones
from db import db

bp = Blueprint('vecinales', __name__, url_prefix='/api')

TEMAS_PERMITIDOS = {'Alumbrado', 'Calles', 'Residuos', 'Servicios', 'Otro'}
YOUTUBE_REGEX = re.compile(r'(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))([\w-]{11})')


def es_url_segura(url: str) -> bool:
    """Verifica que la URL use HTTPS o HTTP y no protocolos peligrosos (javascript:, data:)."""
    if not url:
        return True
    url_limpia = url.strip().lower()
    return url_limpia.startswith('https://') or url_limpia.startswith('http://')


# =============================================================================
# 1. CONTENIDO DE LA PÁGINA (Público y Admin)
# =============================================================================

@bp.get('/contenido')
def obtener_contenido():
    """Devuelve los textos, imágenes y enlaces de la página pública."""
    filas = db.query("SELECT clave, valor FROM contenido_sitio")
    contenido = {f['clave']: f['valor'] for f in filas}
    return jsonify(contenido=contenido)


@bp.post('/admin/contenido')
@sesiones.requiere_sesion
def actualizar_contenido():
    """Permite al administrador editar los textos e imágenes del barrio con sanitización."""
    datos = request.get_json(silent=True) or {}
    yo = sesiones.usuario_actual()

    claves_permitidas = ('intro', 'history', 'extra_text', 'hero_image', 'video_url')
    actualizados = 0

    # Validaciones de seguridad
    if 'hero_image' in datos:
        hero_img = str(datos['hero_image']).strip()
        if hero_img and not es_url_segura(hero_img):
            return jsonify(error="La URL de la imagen debe comenzar con https://"), 400

    if 'video_url' in datos:
        vid_url = str(datos['video_url']).strip()
        if vid_url:
            if not es_url_segura(vid_url) or not YOUTUBE_REGEX.search(vid_url):
                return jsonify(error="El video debe ser un enlace válido de YouTube (ej. https://www.youtube.com/watch?v=...)"), 400

    for clave in claves_permitidas:
        if clave in datos:
            valor = str(datos[clave]).strip()
            # Limitar longitud para prevenir abusos de almacenamiento
            if len(valor) > 3000:
                return jsonify(error=f"El campo '{clave}' excede el límite máximo de caracteres."), 400

            db.execute(
                """INSERT INTO contenido_sitio (clave, valor, actualizado_en)
                   VALUES (?, ?, datetime('now', 'utc'))
                   ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor, actualizado_en = excluded.actualizado_en""",
                [clave, valor]
            )
            actualizados += 1

    auditoria.registrar_accion(
        accion='MODIFICAR_CONTENIDO',
        entidad='contenido_sitio',
        detalle=f"Actualizó {actualizados} secciones del sitio web",
        operador=yo
    )

    filas = db.query("SELECT clave, valor FROM contenido_sitio")
    return jsonify(ok=True, contenido={f['clave']: f['valor'] for f in filas})


# =============================================================================
# 2. RECLAMOS Y AVISOS VECINALES (Público y Admin)
# =============================================================================

@bp.post('/reclamos')
def enviar_reclamo():
    """Recepción de reclamos anónimos con validaciones estrictas y protección antispam."""
    datos = request.get_json(silent=True) or {}

    # 1. Trampa Honeypot: si el bot completó el campo invisible 'website', se descarta en silencio
    if datos.get('website'):
        return jsonify(ok=True)

    fecha = (datos.get('problem-date') or datos.get('problem_date') or '').strip()
    hora = (datos.get('problem-time') or datos.get('problem_time') or '').strip()
    zona = (datos.get('zone') or '').strip()
    tema = (datos.get('topic') or '').strip()
    descripcion = (datos.get('description') or '').strip()

    if not fecha or not hora or not zona or not tema or not descripcion:
        return jsonify(error="Por favor completá todos los campos requeridos."), 400

    # 2. Validación de tema contra lista blanca
    if tema not in TEMAS_PERMITIDOS:
        return jsonify(error="El tema seleccionado no es válido."), 400

    # 3. Validación de formato de fecha básico (YYYY-MM-DD)
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', fecha):
        return jsonify(error="El formato de fecha no es válido."), 400

    # 4. Longitud y sanitización de textos
    if len(zona) < 2 or len(zona) > 120:
        return jsonify(error="La zona debe tener entre 2 y 120 caracteres."), 400

    if len(descripcion) < 5 or len(descripcion) > 1500:
        return jsonify(error="La descripción debe contener entre 5 y 1500 caracteres."), 400

    # 5. Rate limiting básico contra inundación (máximo 10 reclamos por minuto a nivel general)
    try:
        recientes = db.query("SELECT COUNT(*) as cant FROM reclamos WHERE creado_en >= datetime('now', '-1 minute')")
        if recientes and recientes[0].get('cant', 0) > 10:
            return jsonify(error="Hay un alto volumen de envíos en este momento. Por favor intentá en un minuto."), 429
    except Exception:
        pass

    new_id, _ = db.execute(
        """INSERT INTO reclamos (fecha_problema, hora_problema, zona, tema, descripcion, estado)
           VALUES (?, ?, ?, ?, ?, 'recibida')""",
        [fecha, hora, zona, tema, descripcion]
    )

    return jsonify(ok=True, id=new_id, mensaje="Aviso recibido por la Junta Vecinal.")


@bp.get('/admin/reclamos')
@sesiones.requiere_sesion
def listar_reclamos():
    """Lista de reclamos para el panel administrativo con consultas parametrizadas seguras."""
    filtros = []
    params = []

    desde = request.args.get('desde')
    hasta = request.args.get('hasta')
    tema = request.args.get('tema')
    zona = request.args.get('zona')
    estado = request.args.get('estado')

    if desde and re.match(r'^\d{4}-\d{2}-\d{2}$', desde):
        filtros.append("fecha_problema >= ?")
        params.append(desde)
    if hasta and re.match(r'^\d{4}-\d{2}-\d{2}$', hasta):
        filtros.append("fecha_problema <= ?")
        params.append(hasta)
    if tema and tema in TEMAS_PERMITIDOS:
        filtros.append("tema = ?")
        params.append(tema)
    if zona:
        # Sanitizar entrada de búsqueda para LIKE
        zona_limpia = zona.strip().replace('%', '').replace('_', '')
        if zona_limpia:
            filtros.append("zona LIKE ?")
            params.append(f"%{zona_limpia}%")
    if estado and estado in ('recibida', 'en_gestion', 'resuelta'):
        filtros.append("estado = ?")
        params.append(estado)

    where = f"WHERE {' AND '.join(filtros)}" if filtros else ""
    sql = f"""SELECT id, fecha_problema, hora_problema, zona, tema, descripcion, estado, creado_en
              FROM reclamos
              {where}
              ORDER BY creado_en DESC
              LIMIT 1000"""

    filas = db.query(sql, params)
    return jsonify(reclamos=filas)


@bp.patch('/admin/reclamos/<int:reclamo_id>')
@sesiones.requiere_sesion
def actualizar_estado_reclamo(reclamo_id: int):
    """Actualiza el estado de un reclamo vecinal (recibida, en_gestion, resuelta)."""
    datos = request.get_json(silent=True) or {}
    nuevo_estado = (datos.get('estado') or '').strip()

    if nuevo_estado not in ('recibida', 'en_gestion', 'resuelta'):
        return jsonify(error="Estado no válido."), 400

    db.execute("UPDATE reclamos SET estado = ? WHERE id = ?", [nuevo_estado, reclamo_id])

    yo = sesiones.usuario_actual()
    auditoria.registrar_accion(
        accion='ACTUALIZAR_RECLAMO',
        entidad='reclamos',
        entidad_id=str(reclamo_id),
        detalle=f"Cambió el estado a '{nuevo_estado}'",
        operador=yo
    )

    return jsonify(ok=True, estado=nuevo_estado)
