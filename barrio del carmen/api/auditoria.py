# -*- coding: utf-8 -*-
"""Registro de Auditoría y Trazabilidad de Acciones Administrativas."""

from typing import Any, Dict, Optional
from flask import request

from db import db


def registrar_accion(
    accion: str,
    entidad: str,
    entidad_id: Optional[str] = None,
    detalle: str = '',
    operador: Optional[Dict[str, Any]] = None,
    ip: Optional[str] = None
) -> None:
    ip_origen = ip or (request.headers.get('X-Forwarded-For', request.remote_addr) if request else '127.0.0.1')
    if ip_origen and ',' in ip_origen:
        ip_origen = ip_origen.split(',')[0].strip()

    usuario = operador.get('usuario', 'sistema') if operador else 'anonimo'
    nombre = operador.get('nombre', 'Sistema') if operador else 'Anónimo'
    rol = operador.get('rol', 'sistema') if operador else 'anonimo'
    uid = operador.get('id') if operador else None

    try:
        db.execute(
            """INSERT INTO auditoria
               (usuario_id, usuario, nombre_usuario, rol, accion, entidad, entidad_id, detalle, ip)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [uid, usuario, nombre, rol, accion, entidad, str(entidad_id) if entidad_id else None, detalle, ip_origen]
        )
    except Exception as e:
        print(f"[AUDITORIA ERROR] {e}")


def listar_auditoria(limite: int = 50) -> list:
    return db.query(
        """SELECT id, usuario, nombre_usuario, rol, accion, entidad, entidad_id, detalle, ip, creado_en
           FROM auditoria
           ORDER BY id DESC
           LIMIT ?""",
        [limite]
    )
