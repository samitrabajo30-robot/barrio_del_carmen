const config = window.BARRIO_CONFIG || {};
const configured = Boolean(config.supabaseUrl && config.supabaseAnonKey && window.supabase?.createClient);
const client = configured ? window.supabase.createClient(config.supabaseUrl, config.supabaseAnonKey) : null;
const el = (selector) => document.querySelector(selector);
let currentComplaints = [];
let selectedImage = null;

if (!configured) el('#setup-notice').hidden = false;

async function checkSession() {
  if (!client) return;
  const { data: { session } } = await client.auth.getSession();
  if (!session) return;
  const { data, error } = await client.from('admins').select('user_id').eq('user_id', session.user.id).maybeSingle();
  if (error || !data) {
    await client.auth.signOut();
    el('#login-error').textContent = 'Esta cuenta no tiene autorización de administración.';
    return;
  }
  el('#login-panel').hidden = true;
  el('#dashboard').hidden = false;
  await loadContent();
  await loadComplaints();
}

el('#login-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  el('#login-error').textContent = '';
  if (!client) { el('#login-error').textContent = 'Primero hay que conectar Supabase siguiendo README.md.'; return; }
  const form = new FormData(event.currentTarget);
  const { error } = await client.auth.signInWithPassword({ email: form.get('email'), password: form.get('password') });
  if (error) { el('#login-error').textContent = 'No se pudo iniciar sesión. Revisá tus datos o la configuración.'; return; }
  await checkSession();
});

el('#logout').addEventListener('click', async () => { await client?.auth.signOut(); location.reload(); });
document.querySelectorAll('.tab').forEach((tab) => tab.addEventListener('click', () => {
  document.querySelectorAll('.tab').forEach((item) => item.classList.toggle('active', item === tab));
  document.querySelectorAll('.panel').forEach((panel) => { panel.hidden = panel.id !== tab.dataset.panel; });
  if (tab.dataset.panel === 'complaints-panel') loadComplaints();
}));

async function loadContent() {
  const { data, error } = await client.from('site_content').select('key,value');
  if (error) { el('#content-message').textContent = 'No se pudo cargar el contenido. Revisá la configuración.'; return; }
  const content = Object.fromEntries(data.map((item) => [item.key, item.value]));
  el('[name="intro"]').value = content.intro || '';
  el('[name="history"]').value = content.history || '';
  el('[name="extra"]').value = content.extra_text || '';
  showImage(content.hero_image);
}

function showImage(url) {
  const preview = el('#image-preview');
  if (!url) { preview.hidden = true; preview.replaceChildren(); return; }
  const image = document.createElement('img'); image.src = url; image.alt = 'Vista previa de la imagen actual';
  preview.replaceChildren(image); preview.hidden = false;
}

el('[name="hero-image"]').addEventListener('change', (event) => {
  selectedImage = event.target.files[0] || null;
  if (!selectedImage) return;
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(selectedImage.type) || selectedImage.size > 5 * 1024 * 1024) {
    selectedImage = null; event.target.value = '';
    el('#content-message').textContent = 'Elegí una imagen JPG, PNG o WEBP de hasta 5 MB.'; return;
  }
  showImage(URL.createObjectURL(selectedImage)); el('#content-message').textContent = '';
});

el('#content-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const message = el('#content-message'); message.textContent = 'Guardando…';
  const values = new FormData(event.currentTarget);
  let heroImageUrl;
  if (selectedImage) {
    const ext = selectedImage.type.split('/')[1].replace('jpeg', 'jpg');
    const filePath = `presentacion-${Date.now()}.${ext}`;
    const { error: uploadError } = await client.storage.from('public-assets').upload(filePath, selectedImage, { contentType: selectedImage.type });
    if (uploadError) { message.textContent = 'No se pudo subir la imagen. Revisá los permisos del almacenamiento.'; return; }
    heroImageUrl = client.storage.from('public-assets').getPublicUrl(filePath).data.publicUrl;
  }
  const rows = [{ key: 'intro', value: values.get('intro').trim() }, { key: 'history', value: values.get('history').trim() }, { key: 'extra_text', value: values.get('extra').trim() }];
  if (heroImageUrl) rows.push({ key: 'hero_image', value: heroImageUrl });
  const { error } = await client.from('site_content').upsert(rows, { onConflict: 'key' });
  message.textContent = error ? 'No se pudieron guardar los cambios. Revisá la conexión y los permisos.' : 'Cambios guardados. La página pública los mostrará al actualizarse.';
  if (!error) selectedImage = null;
});

function complaintQuery() {
  let query = client.from('complaints').select('id,problem_date,problem_time,zone,topic,description,status,created_at').order('created_at', { ascending: false });
  const from = el('#filter-from').value, to = el('#filter-to').value;
  const topic = el('#filter-topic').value, zone = el('#filter-zone').value.trim(), status = el('#filter-status').value;
  if (from) query = query.gte('problem_date', from);
  if (to) query = query.lte('problem_date', to);
  if (topic) query = query.eq('topic', topic);
  if (zone) query = query.ilike('zone', `%${zone}%`);
  if (status) query = query.eq('status', status);
  return query;
}

async function loadComplaints() {
  const message = el('#complaint-message'); message.textContent = 'Cargando avisos…';
  const allRows = [];
  for (let offset = 0; ; offset += 1000) {
    const { data, error } = await complaintQuery().range(offset, offset + 999);
    if (error) { currentComplaints = []; message.textContent = 'No se pudo cargar la lista. Revisá los filtros y permisos.'; renderComplaints([]); return; }
    allRows.push(...data);
    if (data.length < 1000) break;
  }
  currentComplaints = allRows; message.textContent = `${allRows.length} aviso${allRows.length === 1 ? '' : 's'} encontrado${allRows.length === 1 ? '' : 's'}.`; renderComplaints(allRows);
}

function renderComplaints(rows) {
  const body = el('#complaint-rows'); body.replaceChildren();
  if (!rows.length) { const row = body.insertRow(); const cell = row.insertCell(); cell.colSpan = 6; cell.className = 'empty-row'; cell.textContent = 'No hay avisos para estos filtros.'; return; }
  for (const item of rows) {
    const row = body.insertRow();
    [new Date(item.created_at).toLocaleString('es-AR'), `${item.problem_date} · ${String(item.problem_time).slice(0, 5)}`, item.zone, item.topic, item.description].forEach((value) => { row.insertCell().textContent = value; });
    const statusCell = row.insertCell(), select = document.createElement('select');
    [['recibida', 'Recibida'], ['en_gestion', 'En gestión'], ['resuelta', 'Resuelta']].forEach(([value, label]) => { const option = document.createElement('option'); option.value = value; option.textContent = label; select.append(option); });
    select.value = item.status;
    select.addEventListener('change', async () => {
      select.disabled = true; const nextStatus = select.value;
      const { error } = await client.from('complaints').update({ status: nextStatus }).eq('id', item.id);
      if (error) { select.value = item.status; el('#complaint-message').textContent = 'No se pudo actualizar el estado.'; }
      else { item.status = nextStatus; el('#complaint-message').textContent = 'Estado actualizado.'; }
      select.disabled = false;
    });
    statusCell.append(select);
  }
}

el('#refresh-complaints').addEventListener('click', loadComplaints);
['#filter-from', '#filter-to', '#filter-topic', '#filter-zone', '#filter-status'].forEach((selector) => el(selector).addEventListener('change', loadComplaints));
el('#filter-zone').addEventListener('search', loadComplaints);
el('#export-xlsx').addEventListener('click', () => {
  if (!window.XLSX) { el('#complaint-message').textContent = 'No se cargó el generador de Excel. Revisá tu conexión.'; return; }
  const report = currentComplaints.map((item) => ({ 'Fecha del problema': item.problem_date, 'Horario aproximado': String(item.problem_time).slice(0, 5), 'Zona afectada': item.zone, 'Tema': item.topic, 'Descripción': item.description, 'Fecha y hora de envío': new Date(item.created_at).toLocaleString('es-AR'), 'Estado': ({ recibida: 'Recibida', en_gestion: 'En gestión', resuelta: 'Resuelta' })[item.status] || item.status }));
  const sheet = XLSX.utils.json_to_sheet(report); sheet['!cols'] = [{ wch: 18 }, { wch: 18 }, { wch: 24 }, { wch: 18 }, { wch: 60 }, { wch: 24 }, { wch: 16 }];
  const book = XLSX.utils.book_new(); XLSX.utils.book_append_sheet(book, sheet, 'Avisos vecinales');
  XLSX.writeFile(book, `avisos-barrio-del-carmen-${new Date().toISOString().slice(0, 10)}.xlsx`);
});

checkSession();
