# -*- coding: utf-8 -*-
"""Módulo de Seguridad y Hashing de Contraseñas.

Utiliza Argon2id con fallback a PBKDF2-HMAC-SHA256 (estándar nativo de Python).
"""

import hashlib
import hmac
import os
import secrets
from typing import Optional

LARGO_MINIMO = 8

CLAVES_PROHIBIDAS = {
    '12345678', 'password', 'contrasena', 'contraseña', 'admin123',
    'sistema2026', 'admin2026', 'qwerty123', 'cambiar123'
}

_argon2_disponible = False
try:
    from argon2 import PasswordHasher
    _hasher = PasswordHasher()
    _argon2_disponible = True
except ImportError:
    _hasher = None


def hashear(clave: str) -> str:
    """Genera un hash criptográfico robusto."""
    if _argon2_disponible and _hasher:
        return _hasher.hash(clave)

    # Fallback seguro nativo PBKDF2
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac('sha256', clave.encode('utf-8'), salt.encode('utf-8'), 600000)
    return f"pbkdf2:sha256:600000${salt}${dk.hex()}"


def verificar(hash_guardado: str, clave: str) -> bool:
    """Verifica si la contraseña coincide con el hash guardado."""
    if not hash_guardado or not clave:
        return False

    if hash_guardado.startswith('$argon2'):
        if not _argon2_disponible or not _hasher:
            return False
        try:
            return _hasher.verify(hash_guardado, clave)
        except Exception:
            return False

    if hash_guardado.startswith('pbkdf2:sha256:'):
        try:
            partes = hash_guardado.split('$')
            if len(partes) != 3:
                return False
            _, salt, dk_esperado = partes
            dk_calculado = hashlib.pbkdf2_hmac(
                'sha256', clave.encode('utf-8'), salt.encode('utf-8'), 600000
            ).hex()
            return hmac.compare_digest(dk_esperado, dk_calculado)
        except Exception:
            return False

    return False


def necesita_rehash(hash_guardado: str) -> bool:
    if _argon2_disponible and _hasher:
        if not hash_guardado.startswith('$argon2'):
            return True
        try:
            return _hasher.check_needs_rehash(hash_guardado)
        except Exception:
            return True
    return False


def revisar_fuerza(clave: str) -> Optional[str]:
    if not clave or len(clave) < LARGO_MINIMO:
        return f"La contraseña debe contener al menos {LARGO_MINIMO} caracteres."
    if clave.lower() in CLAVES_PROHIBIDAS:
        return "Esa contraseña es demasiado común o predecible. Por favor elegí una más segura."
    return None
