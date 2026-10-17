# -*- coding: utf-8 -*-
"""Rutas Vecinales: Reclamos, Eventos, Comercios y Contenido de la Página Web."""

import re
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request

import auditoria
import sesiones
from db import db

bp = Blueprint('vecinales', __name__, url_prefix='/api')

TEMAS_PERMITIDOS = {'Alumbrado', 'Calles', 'Residuos', 'Servicios', 'Otro'}
CATEGORIAS_COMERCIOS = {'Gastronomía', 'Salud', 'Almacenes', 'Otros servicios'}
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

    if datos.get('website'):
        return jsonify(ok=True)

    fecha = (datos.get('problem-date') or datos.get('problem_date') or '').strip()
    hora = (datos.get('problem-time') or datos.get('problem_time') or '').strip()
    zona = (datos.get('zone') or '').strip()
    tema = (datos.get('topic') or '').strip()
    descripcion = (datos.get('description') or '').strip()

    if not fecha or not hora or not zona or not tema or not descripcion:
        return jsonify(error="Por favor completá todos los campos requeridos."), 400

    if tema not in TEMAS_PERMITIDOS:
        return jsonify(error="El tema seleccionado no es válido."), 400

    if not re.match(r'^\d{4}-\d{2}-\d{2}$', fecha):
        return jsonify(error="El formato de fecha no es válido."), 400

    if len(zona) < 2 or len(zona) > 120:
        return jsonify(error="La zona debe tener entre 2 y 120 caracteres."), 400

    if len(descripcion) < 5 or len(descripcion) > 1500:
        return jsonify(error="La descripción debe contener entre 5 y 1500 caracteres."), 400

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


# =============================================================================
# 3. EVENTOS VECINALES Y AGENDA COMUNITARIA (Público y Admin)
# =============================================================================

@bp.get('/eventos')
def obtener_eventos():
    """Devuelve los eventos publicados ordenados cronológicamente."""
    filas = db.query(
        """SELECT id, nombre, descripcion, fecha, horario, lugar, creado_en
           FROM eventos
           WHERE estado = 'publicado'
           ORDER BY fecha ASC, horario ASC
           LIMIT 100"""
    )
    return jsonify(eventos=filas)


@bp.post('/eventos')
def crear_evento_publico():
    """Permite a los vecinos compartir un evento desde la página principal."""
    datos = request.get_json(silent=True) or {}

    if datos.get('website'):
        return jsonify(ok=True)

    nombre = (datos.get('event-name') or datos.get('nombre') or '').strip()
    descripcion = (datos.get('description') or datos.get('descripcion') or '').strip()
    fecha = (datos.get('event-date') or datos.get('fecha') or '').strip()
    horario = (datos.get('event-time') or datos.get('horario') or '').strip()
    lugar = (datos.get('place') or datos.get('lugar') or '').strip()

    if not nombre or not descripcion or not fecha or not horario or not lugar:
        return jsonify(error="Todos los campos del evento son requeridos."), 400

    if not re.match(r'^\d{4}-\d{2}-\d{2}$', fecha):
        return jsonify(error="La fecha debe tener formato YYYY-MM-DD."), 400

    if len(nombre) > 120 or len(descripcion) > 1000 or len(lugar) > 120:
        return jsonify(error="Uno de los campos supera la longitud permitida."), 400

    new_id, _ = db.execute(
        """INSERT INTO eventos (nombre, descripcion, fecha, horario, lugar, estado)
           VALUES (?, ?, ?, ?, ?, 'publicado')""",
        [nombre, descripcion, fecha, horario, lugar]
    )

    return jsonify(ok=True, id=new_id, mensaje="¡Tu evento fue publicado con éxito en Novedades del barrio!")


@bp.get('/admin/eventos')
@sesiones.requiere_sesion
def listar_eventos_admin():
    """Lista todos los eventos para el panel de administración."""
    filas = db.query(
        """SELECT id, nombre, descripcion, fecha, horario, lugar, estado, creado_en
           FROM eventos
           ORDER BY fecha DESC, id DESC"""
    )
    return jsonify(eventos=filas)


@bp.post('/admin/eventos')
@sesiones.requiere_sesion
def crear_evento_admin():
    """Crea un evento oficial desde el panel de administración."""
    datos = request.get_json(silent=True) or {}
    nombre = (datos.get('nombre') or '').strip()
    descripcion = (datos.get('descripcion') or '').strip()
    fecha = (datos.get('fecha') or '').strip()
    horario = (datos.get('horario') or '').strip()
    lugar = (datos.get('lugar') or '').strip()

    if not nombre or not descripcion or not fecha or not horario or not lugar:
        return jsonify(error="Todos los campos son obligatorios."), 400

    new_id, _ = db.execute(
        """INSERT INTO eventos (nombre, descripcion, fecha, horario, lugar, estado)
           VALUES (?, ?, ?, ?, ?, 'publicado')""",
        [nombre, descripcion, fecha, horario, lugar]
    )

    yo = sesiones.usuario_actual()
    auditoria.registrar_accion(
        accion='CREAR_EVENTO',
        entidad='eventos',
        entidad_id=str(new_id),
        detalle=f"Creó el evento '{nombre}' para la fecha {fecha}",
        operador=yo
    )

    return jsonify(ok=True, id=new_id)


@bp.delete('/admin/eventos/<int:evento_id>')
@sesiones.requiere_sesion
def eliminar_evento(evento_id: int):
    """Elimina un evento."""
    db.execute("DELETE FROM eventos WHERE id = ?", [evento_id])

    yo = sesiones.usuario_actual()
    auditoria.registrar_accion(
        accion='ELIMINAR_EVENTO',
        entidad='eventos',
        entidad_id=str(evento_id),
        detalle=f"Eliminó el evento ID {evento_id}",
        operador=yo
    )

    return jsonify(ok=True)


# =============================================================================
# 4. COMERCIOS Y SERVICIOS DEL BARRIO (Público y Admin)
# =============================================================================

@bp.get('/comercios')
def obtener_comercios():
    """Devuelve todos los comercios activos para el directorio público."""
    filas = db.query(
        """SELECT id, nombre, categoria, descripcion, direccion, telefono
           FROM comercios
           WHERE activo = 1
           ORDER BY nombre ASC"""
    )
    return jsonify(comercios=filas)


@bp.get('/admin/comercios')
@sesiones.requiere_sesion
def listar_comercios_admin():
    """Lista todos los comercios para el panel administrativo."""
    filas = db.query(
        """SELECT id, nombre, categoria, descripcion, direccion, telefono, activo, creado_en
           FROM comercios
           ORDER BY nombre ASC"""
    )
    return jsonify(comercios=filas)


@bp.post('/admin/comercios')
@sesiones.requiere_sesion
def crear_comercio():
    """Agrega un nuevo comercio o servicio del barrio."""
    datos = request.get_json(silent=True) or {}
    nombre = (datos.get('nombre') or '').strip()
    categoria = (datos.get('categoria') or '').strip()
    descripcion = (datos.get('descripcion') or '').strip()
    direccion = (datos.get('direccion') or '').strip() or None
    telefono = (datos.get('telefono') or '').strip() or None

    if not nombre or not categoria or not descripcion:
        return jsonify(error="El nombre, la categoría y la descripción son obligatorios."), 400

    if categoria not in CATEGORIAS_COMERCIOS:
        categoria = 'Otros servicios'

    new_id, _ = db.execute(
        """INSERT INTO comercios (nombre, categoria, descripcion, direccion, telefono, activo)
           VALUES (?, ?, ?, ?, ?, 1)""",
        [nombre, categoria, descripcion, direccion, telefono]
    )

    yo = sesiones.usuario_actual()
    auditoria.registrar_accion(
        accion='CREAR_COMERCIO',
        entidad='comercios',
        entidad_id=str(new_id),
        detalle=f"Agregó el comercio '{nombre}' en la categoría {categoria}",
        operador=yo
    )

    return jsonify(ok=True, id=new_id)


@bp.patch('/admin/comercios/<int:comercio_id>')
@sesiones.requiere_sesion
def editar_comercio(comercio_id: int):
    """Edita los datos de un comercio existente."""
    datos = request.get_json(silent=True) or {}

    campos = []
    valores = []
    for c_json, c_bd in [
        ('nombre', 'nombre'),
        ('categoria', 'categoria'),
        ('descripcion', 'descripcion'),
        ('direccion', 'direccion'),
        ('telefono', 'telefono'),
        ('activo', 'activo'),
    ]:
        if c_json in datos:
            val = datos[c_json]
            if c_bd == 'activo':
                val = 1 if val else 0
            elif isinstance(val, str):
                val = val.strip() or None
            campos.append(f"{c_bd} = ?")
            valores.append(val)

    if not campos:
        return jsonify(error="No se proporcionaron campos para actualizar."), 400

    valores.append(comercio_id)
    db.execute(f"UPDATE comercios SET {', '.join(campos)} WHERE id = ?", valores)

    yo = sesiones.usuario_actual()
    auditoria.registrar_accion(
        accion='EDITAR_COMERCIO',
        entidad='comercios',
        entidad_id=str(comercio_id),
        detalle=f"Editó datos del comercio ID {comercio_id}",
        operador=yo
    )

    return jsonify(ok=True)


@bp.delete('/admin/comercios/<int:comercio_id>')
@sesiones.requiere_sesion
def eliminar_comercio(comercio_id: int):
    """Elimina definitivamente un comercio."""
    db.execute("DELETE FROM comercios WHERE id = ?", [comercio_id])

    yo = sesiones.usuario_actual()
    auditoria.registrar_accion(
        accion='ELIMINAR_COMERCIO',
        entidad='comercios',
        entidad_id=str(comercio_id),
        detalle=f"Eliminó el comercio ID {comercio_id}",
        operador=yo
    )

    return jsonify(ok=True)
