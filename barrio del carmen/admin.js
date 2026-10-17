// =============================================================================
// LÓGICA DEL PANEL DE ADMINISTRACIÓN (TURSO CLOUD + API SERVERLESS)
// =============================================================================

const el = (selector) => document.querySelector(selector);
let currentComplaints = [];
let currentUser = null;

// =============================================================================
// 1. SESIÓN Y AUTENTICACIÓN
// =============================================================================

async function checkSession() {
  try {
    const res = await fetch('/api/auth/sesion', { credentials: 'include' });
    if (!res.ok) {
      showLogin();
      return;
    }
    const data = await res.json();
    if (data.operador) {
      currentUser = data.operador;
      showDashboard(currentUser);
      return;
    }
  } catch (e) {
    console.warn('Sin sesión previa');
  }
  showLogin();
}

function showLogin() {
  currentUser = null;
  el('#login-panel').hidden = false;
  el('#dashboard').hidden = true;
}

function showDashboard(user) {
  el('#login-panel').hidden = true;
  el('#dashboard').hidden = false;
  el('#user-greeting').textContent = `Conectado como: ${user.nombre} (@${user.usuario}) · ROL: ${user.rol.toUpperCase()}`;

  // Ocultar pestañas de administración avanzada si no es admin
  const esAdmin = user.rol === 'admin';
  el('#tab-users').hidden = !esAdmin;
  el('#tab-audit').hidden = !esAdmin;

  loadContent();
  loadComplaints();
}

// Selector de pestañas de login (Contraseña vs PIN)
el('#tab-login-clave').addEventListener('click', () => {
  el('#tab-login-clave').classList.add('active');
  el('#tab-login-pin').classList.remove('active');
  el('#login-form').hidden = false;
  el('#pin-login-form').hidden = true;
});

el('#tab-login-pin').addEventListener('click', () => {
  el('#tab-login-pin').classList.add('active');
  el('#tab-login-clave').classList.remove('active');
  el('#pin-login-form').hidden = false;
  el('#login-form').hidden = true;
});

// Login con usuario y contraseña
el('#login-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const errorEl = el('#login-error');
  errorEl.textContent = '';

  const usuario = el('#login-usuario').value.trim();
  const clave = el('#login-password').value.trim();

  try {
    const res = await fetch('/api/auth/iniciar-sesion', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ usuario, clave })
    });
    const data = await res.json();

    if (res.ok && data.operador) {
      currentUser = data.operador;
      showDashboard(currentUser);
    } else {
      errorEl.textContent = data.error || 'Credenciales incorrectas.';
    }
  } catch (err) {
    errorEl.textContent = 'No se pudo conectar con el servidor.';
  }
});

// Login con PIN - Paso 1: Validar PIN
el('#btn-validar-pin').addEventListener('click', async () => {
  const errorEl = el('#pin-error');
  errorEl.textContent = '';

  const usuario = el('#pin-user').value.trim();
  const pin = el('#pin-code').value.trim();

  if (!usuario || !pin) {
    errorEl.textContent = 'Ingresá tu usuario y el PIN de 4 dígitos.';
    return;
  }

  try {
    const res = await fetch('/api/auth/pin/validar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ usuario, pin })
    });
    const data = await res.json();

    if (res.ok && data.ok) {
      el('#pin-nombre-usuario').textContent = data.nombre || usuario;
      el('#pin-paso-1').hidden = true;
      el('#pin-paso-2').hidden = false;
    } else {
      errorEl.textContent = data.error || 'PIN incorrecto o expirado.';
    }
  } catch (err) {
    errorEl.textContent = 'Error de conexión.';
  }
});

// Login con PIN - Paso 2: Guardar nueva contraseña e ingresar
el('#pin-login-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const errorEl = el('#pin-error');
  errorEl.textContent = '';

  const usuario = el('#pin-user').value.trim();
  const pin = el('#pin-code').value.trim();
  const nueva = el('#pin-nueva-clave').value.trim();
  const confirmacion = el('#pin-confirma-clave').value.trim();

  if (nueva !== confirmacion) {
    errorEl.textContent = 'Las contraseñas no coinciden.';
    return;
  }

  try {
    const res = await fetch('/api/auth/pin/clave', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ usuario, pin, nueva, confirmacion })
    });
    const data = await res.json();

    if (res.ok && data.ok) {
      // Iniciar sesión inmediatamente con la nueva clave
      const loginRes = await fetch('/api/auth/iniciar-sesion', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ usuario, clave: nueva })
      });
      const loginData = await loginRes.json();
      if (loginRes.ok && loginData.operador) {
        showDashboard(loginData.operador);
      } else {
        location.reload();
      }
    } else {
      errorEl.textContent = data.error || 'No se pudo guardar la contraseña.';
    }
  } catch (err) {
    errorEl.textContent = 'Error al comunicarse con el servidor.';
  }
});

// Cerrar sesión
el('#logout').addEventListener('click', async () => {
  try {
    await fetch('/api/auth/cerrar-sesion', { method: 'POST', credentials: 'include' });
  } catch (e) {}
  showLogin();
});

// Pestañas del Dashboard
document.querySelectorAll('.tab[data-panel]').forEach((tab) => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab[data-panel]').forEach((t) => t.classList.remove('active'));
    tab.classList.add('active');

    document.querySelectorAll('.panel').forEach((panel) => {
      panel.hidden = panel.id !== tab.dataset.panel;
    });

    if (tab.dataset.panel === 'events-panel') loadAdminEvents();
    if (tab.dataset.panel === 'businesses-panel') loadAdminBusinesses();
    if (tab.dataset.panel === 'complaints-panel') loadComplaints();
    if (tab.dataset.panel === 'users-panel') loadUsers();
    if (tab.dataset.panel === 'audit-panel') loadAudit();
  });
});

// =============================================================================
// EVENTOS VECINALES Y AGENDA COMUNITARIA
// =============================================================================

el('#btn-toggle-nuevo-evento')?.addEventListener('click', () => {
  const wrap = el('#form-nuevo-evento-wrap');
  wrap.hidden = !wrap.hidden;
});

el('#btn-cancelar-nuevo-evento')?.addEventListener('click', () => {
  el('#form-nuevo-evento-wrap').hidden = true;
});

async function loadAdminEvents() {
  const tbody = el('#event-rows');
  const msg = el('#events-message');
  msg.textContent = 'Cargando eventos…';

  try {
    const res = await fetch('/api/admin/eventos', { credentials: 'include' });
    if (!res.ok) {
      msg.textContent = 'Error al cargar eventos.';
      return;
    }
    const data = await res.json();
    const eventos = data.eventos || [];
    msg.textContent = `${eventos.length} evento(s) cargado(s).`;
    renderAdminEvents(eventos);
  } catch (err) {
    msg.textContent = 'Error al conectar para obtener los eventos.';
  }
}

function renderAdminEvents(eventos) {
  const tbody = el('#event-rows');
  tbody.replaceChildren();

  if (!eventos.length) {
    const tr = tbody.insertRow();
    const td = tr.insertCell();
    td.colSpan = 6;
    td.className = 'empty-row';
    td.textContent = 'No hay eventos cargados aún.';
    return;
  }

  for (const ev of eventos) {
    const tr = tbody.insertRow();
    [ev.fecha, ev.horario ? ev.horario.slice(0, 5) : '-', ev.nombre, ev.lugar, ev.descripcion].forEach((txt) => {
      tr.insertCell().textContent = txt || '-';
    });

    const actionsCell = tr.insertCell();
    const btnEliminar = document.createElement('button');
    btnEliminar.className = 'quiet-button';
    btnEliminar.textContent = '✕ Eliminar';
    btnEliminar.style.color = '#a23f32';
    btnEliminar.addEventListener('click', async () => {
      if (!confirm(`¿Eliminar el evento "${ev.nombre}"?`)) return;
      try {
        const res = await fetch(`/api/admin/eventos/${ev.id}`, {
          method: 'DELETE',
          credentials: 'include'
        });
        if (res.ok) {
          loadAdminEvents();
        } else {
          alert('No se pudo eliminar el evento.');
        }
      } catch (e) {
        alert('Error de conexión.');
      }
    });
    actionsCell.append(btnEliminar);
  }
}

el('#form-crear-evento')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const msg = el('#new-event-message');
  msg.textContent = 'Guardando evento…';

  const payload = {
    nombre: el('#new-event-name').value.trim(),
    fecha: el('#new-event-date').value,
    horario: el('#new-event-time').value,
    lugar: el('#new-event-place').value.trim(),
    descripcion: el('#new-event-description').value.trim()
  };

  try {
    const res = await fetch('/api/admin/eventos', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(payload)
    });
    const data = await res.json();

    if (res.ok && data.ok) {
      msg.textContent = '¡Evento publicado con éxito!';
      el('#form-crear-evento').reset();
      el('#form-nuevo-evento-wrap').hidden = true;
      loadAdminEvents();
    } else {
      msg.textContent = data.error || 'No se pudo guardar el evento.';
    }
  } catch (err) {
    msg.textContent = 'Error de conexión con el servidor.';
  }
});

// =============================================================================
// COMERCIOS Y SERVICIOS DEL BARRIO
// =============================================================================

el('#btn-toggle-nuevo-comercio')?.addEventListener('click', () => {
  const wrap = el('#form-nuevo-comercio-wrap');
  wrap.hidden = !wrap.hidden;
});

el('#btn-cancelar-nuevo-comercio')?.addEventListener('click', () => {
  el('#form-nuevo-comercio-wrap').hidden = true;
});

async function loadAdminBusinesses() {
  const tbody = el('#business-rows');
  const msg = el('#businesses-message');
  msg.textContent = 'Cargando comercios…';

  try {
    const res = await fetch('/api/admin/comercios', { credentials: 'include' });
    if (!res.ok) {
      msg.textContent = 'Error al cargar comercios.';
      return;
    }
    const data = await res.json();
    const comercios = data.comercios || [];
    msg.textContent = `${comercios.length} comercio(s) registrado(s).`;
    renderAdminBusinesses(comercios);
  } catch (err) {
    msg.textContent = 'Error al conectar para obtener los comercios.';
  }
}

function renderAdminBusinesses(comercios) {
  const tbody = el('#business-rows');
  tbody.replaceChildren();

  if (!comercios.length) {
    const tr = tbody.insertRow();
    const td = tr.insertCell();
    td.colSpan = 6;
    td.className = 'empty-row';
    td.textContent = 'No hay comercios cargados todavía.';
    return;
  }

  for (const c of comercios) {
    const tr = tbody.insertRow();
    [c.nombre, c.categoria, c.direccion || '-', c.telefono || '-', c.descripcion].forEach((txt) => {
      tr.insertCell().textContent = txt || '-';
    });

    const actionsCell = tr.insertCell();
    const btnEliminar = document.createElement('button');
    btnEliminar.className = 'quiet-button';
    btnEliminar.textContent = '✕ Eliminar';
    btnEliminar.style.color = '#a23f32';
    btnEliminar.addEventListener('click', async () => {
      if (!confirm(`¿Eliminar el comercio "${c.nombre}"?`)) return;
      try {
        const res = await fetch(`/api/admin/comercios/${c.id}`, {
          method: 'DELETE',
          credentials: 'include'
        });
        if (res.ok) {
          loadAdminBusinesses();
        } else {
          alert('No se pudo eliminar el comercio.');
        }
      } catch (e) {
        alert('Error de conexión.');
      }
    });
    actionsCell.append(btnEliminar);
  }
}

el('#form-crear-comercio')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const msg = el('#new-business-message');
  msg.textContent = 'Guardando comercio…';

  const payload = {
    nombre: el('#new-business-name').value.trim(),
    categoria: el('#new-business-category').value,
    direccion: el('#new-business-address').value.trim(),
    telefono: el('#new-business-phone').value.trim(),
    descripcion: el('#new-business-description').value.trim()
  };

  try {
    const res = await fetch('/api/admin/comercios', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(payload)
    });
    const data = await res.json();

    if (res.ok && data.ok) {
      msg.textContent = '¡Comercio agregado con éxito!';
      el('#form-crear-comercio').reset();
      el('#form-nuevo-comercio-wrap').hidden = true;
      loadAdminBusinesses();
    } else {
      msg.textContent = data.error || 'No se pudo agregar el comercio.';
    }
  } catch (err) {
    msg.textContent = 'Error al comunicarse con el servidor.';
  }
});


// =============================================================================
// 2. CONTENIDO DE LA PÁGINA
// =============================================================================

async function loadContent() {
  try {
    const res = await fetch('/api/contenido');
    if (!res.ok) return;
    const data = await res.json();
    const content = data.contenido || {};

    el('#edit-intro').value = content.intro || '';
    el('#edit-history').value = content.history || '';
    el('#edit-extra').value = content.extra_text || '';
    el('#edit-hero-image').value = content.hero_image || '';
    el('#edit-video-url').value = content.video_url || '';
  } catch (e) {
    el('#content-message').textContent = 'No se pudo cargar el contenido actual.';
  }
}

el('#content-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const message = el('#content-message');
  message.textContent = 'Guardando cambios…';

  const payload = {
    intro: el('#edit-intro').value.trim(),
    history: el('#edit-history').value.trim(),
    extra_text: el('#edit-extra').value.trim(),
    hero_image: el('#edit-hero-image').value.trim(),
    video_url: el('#edit-video-url').value.trim()
  };

  try {
    const res = await fetch('/api/admin/contenido', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(payload)
    });
    const data = await res.json();

    if (res.ok && data.ok) {
      message.textContent = '¡Cambios guardados con éxito! Ya se ven reflejados en la página pública.';
    } else {
      message.textContent = data.error || 'No se pudieron guardar los cambios.';
    }
  } catch (err) {
    message.textContent = 'Error al conectar con el servidor.';
  }
});

// =============================================================================
// 3. AVISOS Y QUEJAS VECINALES (Con Excel)
// =============================================================================

async function loadComplaints() {
  const message = el('#complaint-message');
  message.textContent = 'Cargando avisos…';

  const params = new URLSearchParams();
  const desde = el('#filter-from').value;
  const hasta = el('#filter-to').value;
  const tema = el('#filter-topic').value;
  const zona = el('#filter-zone').value.trim();
  const estado = el('#filter-status').value;

  if (desde) params.append('desde', desde);
  if (hasta) params.append('hasta', hasta);
  if (tema) params.append('tema', tema);
  if (zona) params.append('zona', zona);
  if (estado) params.append('estado', estado);

  try {
    const res = await fetch(`/api/admin/reclamos?${params.toString()}`, { credentials: 'include' });
    if (!res.ok) {
      message.textContent = 'Error al cargar los avisos.';
      return;
    }
    const data = await res.json();
    currentComplaints = data.reclamos || [];
    message.textContent = `${currentComplaints.length} aviso(s) encontrado(s).`;
    renderComplaints(currentComplaints);
  } catch (err) {
    message.textContent = 'No se pudo conectar para obtener los avisos.';
  }
}

function renderComplaints(rows) {
  const tbody = el('#complaint-rows');
  tbody.replaceChildren();

  if (!rows.length) {
    const tr = tbody.insertRow();
    const td = tr.insertCell();
    td.colSpan = 6;
    td.className = 'empty-row';
    td.textContent = 'No hay avisos para los filtros seleccionados.';
    return;
  }

  for (const item of rows) {
    const tr = tbody.insertRow();
    const fechaEnvio = item.creado_en ? new Date(item.creado_en).toLocaleString('es-AR') : '-';
    const fechaProblema = `${item.fecha_problema || ''} ${String(item.hora_problema || '').slice(0, 5)}`;

    [fechaEnvio, fechaProblema, item.zona, item.tema, item.descripcion].forEach((texto) => {
      tr.insertCell().textContent = texto;
    });

    const statusCell = tr.insertCell();
    const select = document.createElement('select');
    [
      ['recibida', 'Recibida'],
      ['en_gestion', 'En gestión'],
      ['resuelta', 'Resuelta']
    ].forEach(([val, label]) => {
      const opt = document.createElement('option');
      opt.value = val;
      opt.textContent = label;
      select.append(opt);
    });
    select.value = item.estado;

    select.addEventListener('change', async () => {
      select.disabled = true;
      const nuevoEstado = select.value;
      try {
        const res = await fetch(`/api/admin/reclamos/${item.id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ estado: nuevoEstado })
        });
        if (res.ok) {
          item.estado = nuevoEstado;
          el('#complaint-message').textContent = 'Estado del aviso actualizado.';
        } else {
          select.value = item.estado;
          el('#complaint-message').textContent = 'No se pudo actualizar el estado.';
        }
      } catch (e) {
        select.value = item.estado;
        el('#complaint-message').textContent = 'Error al actualizar estado.';
      }
      select.disabled = false;
    });

    statusCell.append(select);
  }
}

el('#refresh-complaints').addEventListener('click', loadComplaints);
['#filter-from', '#filter-to', '#filter-topic', '#filter-status'].forEach((s) => {
  el(s).addEventListener('change', loadComplaints);
});
el('#filter-zone').addEventListener('input', () => {
  clearTimeout(window._searchTimeout);
  window._searchTimeout = setTimeout(loadComplaints, 400);
});

// Descargar Excel (.xlsx)
el('#export-xlsx').addEventListener('click', () => {
  const datosExcel = currentComplaints.length > 0
    ? currentComplaints.map((c) => ({
        'Fecha de Envío': c.creado_en ? new Date(c.creado_en).toLocaleString('es-AR') : '',
        'Fecha del Problema': c.fecha_problema,
        'Horario Aproximado': c.hora_problema,
        'Zona del Barrio': c.zona,
        'Tema': c.tema,
        'Descripción del Reclamo': c.descripcion,
        'Estado': (c.estado || 'RECIBIDA').toUpperCase()
      }))
    : [{
        'Fecha de Envío': new Date().toLocaleString('es-AR'),
        'Fecha del Problema': '-',
        'Horario Aproximado': '-',
        'Zona del Barrio': '-',
        'Tema': 'Sin avisos',
        'Descripción del Reclamo': 'No hay reclamos registrados aún en la base de datos.',
        'Estado': 'PLANILLA INICIAL'
      }];

  const hoja = XLSX.utils.json_to_sheet(datosExcel);
  const libro = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(libro, hoja, 'Avisos y Quejas');

  const fechaHoy = new Date().toISOString().slice(0, 10);
  XLSX.writeFile(libro, `Reclamos_Barrio_Del_Carmen_${fechaHoy}.xlsx`);
});

// =============================================================================
// 4. GESTIÓN DE USUARIOS Y OPERADORES
// =============================================================================

el('#btn-toggle-nuevo-usuario').addEventListener('click', () => {
  const wrap = el('#form-nuevo-usuario-wrap');
  wrap.hidden = !wrap.hidden;
});

el('#btn-cancelar-nuevo-usuario').addEventListener('click', () => {
  el('#form-nuevo-usuario-wrap').hidden = true;
});

async function loadUsers() {
  const tbody = el('#user-rows');
  tbody.innerHTML = '<tr><td colspan="6" class="empty-row">Cargando usuarios…</td></tr>';

  try {
    const res = await fetch('/api/admin/operadores', { credentials: 'include' });
    if (!res.ok) {
      tbody.innerHTML = '<tr><td colspan="6" class="empty-row">Error al cargar usuarios o permisos insuficientes.</td></tr>';
      return;
    }
    const data = await res.json();
    const usuarios = data.operadores || [];

    tbody.replaceChildren();
    if (!usuarios.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="empty-row">No hay operadores cargados.</td></tr>';
      return;
    }

    for (const u of usuarios) {
      const tr = tbody.insertRow();
      tr.insertCell().textContent = u.nombre;
      tr.insertCell().textContent = `@${u.usuario}`;
      tr.insertCell().textContent = u.rol.toUpperCase();
      tr.insertCell().textContent = u.area || '-';
      tr.insertCell().textContent = u.telefono || '-';

      const actionsCell = tr.insertCell();
      actionsCell.style.display = 'flex';
      actionsCell.style.gap = '6px';

      // Botón Generar PIN WhatsApp
      const btnPin = document.createElement('button');
      btnPin.className = 'quiet-button';
      btnPin.textContent = '🔑 PIN / WhatsApp';
      btnPin.title = 'Generar PIN temporal de 4 dígitos para este usuario';
      btnPin.addEventListener('click', () => generarPinUsuario(u.id));

      // Botón Dar de baja
      const btnBaja = document.createElement('button');
      btnBaja.className = 'quiet-button';
      btnBaja.textContent = '✕ Baja';
      btnBaja.style.color = '#a23f32';
      btnBaja.addEventListener('click', async () => {
        if (!confirm(`¿Dar de baja al usuario @${u.usuario}?`)) return;
        const delRes = await fetch(`/api/admin/operadores/${u.id}`, {
          method: 'DELETE',
          credentials: 'include'
        });
        if (delRes.ok) loadUsers();
      });

      actionsCell.append(btnPin, btnBaja);
    }
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="6" class="empty-row">Error de conexión.</td></tr>';
  }
}

// Crear Usuario
el('#form-crear-usuario').addEventListener('submit', async (e) => {
  e.preventDefault();
  const msg = el('#new-user-message');
  msg.textContent = 'Creando usuario…';

  const payload = {
    nombre: el('#new-user-nombre').value.trim(),
    usuario: el('#new-user-usuario').value.trim(),
    rol: el('#new-user-rol').value,
    area: el('#new-user-area').value.trim(),
    telefono: el('#new-user-telefono').value.trim()
  };

  try {
    const res = await fetch('/api/admin/operadores', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(payload)
    });
    const data = await res.json();

    if (res.ok && data.operador) {
      msg.textContent = `¡Usuario @${data.operador.usuario} creado!`;
      el('#form-crear-usuario').reset();
      el('#form-nuevo-usuario-wrap').hidden = true;
      loadUsers();

      // Ofrecer de inmediato generar el PIN para WhatsApp
      if (confirm(`¿Querés generar ahora mismo el PIN de activación para enviar a @${data.operador.usuario} por WhatsApp?`)) {
        generarPinUsuario(data.operador.id);
      }
    } else {
      msg.textContent = data.error || 'No se pudo crear el usuario.';
    }
  } catch (err) {
    msg.textContent = 'Error al comunicarse con el servidor.';
  }
});

// Generar PIN y abrir modal WhatsApp
async function generarPinUsuario(id) {
  try {
    const res = await fetch(`/api/admin/operadores/${id}/pin`, {
      method: 'POST',
      credentials: 'include'
    });
    const data = await res.json();

    if (res.ok && data.pin) {
      el('#modal-pin-user').textContent = `@${data.operador.usuario} (${data.operador.nombre})`;
      el('#modal-pin-valor').textContent = data.pin;

      const whatsappBtn = el('#modal-pin-whatsapp');
      if (data.enlaceWhatsapp) {
        whatsappBtn.href = data.enlaceWhatsapp;
        whatsappBtn.hidden = false;
      } else {
        whatsappBtn.hidden = true;
      }

      el('#pin-modal').showModal();
    } else {
      alert(data.error || 'No se pudo generar el PIN.');
    }
  } catch (e) {
    alert('Error al generar el PIN temporal.');
  }
}

el('#modal-pin-close').addEventListener('click', () => {
  el('#pin-modal').close();
});

// =============================================================================
// 5. AUDITORÍA
// =============================================================================

async function loadAudit() {
  const tbody = el('#audit-rows');
  tbody.innerHTML = '<tr><td colspan="6" class="empty-row">Cargando registros…</td></tr>';

  try {
    const res = await fetch('/api/admin/auditoria?limite=100', { credentials: 'include' });
    if (!res.ok) {
      tbody.innerHTML = '<tr><td colspan="6" class="empty-row">No se pudo cargar la auditoría.</td></tr>';
      return;
    }
    const data = await res.json();
    const rows = data.auditoria || [];

    tbody.replaceChildren();
    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="empty-row">No hay registros aún.</td></tr>';
      return;
    }

    for (const item of rows) {
      const tr = tbody.insertRow();
      tr.insertCell().textContent = item.creado_en ? item.creado_en.replace('T', ' ').slice(0, 19) : '-';
      tr.insertCell().textContent = `${item.nombre_usuario || ''} (@${item.usuario})`;
      tr.insertCell().textContent = item.accion;
      tr.insertCell().textContent = item.entidad;
      tr.insertCell().textContent = item.detalle;
      tr.insertCell().textContent = item.ip || '-';
    }
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="6" class="empty-row">Error de conexión.</td></tr>';
  }
}

el('#refresh-audit').addEventListener('click', loadAudit);

// Verificación inicial al cargar la página
checkSession();
