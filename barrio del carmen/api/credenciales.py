# -*- coding: utf-8 -*-
"""PIN Temporal de Activación y Enlace de WhatsApp Web."""

import secrets
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union

from db import db
import seguridad

LARGO_PIN = 4
HORAS_VIGENCIA = 24
MAX_INTENTOS_PIN = 5


def ahora_utc() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class RechazoPin:
    motivo: str


GENERICO_PIN = RechazoPin("El PIN ingresado es incorrecto o ha expirado. Solicitá uno nuevo al administrador.")


def normalizar_telefono(texto: Optional[str]) -> str:
    if not texto:
        return ''
    solo_digitos = ''.join(c for c in str(texto) if c.isdigit())
    if len(solo_digitos) == 10 and not solo_digitos.startswith('54'):
        return '549' + solo_digitos
    return solo_digitos


def generar_pin(u: Dict[str, Any]) -> str:
    pin = str(secrets.randbelow(10 ** LARGO_PIN)).zfill(LARGO_PIN)
    pin_hash = seguridad.hashear(pin)
    expira = (ahora_utc() + timedelta(hours=HORAS_VIGENCIA)).strftime('%Y-%m-%d %H:%M:%S')

    db.execute(
        """UPDATE usuarios
           SET pin_hash = ?, pin_expira_en = ?, pin_intentos = 0, debe_cambiar_clave = 1
           WHERE id = ?""",
        [pin_hash, expira, u['id']]
    )
    return pin


def invalidar_pin(usuario_id: int) -> None:
    db.execute(
        "UPDATE usuarios SET pin_hash = NULL, pin_expira_en = NULL, pin_intentos = 0 WHERE id = ?",
        [usuario_id]
    )


def validar_pin(usuario: str, pin: str) -> Union[Dict[str, Any], RechazoPin]:
    usr = (usuario or '').strip().lower()
    pin = (pin or '').strip()
    if not usr or not pin:
        return GENERICO_PIN

    filas = db.query("SELECT * FROM usuarios WHERE lower(usuario) = ? LIMIT 1", [usr])
    if not filas:
        return GENERICO_PIN
    u = filas[0]

    if not bool(u.get('activo', 1)):
        return GENERICO_PIN

    pin_hash = u.get('pin_hash')
    expira_str = u.get('pin_expira_en')
    if not pin_hash or not expira_str:
        return GENERICO_PIN

    try:
        dt_expira = datetime.fromisoformat(expira_str.replace('Z', '+00:00'))
        if dt_expira.tzinfo is None:
            dt_expira = dt_expira.replace(tzinfo=timezone.utc)
        if dt_expira <= ahora_utc():
            invalidar_pin(u['id'])
            return GENERICO_PIN
    except Exception:
        return GENERICO_PIN

    intentos = u.get('pin_intentos', 0)
    if intentos >= MAX_INTENTOS_PIN:
        invalidar_pin(u['id'])
        return GENERICO_PIN

    if not seguridad.verificar(pin_hash, pin):
        nuevos = intentos + 1
        if nuevos >= MAX_INTENTOS_PIN:
            invalidar_pin(u['id'])
        else:
            db.execute("UPDATE usuarios SET pin_intentos = ? WHERE id = ?", [nuevos, u['id']])
        return GENERICO_PIN

    return u


def cambiar_clave_con_pin(usuario: str, pin: str, nueva: str, confirmacion: str) -> Optional[RechazoPin]:
    resultado = validar_pin(usuario, pin)
    if isinstance(resultado, RechazoPin):
        return resultado
    u = resultado

    nueva = (nueva or '').strip()
    confirmacion = (confirmacion or '').strip()

    if nueva != confirmacion:
        return RechazoPin("Las contraseñas no coinciden.")

    error_fuerza = seguridad.revisar_fuerza(nueva)
    if error_fuerza:
        return RechazoPin(error_fuerza)

    if nueva == pin:
        return RechazoPin("La nueva contraseña no puede ser igual al PIN.")

    nuevo_hash = seguridad.hashear(nueva)
    db.execute(
        """UPDATE usuarios
           SET hash_clave = ?, debe_cambiar_clave = 0, pin_hash = NULL,
               pin_expira_en = NULL, pin_intentos = 0, intentos_fallidos = 0,
               bloqueado_hasta = NULL
           WHERE id = ?""",
        [nuevo_hash, u['id']]
    )
    return None


def enlace_whatsapp(u: Dict[str, Any], pin: str, url_acceso: str = '') -> Optional[str]:
    telefono = normalizar_telefono(u.get('telefono'))
    if len(telefono) < 10:
        return None

    url_base = url_acceso.rstrip('/') if url_acceso else 'https://tu-sitio-web.com/admin.html'
    nombre = u.get('nombre', 'Estimado/a')
    usuario = u.get('usuario', '')

    mensaje = (
        f"Hola {nombre}, acá están tus credenciales de acceso para el panel de la Junta Vecinal:\n\n"
        f"👤 *Usuario:* {usuario}\n"
        f"🔑 *PIN Temporal:* {pin}\n"
        f"🌐 *Enlace:* {url_base}\n\n"
        f"⏳ Vigencia: {HORAS_VIGENCIA} horas (un solo uso).\n"
        f"Ingresá a la web, elegí 'Ingresar con PIN' y configurá tu clave personal."
    )

    return f"https://wa.me/{telefono}?text={urllib.parse.quote(mensaje)}"
