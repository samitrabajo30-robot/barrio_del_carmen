# -*- coding: utf-8 -*-
"""Rutas de Administración de Operadores, PIN y Auditoría."""

import secrets
from flask import Blueprint, jsonify, request

import auditoria
import credenciales
import seguridad
import sesiones
from config import ROLES
from db import db

bp = Blueprint('admin', __name__, url_prefix='/api')


def usuario_a_json(u: dict) -> dict:
    return {
        'id': u.get('id'),
        'usuario': u.get('usuario'),
        'nombre': u.get('nombre'),
        'rol': u.get('rol'),
        'area': u.get('area'),
        'email': u.get('email'),
        'telefono': u.get('telefono'),
        'activo': bool(u.get('activo')),
        'debeCambiarClave': bool(u.get('debe_cambiar_clave')),
        'creadoEn': u.get('creado_en'),
    }


@bp.get('/admin/operadores')
@sesiones.requiere_admin
def listar_usuarios():
    filas = db.query("SELECT * FROM usuarios WHERE activo = 1 ORDER BY usuario ASC")
    resp = jsonify(operadores=[usuario_a_json(f) for f in filas])
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return resp


@bp.post('/admin/operadores')
@sesiones.requiere_admin
def crear_usuario():
    datos = request.get_json(silent=True) or {}
    usuario = (datos.get('usuario') or '').strip().lower()
    nombre = (datos.get('nombre') or '').strip()

    if not usuario or not nombre:
        return jsonify(error="El nombre completo y el nombre de usuario son obligatorios."), 400

    existente = db.query("SELECT id FROM usuarios WHERE lower(usuario) = ? LIMIT 1", [usuario])
    if existente:
        return jsonify(error=f"Ya existe un usuario registrado como '{usuario}'."), 400

    rol = datos.get('rol') if datos.get('rol') in ROLES else 'operador'
    area = (datos.get('area') or '').strip() or None
    email = (datos.get('email') or '').strip() or None
    telefono = (datos.get('telefono') or '').strip() or None

    provisoria = (datos.get('clave') or '').strip() or f"temp{secrets.token_hex(4)}"
    hash_clave = seguridad.hashear(provisoria)

    new_id, _ = db.execute(
        """INSERT INTO usuarios
           (usuario, hash_clave, nombre, rol, area, email, telefono, activo, debe_cambiar_clave)
           VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1)""",
        [usuario, hash_clave, nombre, rol, area, email, telefono]
    )

    yo = sesiones.usuario_actual()
    auditoria.registrar_accion(
        accion='CREAR_USUARIO',
        entidad='usuario',
        entidad_id=usuario,
        detalle=f"Creó el usuario {nombre} (@{usuario}) con rol {rol}",
        operador=yo
    )

    nuevo_u = db.query("SELECT * FROM usuarios WHERE id = ?", [new_id])[0]
    return jsonify(operador=usuario_a_json(nuevo_u), claveProvisoria=provisoria), 201


@bp.patch('/admin/operadores/<int:usuario_id>')
@sesiones.requiere_admin
def editar_usuario(usuario_id: int):
    filas = db.query("SELECT * FROM usuarios WHERE id = ? LIMIT 1", [usuario_id])
    if not filas:
        return jsonify(error="El usuario no existe."), 404
    u = filas[0]

    datos = request.get_json(silent=True) or {}
    yo = sesiones.usuario_actual()

    if yo and yo['id'] == usuario_id:
        if 'activo' in datos and not datos['activo']:
            return jsonify(error="No podés dar de baja tu propia cuenta."), 400
        if 'rol' in datos and datos['rol'] != 'admin':
            return jsonify(error="No podés quitarte el rol de Administrador."), 400

    campos = []
    valores = []

    for campo_json, campo_bd in [
        ('nombre', 'nombre'),
        ('rol', 'rol'),
        ('area', 'area'),
        ('email', 'email'),
        ('telefono', 'telefono'),
        ('activo', 'activo'),
    ]:
        if campo_json in datos:
            val = datos[campo_json]
            if campo_bd == 'activo':
                val = 1 if val else 0
            elif isinstance(val, str):
                val = val.strip() or None
            campos.append(f"{campo_bd} = ?")
            valores.append(val)

    if 'clave' in datos and datos['clave']:
        clave_str = str(datos['clave']).strip()
        if clave_str:
            campos.append("hash_clave = ?")
            valores.append(seguridad.hashear(clave_str))

    if campos:
        valores.append(usuario_id)
        sql = f"UPDATE usuarios SET {', '.join(campos)} WHERE id = ?"
        db.execute(sql, valores)

    auditoria.registrar_accion(
        accion='EDITAR_USUARIO',
        entidad='usuario',
        entidad_id=u['usuario'],
        detalle=f"Modificó los datos del usuario @{u['usuario']}",
        operador=yo
    )

    actualizado = db.query("SELECT * FROM usuarios WHERE id = ?", [usuario_id])[0]
    return jsonify(operador=usuario_a_json(actualizado))


@bp.post('/admin/operadores/<int:usuario_id>/pin')
@sesiones.requiere_admin
def generar_pin_usuario(usuario_id: int):
    filas = db.query("SELECT * FROM usuarios WHERE id = ? LIMIT 1", [usuario_id])
    if not filas:
        return jsonify(error="El usuario no existe."), 404
    u = filas[0]

    if not bool(u.get('activo', 1)):
        return jsonify(error="El usuario está dado de baja."), 400

    pin = credenciales.generar_pin(u)
    app_url = request.host_url.rstrip('/')
    enlace = credenciales.enlace_whatsapp(u, pin, url_acceso=app_url)

    yo = sesiones.usuario_actual()
    auditoria.registrar_accion(
        accion='GENERAR_PIN',
        entidad='usuario',
        entidad_id=u['usuario'],
        detalle=f"Generó un PIN temporal para @{u['usuario']}",
        operador=yo
    )

    return jsonify(
        pin=pin,
        enlaceWhatsapp=enlace,
        minutosVigencia=credenciales.HORAS_VIGENCIA * 60,
        horasVigencia=credenciales.HORAS_VIGENCIA,
        telefono=u.get('telefono'),
        operador=usuario_a_json(u)
    )


@bp.delete('/admin/operadores/<int:usuario_id>')
@sesiones.requiere_admin
def eliminar_usuario(usuario_id: int):
    filas = db.query("SELECT * FROM usuarios WHERE id = ? LIMIT 1", [usuario_id])
    if not filas:
        return jsonify(error="El usuario no existe."), 404
    u = filas[0]

    yo = sesiones.usuario_actual()
    if yo and yo['id'] == usuario_id:
        return jsonify(error="No podés eliminar tu propia cuenta."), 400

    db.execute("UPDATE usuarios SET activo = 0 WHERE id = ?", [usuario_id])
    auditoria.registrar_accion(
        accion='BAJA_LOGICA_USUARIO',
        entidad='usuario',
        entidad_id=u['usuario'],
        detalle=f"Dio de baja la cuenta de @{u['usuario']}",
        operador=yo
    )

    return jsonify(ok=True)


@bp.get('/admin/auditoria')
@sesiones.requiere_admin
def obtener_auditoria():
    limite = min(int(request.args.get('limite', 50)), 200)
    registros = auditoria.listar_auditoria(limite)
    return jsonify(auditoria=registros)
