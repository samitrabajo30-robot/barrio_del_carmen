# -*- coding: utf-8 -*-
"""Rutas de Autenticación, Sesión y Validación de PIN."""

from flask import Blueprint, jsonify, request

import auditoria
import credenciales
import seguridad
import sesiones
from db import db

bp = Blueprint('auth', __name__, url_prefix='/api')


@bp.post('/auth/iniciar-sesion')
@bp.post('/sesion')
def iniciar_sesion():
    datos = request.get_json(silent=True) or {}
    usuario = datos.get('usuario', '')
    clave = datos.get('clave', '')

    res = sesiones.autenticar(usuario, clave)
    if isinstance(res, sesiones.Rechazo):
        cuerpo = {'error': res.motivo}
        if res.minutos:
            cuerpo['minutos'] = res.minutos
        return jsonify(cuerpo), 401

    sesiones.iniciar(res)
    auditoria.registrar_accion(
        accion='INICIO_SESION',
        entidad='sesion',
        entidad_id=res.get('usuario'),
        detalle=f"Inicio de sesión exitoso ({res.get('rol')})",
        operador=res
    )
    return jsonify(operador=sesiones.como_json(res))


@bp.post('/auth/cerrar-sesion')
@bp.delete('/auth/sesion')
@bp.delete('/sesion')
def cerrar_sesion():
    u = sesiones.usuario_actual()
    if u:
        auditoria.registrar_accion(
            accion='CIERRE_SESION',
            entidad='sesion',
            entidad_id=u.get('usuario'),
            detalle="Cierre de sesión voluntario",
            operador=u
        )
    sesiones.cerrar()
    return jsonify(ok=True)


@bp.get('/auth/sesion')
@bp.get('/sesion')
def quien_soy():
    u = sesiones.usuario_actual()
    if not u:
        return jsonify(operador=None), 401
    return jsonify(operador=sesiones.como_json(u))


@bp.post('/sesion/clave')
@sesiones.requiere_sesion
def cambiar_clave():
    datos = request.get_json(silent=True) or {}
    u = sesiones.usuario_actual()
    nueva = (datos.get('nueva') or '').strip()
    actual = datos.get('actual', '')

    if not bool(u.get('debe_cambiar_clave')):
        if not seguridad.verificar(u.get('hash_clave', ''), actual):
            return jsonify(error="La contraseña actual ingresada es incorrecta."), 400

    error_fuerza = seguridad.revisar_fuerza(nueva)
    if error_fuerza:
        return jsonify(error=error_fuerza), 400

    if seguridad.verificar(u.get('hash_clave', ''), nueva):
        return jsonify(error="La nueva contraseña debe ser distinta de la actual."), 400

    nuevo_hash = seguridad.hashear(nueva)
    db.execute(
        "UPDATE usuarios SET hash_clave = ?, debe_cambiar_clave = 0 WHERE id = ?",
        [nuevo_hash, u['id']]
    )

    auditoria.registrar_accion(
        accion='CAMBIO_CLAVE_PROPIA',
        entidad='usuario',
        entidad_id=u.get('usuario'),
        detalle="Actualizó su contraseña personal",
        operador=u
    )
    return jsonify(ok=True)


@bp.post('/auth/pin/validar')
def validar_pin():
    datos = request.get_json(silent=True) or {}
    res = credenciales.validar_pin(datos.get('usuario', ''), datos.get('pin', ''))
    if isinstance(res, credenciales.RechazoPin):
        return jsonify(error=res.motivo), 401
    return jsonify(ok=True, nombre=res.get('nombre', ''))


@bp.post('/auth/pin/clave')
def cambiar_clave_con_pin():
    datos = request.get_json(silent=True) or {}
    usuario = datos.get('usuario', '')

    rechazo = credenciales.cambiar_clave_con_pin(
        usuario=usuario,
        pin=datos.get('pin', ''),
        nueva=datos.get('nueva', ''),
        confirmacion=datos.get('confirmacion', ''),
    )
    if rechazo:
        return jsonify(error=rechazo.motivo), 400

    auditoria.registrar_accion(
        accion='CLAVE_DEFINIDA_CON_PIN',
        entidad='usuario',
        entidad_id=(usuario or '').strip().lower(),
        detalle="Definió su contraseña usando PIN temporal",
        operador=None
    )
    return jsonify(ok=True)
