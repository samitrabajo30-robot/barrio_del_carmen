# -*- coding: utf-8 -*-
"""Rutas Vecinales: Reclamos y Contenido de la Página Web."""

from flask import Blueprint, jsonify, request

import auditoria
import sesiones
from db import db

bp = Blueprint('vecinales', __name__, url_prefix='/api')


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
    """Permite al administrador editar los textos e imágenes del barrio."""
    datos = request.get_json(silent=True) or {}
    yo = sesiones.usuario_actual()

    claves_permitidas = ('intro', 'history', 'extra_text', 'hero_image', 'video_url')
    actualizados = 0

    for clave in claves_permitidas:
        if clave in datos:
            valor = str(datos[clave]).strip()
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
    """Recepción de reclamos anónimos desde la página pública."""
    datos = request.get_json(silent=True) or {}

    # Trampa Honeypot antispam
    if datos.get('website'):
        return jsonify(ok=True)

    fecha = (datos.get('problem-date') or datos.get('problem_date') or '').strip()
    hora = (datos.get('problem-time') or datos.get('problem_time') or '').strip()
    zona = (datos.get('zone') or '').strip()
    tema = (datos.get('topic') or '').strip()
    descripcion = (datos.get('description') or '').strip()

    if not fecha or not hora or not zona or not tema or not descripcion:
        return jsonify(error="Por favor completá todos los campos requeridos."), 400

    if len(descripcion) < 5 or len(descripcion) > 1500:
        return jsonify(error="La descripción debe contener entre 5 y 1500 caracteres."), 400

    new_id, _ = db.execute(
        """INSERT INTO reclamos (fecha_problema, hora_problema, zona, tema, descripcion, estado)
           VALUES (?, ?, ?, ?, ?, 'recibida')""",
        [fecha, hora, zona, tema, descripcion]
    )

    return jsonify(ok=True, id=new_id, mensaje="Aviso recibido por la Junta Vecinal.")


@bp.get('/admin/reclamos')
@sesiones.requiere_sesion
def listar_reclamos():
    """Lista de reclamos para el panel administrativo con filtros."""
    filtros = []
    params = []

    desde = request.args.get('desde')
    hasta = request.args.get('hasta')
    tema = request.args.get('tema')
    zona = request.args.get('zona')
    estado = request.args.get('estado')

    if desde:
        filtros.append("fecha_problema >= ?")
        params.append(desde)
    if hasta:
        filtros.append("fecha_problema <= ?")
        params.append(hasta)
    if tema:
        filtros.append("tema = ?")
        params.append(tema)
    if zona:
        filtros.append("zona LIKE ?")
        params.append(f"%{zona.strip()}%")
    if estado:
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
