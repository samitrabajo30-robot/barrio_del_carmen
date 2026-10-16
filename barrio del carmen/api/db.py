# -*- coding: utf-8 -*-
"""Conector de Base de Datos Híbrido: Turso Cloud (libSQL) + SQLite Local.

Si TURSO_DATABASE_URL está configurada, se comunica directamente con Turso
mediante su Pipeline HTTP v2 nativo (/v2/pipeline), con CERO dependencias C
adicionales (usa urllib y json estándar).
"""

import json
import os
import sqlite3
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import config

LOCAL_DB_PATH = Path(__file__).resolve().parent / 'barrio_local.db'


def _es_turso() -> bool:
    """Detecta si se debe conectar a Turso Cloud."""
    url = (config.TURSO_DATABASE_URL or '').lower().strip()
    return url.startswith('http://') or url.startswith('https://') or url.startswith('libsql://')


def _normalizar_url_turso(url: str) -> str:
    """Convierte libsql:// a https:// y asegura el endpoint /v2/pipeline."""
    url = url.strip()
    if url.startswith('libsql://'):
        url = url.replace('libsql://', 'https://')
    if not url.startswith('http://') and not url.startswith('https://'):
        url = 'https://' + url
    url = url.rstrip('/')
    if not url.endswith('/v2/pipeline'):
        url += '/v2/pipeline'
    return url


def _param_a_turso(val: Any) -> Dict[str, Any]:
    """Convierte un valor de Python al formato esperado por el pipeline de Turso."""
    if val is None:
        return {'type': 'null'}
    if isinstance(val, bool):
        return {'type': 'integer', 'value': '1' if val else '0'}
    if isinstance(val, int):
        return {'type': 'integer', 'value': str(val)}
    if isinstance(val, float):
        return {'type': 'float', 'value': val}
    return {'type': 'text', 'value': str(val)}


def _turso_a_python(val_obj: Any) -> Any:
    """Convierte un valor devuelto por Turso a tipo nativo de Python."""
    if not isinstance(val_obj, dict):
        return val_obj
    tipo = val_obj.get('type')
    if tipo == 'null':
        return None
    val = val_obj.get('value')
    if tipo == 'integer':
        return int(val) if val is not None else None
    if tipo == 'float':
        return float(val) if val is not None else None
    return val


class ClienteTurso:
    """Cliente HTTP nativo para Turso Cloud libSQL Pipeline v2."""

    def __init__(self, db_url: str, token: str):
        self.url = _normalizar_url_turso(db_url)
        self.token = token.strip()

    def ejecutar_pipeline(self, peticiones: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        body = json.dumps({'requests': peticiones}).encode('utf-8')
        req = urllib.request.Request(
            self.url,
            data=body,
            headers={
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json',
                'User-Agent': 'BarrioDelCarmen-Turso/1.0',
            },
            method='POST',
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                results = data.get('results', [])
                for r in results:
                    if r.get('type') == 'error':
                        err = r.get('error', {})
                        raise RuntimeError(f"Error en consulta Turso: {err.get('message', 'Desconocido')}")
                return results
        except urllib.error.HTTPError as e:
            detalle = ''
            try:
                detalle = e.read().decode('utf-8')
            except Exception:
                pass
            raise RuntimeError(f"Falla HTTP de Turso ({e.code}): {e.reason}. Detalle: {detalle}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"No se pudo conectar al cluster de Turso: {e.reason}")

    def query(self, sql: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        args = [_param_a_turso(p) for p in (params or [])]
        reqs = [
            {'type': 'execute', 'stmt': {'sql': sql, 'args': args}},
            {'type': 'close'},
        ]
        res = self.ejecutar_pipeline(reqs)
        if not res:
            return []
        ejec = res[0]
        if ejec.get('type') != 'ok':
            return []
        resp_obj = ejec.get('response', {}).get('result', {})
        cols = [c.get('name') for c in resp_obj.get('cols', [])]
        filas = []
        for row in resp_obj.get('rows', []):
            valores = [_turso_a_python(col) for col in row]
            filas.append(dict(zip(cols, valores)))
        return filas

    def execute(self, sql: str, params: Optional[List[Any]] = None) -> Tuple[Optional[int], int]:
        args = [_param_a_turso(p) for p in (params or [])]
        reqs = [
            {'type': 'execute', 'stmt': {'sql': sql, 'args': args}},
            {'type': 'close'},
        ]
        res = self.ejecutar_pipeline(reqs)
        if not res:
            return (None, 0)
        ejec = res[0]
        if ejec.get('type') != 'ok':
            return (None, 0)
        resp_obj = ejec.get('response', {}).get('result', {})
        last_id = resp_obj.get('last_insert_rowid')
        last_id_int = int(last_id) if last_id is not None else None
        affected = resp_obj.get('affected_row_count', 0)
        return (last_id_int, affected)

    def executescript(self, script_text: str) -> None:
        """Ejecuta múltiples sentencias SQL en lote eliminando comentarios."""
        lineas_limpias = []
        for linea in script_text.splitlines():
            linea_sin_comentario = linea.split('--')[0].strip()
            if linea_sin_comentario:
                lineas_limpias.append(linea_sin_comentario)

        texto_limpio = ' '.join(lineas_limpias)
        sentencias = [s.strip() for s in texto_limpio.split(';') if s.strip()]
        if not sentencias:
            return

        reqs = []
        for s in sentencias:
            reqs.append({'type': 'execute', 'stmt': {'sql': s, 'args': []}})
        reqs.append({'type': 'close'})
        self.ejecutar_pipeline(reqs)


class ClienteSQLiteLocal:
    """Cliente para SQLite local integrado cuando no hay conexión externa."""

    def __init__(self, db_path: Path):
        self.db_path = db_path

    def _conectar(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def query(self, sql: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        with self._conectar() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params or [])
            return [dict(row) for row in cursor.fetchall()]

    def execute(self, sql: str, params: Optional[List[Any]] = None) -> Tuple[Optional[int], int]:
        with self._conectar() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params or [])
            conn.commit()
            return (cursor.lastrowid, cursor.rowcount)

    def executescript(self, script_text: str) -> None:
        with self._conectar() as conn:
            conn.executescript(script_text)
            conn.commit()


# Instancia del motor de base de datos
def obtener_db():
    if _es_turso():
        return ClienteTurso(config.TURSO_DATABASE_URL, config.TURSO_AUTH_TOKEN)
    return ClienteSQLiteLocal(LOCAL_DB_PATH)


db = obtener_db()


def es_turso_activo() -> bool:
    return _es_turso()


def inicializar_tablas() -> None:
    """Lee schema.sql y aplica las tablas si no existen."""
    schema_path = Path(__file__).resolve().parent / 'schema.sql'
    if schema_path.exists():
        sql = schema_path.read_text(encoding='utf-8')
        motor = obtener_db()
        motor.executescript(sql)
