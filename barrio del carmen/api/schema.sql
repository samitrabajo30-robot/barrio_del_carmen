-- =============================================================================
-- ESQUEMA DE BASE DE DATOS: BARRIO DEL CARMEN · TURSO CLOUD / LIBSQL
-- =============================================================================

-- 1. Tabla de Usuarios y Operadores
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT NOT NULL UNIQUE COLLATE NOCASE,
    hash_clave TEXT NOT NULL,
    nombre TEXT NOT NULL,
    rol TEXT NOT NULL DEFAULT 'operador',
    area TEXT,
    email TEXT,
    telefono TEXT,
    activo INTEGER NOT NULL DEFAULT 1,
    debe_cambiar_clave INTEGER NOT NULL DEFAULT 0,
    intentos_fallidos INTEGER NOT NULL DEFAULT 0,
    bloqueado_hasta TEXT,
    pin_hash TEXT,
    pin_expira_en TEXT,
    pin_intentos INTEGER NOT NULL DEFAULT 0,
    creado_en TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);

CREATE INDEX IF NOT EXISTS idx_usuarios_usuario ON usuarios(usuario);
CREATE INDEX IF NOT EXISTS idx_usuarios_rol ON usuarios(rol);
CREATE INDEX IF NOT EXISTS idx_usuarios_activo ON usuarios(activo);

-- 2. Tabla de Auditoría
CREATE TABLE IF NOT EXISTS auditoria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER,
    usuario TEXT NOT NULL,
    nombre_usuario TEXT,
    rol TEXT,
    accion TEXT NOT NULL,
    entidad TEXT NOT NULL,
    entidad_id TEXT,
    detalle TEXT NOT NULL,
    ip TEXT,
    creado_en TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);

CREATE INDEX IF NOT EXISTS idx_auditoria_usuario ON auditoria(usuario);
CREATE INDEX IF NOT EXISTS idx_auditoria_creado_en ON auditoria(creado_en);

-- 3. Tabla de Reclamos y Avisos Vecinales
CREATE TABLE IF NOT EXISTS reclamos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_problema TEXT NOT NULL,
    hora_problema TEXT NOT NULL,
    zona TEXT NOT NULL,
    tema TEXT NOT NULL,
    descripcion TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'recibida',
    creado_en TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);

CREATE INDEX IF NOT EXISTS idx_reclamos_estado ON reclamos(estado);
CREATE INDEX IF NOT EXISTS idx_reclamos_creado_en ON reclamos(creado_en);

-- 4. Tabla de Contenido Dinámico de la Página Web
CREATE TABLE IF NOT EXISTS contenido_sitio (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL,
    actualizado_en TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);

-- 5. Tabla de Eventos Vecinales y Agenda Comunitaria
CREATE TABLE IF NOT EXISTS eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    descripcion TEXT NOT NULL,
    fecha TEXT NOT NULL,
    horario TEXT NOT NULL,
    lugar TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'publicado',
    creado_en TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);

CREATE INDEX IF NOT EXISTS idx_eventos_fecha ON eventos(fecha);
CREATE INDEX IF NOT EXISTS idx_eventos_estado ON eventos(estado);

-- 6. Tabla de Comercios y Servicios del Barrio
CREATE TABLE IF NOT EXISTS comercios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    categoria TEXT NOT NULL,
    descripcion TEXT NOT NULL,
    direccion TEXT,
    telefono TEXT,
    activo INTEGER NOT NULL DEFAULT 1,
    creado_en TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);

CREATE INDEX IF NOT EXISTS idx_comercios_categoria ON comercios(categoria);
CREATE INDEX IF NOT EXISTS idx_comercios_activo ON comercios(activo);

-- Valores iniciales del sitio
INSERT INTO contenido_sitio (clave, valor) VALUES
('intro', 'Este es un punto de encuentro para quienes viven y trabajan en el barrio. Queremos compartir información útil, celebrar lo que hacemos juntos y encontrar soluciones entre todos.'),
('history', 'La historia de Nuestra Señora del Carmen se sumará próximamente con el aporte de sus vecinos.'),
('extra_text', ''),
('hero_image', ''),
('video_url', '')
ON CONFLICT (clave) DO NOTHING;

-- Administrador Inicial: usuario 'admin' con clave 'Admin2026!'
INSERT INTO usuarios (usuario, hash_clave, nombre, rol, area, activo, debe_cambiar_clave)
VALUES (
    'admin',
    'pbkdf2:sha256:600000$7584c245947a5a5b1139f2dc7c3248ec$80f8943b5e6251a943beef1b3841f1522f98eb55cd85bb8a6a3070949a216604',
    'Administrador Junta Vecinal',
    'admin',
    'Junta Vecinal',
    1,
    0
)
ON CONFLICT (usuario) DO NOTHING;
