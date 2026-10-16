# -*- coding: utf-8 -*-
"""Control de Sesiones y Autenticación de Operadores."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Dict, Optional, Union

from flask import g, jsonify, session

from config import ROLES
from db import db
import seguridad

MAX_INTENTOS = 5
MINUTOS_BLOQUEO = 15


def ahora_utc() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Rechazo:
    motivo: str
    minutos: Optional[int] = None


def como_json(u: Dict[str, Any]) -> Dict[str, Any]:
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
    }


def buscar_por_usuario(usuario: str) -> Optional[Dict[str, Any]]:
    usr = (usuario or '').strip().lower()
    filas = db.query("SELECT * FROM usuarios WHERE lower(usuario) = ? LIMIT 1", [usr])
    return filas[0] if filas else None


def buscar_por_id(uid: int) -> Optional[Dict[str, Any]]:
    filas = db.query("SELECT * FROM usuarios WHERE id = ? LIMIT 1", [uid])
    return filas[0] if filas else None


def autenticar(usuario: str, clave: str) -> Union[Dict[str, Any], Rechazo]:
    u = buscar_por_usuario(usuario)
    generico = Rechazo("Usuario o contraseña incorrectos.")

    if not u:
        return generico

    if not bool(u.get('activo', 1)):
        return Rechazo("Tu usuario se encuentra deshabilitado. Consultá con la Junta Vecinal.")

    bloqueado_hasta = u.get('bloqueado_hasta')
    if bloqueado_hasta:
        try:
            dt_bloqueo = datetime.fromisoformat(bloqueado_hasta.replace('Z', '+00:00'))
            if dt_bloqueo.tzinfo is None:
                dt_bloqueo = dt_bloqueo.replace(tzinfo=timezone.utc)
            if dt_bloqueo > ahora_utc():
                faltan = int((dt_bloqueo - ahora_utc()).total_seconds() // 60) + 1
                return Rechazo("Cuenta temporalmente bloqueada por intentos fallidos.", minutos=faltan)
        except Exception:
            pass

    hash_guardado = u.get('hash_clave', '')
    if not seguridad.verificar(hash_guardado, clave):
        intentos = (u.get('intentos_fallidos') or 0) + 1
        if intentos >= MAX_INTENTOS:
            hasta = (ahora_utc() + timedelta(minutes=MINUTOS_BLOQUEO)).strftime('%Y-%m-%d %H:%M:%S')
            db.execute(
                "UPDATE usuarios SET intentos_fallidos = 0, bloqueado_hasta = ? WHERE id = ?",
                [hasta, u['id']]
            )
            return Rechazo("Demasiados intentos fallidos. Bloqueado temporalmente.", minutos=MINUTOS_BLOQUEO)
        else:
            db.execute("UPDATE usuarios SET intentos_fallidos = ? WHERE id = ?", [intentos, u['id']])
            return generico

    # Limpiar bloqueos
    sql_update = "UPDATE usuarios SET intentos_fallidos = 0, bloqueado_hasta = NULL"
    params = []
    if seguridad.necesita_rehash(hash_guardado):
        sql_update += ", hash_clave = ?"
        params.append(seguridad.hashear(clave))
    sql_update += " WHERE id = ?"
    params.append(u['id'])
    db.execute(sql_update, params)

    return u


def iniciar(u: Dict[str, Any]) -> None:
    session.clear()
    session['usuario_id'] = u['id']
    session.permanent = True


def cerrar() -> None:
    session.clear()


def usuario_actual() -> Optional[Dict[str, Any]]:
    if 'usuario_actual' in g:
        return g.usuario_actual

    uid = session.get('usuario_id')
    g.usuario_actual = None
    if uid:
        u = buscar_por_id(uid)
        if u and bool(u.get('activo', 1)):
            g.usuario_actual = u
        else:
            session.clear()
    return g.usuario_actual


def requiere_sesion(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if usuario_actual() is None:
            return jsonify(error="Se requiere iniciar sesión."), 401
        return fn(*args, **kwargs)
    return wrapper


def requiere_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        u = usuario_actual()
        if u is None:
            return jsonify(error="Se requiere iniciar sesión."), 401
        if u.get('rol') != 'admin':
            return jsonify(error="Acción reservada únicamente para administradores."), 403
        return fn(*args, **kwargs)
    return wrapper
