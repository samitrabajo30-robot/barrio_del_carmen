let businesses = [];
let selectedCategory = 'Todos';

const businessList = document.querySelector('#business-list');
const searchInput = document.querySelector('#business-search');
const MESES = ['ENE', 'FEB', 'MAR', 'ABR', 'MAY', 'JUN', 'JUL', 'AGO', 'SEP', 'OCT', 'NOV', 'DIC'];

function escapeHtml(text) {
  if (!text) return '';
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function renderBusinesses() {
  const query = searchInput.value.trim().toLocaleLowerCase('es-AR');
  const filtered = businesses.filter((business) => {
    const matchesCategory = selectedCategory === 'Todos' || business.category === selectedCategory;
    const matchesQuery = `${business.name} ${business.category} ${business.description}`.toLocaleLowerCase('es-AR').includes(query);
    return matchesCategory && matchesQuery;
  });

  const categoryTab = document.querySelector('[data-category="Todos"] span');
  if (categoryTab) categoryTab.textContent = businesses.length;

  if (!filtered.length) {
    businessList.innerHTML = `<div class="business-empty"><div class="empty-icon" aria-hidden="true">⌕</div><div><h3>${query || selectedCategory !== 'Todos' ? 'No encontramos resultados.' : 'El directorio está en preparación.'}</h3><p>${query || selectedCategory !== 'Todos' ? 'Probá con otro nombre o rubro.' : 'Pronto vas a encontrar comercios y servicios del barrio. La Junta Vecinal validará la información antes de publicarla.'}</p></div></div>`;
    return;
  }
  businessList.innerHTML = filtered.map((business) => `
    <article class="business-card">
      <span class="tag">${escapeHtml(business.category)}</span>
      <h3>${escapeHtml(business.name)}</h3>
      <p>${escapeHtml(business.description)}</p>
      ${business.address ? `<div class="business-meta"><span>📍</span> <span>${escapeHtml(business.address)}</span></div>` : ''}
      ${business.phone ? `<div class="business-meta"><span>📞</span> <a href="tel:${escapeHtml(business.phone)}">${escapeHtml(business.phone)}</a></div>` : ''}
    </article>
  `).join('');
}

async function loadBusinesses() {
  try {
    const res = await fetch('/api/comercios');
    if (!res.ok) return;
    const data = await res.json();
    if (Array.isArray(data.comercios)) {
      businesses = data.comercios.map((c) => ({
        name: c.nombre,
        category: c.categoria,
        description: c.descripcion,
        address: c.direccion,
        phone: c.telefono
      }));
      renderBusinesses();
    }
  } catch (err) {
    console.warn('Directorio comercial en modo local/preparación.');
  }
}

function formatFechaEvento(fechaStr) {
  if (!fechaStr) return { dia: '—', mes: 'PRÓX', texto: 'Fecha a confirmar' };
  try {
    const match = String(fechaStr).match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (match) {
      const anio = match[1];
      const mesNum = parseInt(match[2], 10);
      const diaNum = parseInt(match[3], 10);
      const mesesCortos = ['ENE', 'FEB', 'MAR', 'ABR', 'MAY', 'JUN', 'JUL', 'AGO', 'SEP', 'OCT', 'NOV', 'DIC'];
      const mesesLargos = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
      const mesCorto = mesesCortos[mesNum - 1] || 'MES';
      const mesLargo = mesesLargos[mesNum - 1] || '';
      return {
        dia: String(diaNum).padStart(2, '0'),
        mes: mesCorto,
        texto: `${diaNum} de ${mesLargo} de ${anio}`
      };
    }
  } catch (e) {}
  return { dia: '—', mes: 'PRÓX', texto: fechaStr };
}

async function loadEvents() {
  const container = document.querySelector('#events-container');
  if (!container) return;
  try {
    const res = await fetch('/api/eventos');
    if (!res.ok) return;
    const data = await res.json();
    const eventos = data.eventos || [];

    if (!eventos.length) {
      container.innerHTML = `
        <div class="news-empty">
          <div class="news-calendar"><span>PRÓXIMO</span><strong>—</strong><small>A CONFIRMAR</small></div>
          <div><span class="tag">AGENDA VECINAL</span><h3>Estamos preparando el próximo encuentro.</h3><p>Las novedades y actividades oficiales se publicarán por este medio.</p></div>
          <span class="news-spark" aria-hidden="true">✳</span>
        </div>`;
      return;
    }

    container.innerHTML = eventos.map((ev) => {
      const infoFecha = formatFechaEvento(ev.fecha);
      const horario = ev.horario ? ev.horario.slice(0, 5) : '';

      return `
        <article class="event-item">
          <div class="news-calendar">
            <span>${infoFecha.mes}</span>
            <strong>${infoFecha.dia}</strong>
            <small>${horario ? `${horario} HS` : 'A CONFIRMAR'}</small>
          </div>
          <div class="event-info">
            <span class="tag">AGENDA VECINAL</span>
            <h3>${escapeHtml(ev.nombre)}</h3>
            <p>${escapeHtml(ev.descripcion)}</p>
            <div class="event-meta">
              <span>📅 <strong>Fecha del evento:</strong> ${infoFecha.texto}</span>
              ${horario ? `<span>🕒 <strong>Horario:</strong> ${horario} hs</span>` : ''}
              ${ev.lugar ? `<span>📍 <strong>Lugar:</strong> ${escapeHtml(ev.lugar)}</span>` : ''}
            </div>
          </div>
          <span class="news-spark" aria-hidden="true">✳</span>
        </article>`;
    }).join('');
  } catch (err) {
    console.warn('No se pudieron cargar los eventos:', err);
  }
}

searchInput.addEventListener('input', renderBusinesses);
document.querySelectorAll('.category-chip').forEach((button) => button.addEventListener('click', () => {
  document.querySelector('.category-chip.active')?.classList.remove('active');
  button.classList.add('active');
  selectedCategory = button.dataset.category;
  renderBusinesses();
}));
renderBusinesses();
loadBusinesses();
loadEvents();

async function loadPublicContent() {
  try {
    const res = await fetch('/api/contenido');
    if (!res.ok) return;
    const data = await res.json();
    const content = data.contenido || {};
    if (content.intro) document.querySelector('#site-intro').textContent = content.intro;
    if (content.history) document.querySelector('#site-history').textContent = content.history;
    if (content.extra_text) {
      const extra = document.querySelector('#site-extra');
      extra.textContent = content.extra_text;
      extra.hidden = false;
    }
    if (content.hero_image) {
      const art = document.querySelector('#hero-art');
      const image = document.querySelector('#hero-photo');
      if (image && art) {
        image.src = content.hero_image;
        image.hidden = false;
        art.classList.add('has-photo');
      }
    }
    if (content.video_url) {
      const videoWrap = document.querySelector('#site-video-wrap');
      if (videoWrap) {
        const rawUrl = content.video_url.trim();
        const ytMatch = rawUrl.match(/(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))([\w-]{11})/);
        if (ytMatch && ytMatch[1]) {
          const safeId = encodeURIComponent(ytMatch[1]);
          videoWrap.innerHTML = `<iframe width="100%" height="280" src="https://www.youtube.com/embed/${safeId}" title="Video del barrio" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen style="border-radius: 16px; margin-top: 1rem;"></iframe>`;
          videoWrap.hidden = false;
        } else {
          videoWrap.hidden = true;
        }
      }
    }
  } catch (e) {
    console.warn('Contenido dinámico en modo local/preparación.');
  }
}
loadPublicContent();

const menuToggle = document.querySelector('.menu-toggle');
const nav = document.querySelector('#main-nav');
menuToggle.addEventListener('click', () => {
  const isOpen = nav.classList.toggle('open');
  menuToggle.setAttribute('aria-expanded', String(isOpen));
});
nav.querySelectorAll('a').forEach((link) => link.addEventListener('click', () => {
  nav.classList.remove('open');
  menuToggle.setAttribute('aria-expanded', 'false');
}));

document.addEventListener('keydown', (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault();
    searchInput.focus();
  }
});

const dialog = document.querySelector('#participation-dialog');
const formFields = document.querySelector('#form-fields');
const formPreview = document.querySelector('#form-preview');
const dialogNotice = document.querySelector('#dialog-notice');
const dialogSubmit = document.querySelector('#dialog-submit');
const forms = {
  complaint: {
    tag: 'AVISOS Y QUEJAS',
    title: 'Contanos qué pasa.',
    copy: 'La Junta Vecinal recibirá este aviso para darle seguimiento. No hace falta que escribas tu nombre ni teléfono.',
    notice: 'El aviso se enviará de forma privada a la Junta Vecinal. No se publicará en la página.',
    submit: 'Enviar aviso <span>↗</span>',
    fields: [['Fecha del problema', 'date', 'problem-date'], ['Horario aproximado', 'time', 'problem-time'], ['Zona del barrio', 'text', 'zone'], ['Tema', 'select', 'topic'], ['Descripción', 'textarea', 'description']],
  },
  event: {
    tag: 'EVENTOS VECINALES',
    title: 'Compartí tu evento.',
    copy: 'Proponé una actividad, festejo o encuentro comunitario para los vecinos del barrio.',
    notice: 'Tu propuesta será enviada a la Junta Vecinal y, una vez aprobada, aparecerá publicada en Novedades del barrio con la fecha y hora indicadas.',
    submit: 'Enviar propuesta de evento <span>↗</span>',
    fields: [['Nombre del evento', 'text', 'event-name'], ['Descripción', 'textarea', 'description'], ['Fecha', 'date', 'event-date'], ['Horario', 'time', 'event-time'], ['Lugar', 'text', 'place']],
  },
};

document.querySelectorAll('.open-form').forEach((button) => button.addEventListener('click', () => {
  const config = forms[button.dataset.form];
  document.querySelector('#dialog-tag').textContent = config.tag;
  document.querySelector('#dialog-title').textContent = config.title;
  document.querySelector('#dialog-copy').textContent = config.copy;
  dialogNotice.textContent = config.notice;
  dialogSubmit.innerHTML = config.submit;
  formPreview.textContent = '';
  formFields.innerHTML = config.fields.map(([label, type, name]) => {
    if (type === 'select') return `<label>${label}<select name="${name}" required><option value="">Elegí una opción</option><option>Alumbrado</option><option>Calles</option><option>Residuos</option><option>Servicios</option><option>Otro</option></select></label>`;
    if (type === 'textarea') return `<label>${label}<textarea name="${name}" required maxlength="500" placeholder="Escribí un mensaje breve"></textarea></label>`;
    return `<label>${label}<input name="${name}" type="${type}" ${type === 'text' ? 'maxlength="100"' : ''} required></label>`;
  }).join('');
  dialog.showModal();
}));

document.querySelector('#demo-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const values = new FormData(form);
  if (values.get('website')) return;

  const tag = document.querySelector('#dialog-tag').textContent;

  if (tag === 'AVISOS Y QUEJAS') {
    formPreview.textContent = 'Enviando aviso a la Junta Vecinal…';
    try {
      const payload = {
        'problem-date': values.get('problem-date'),
        'problem-time': values.get('problem-time'),
        'zone': values.get('zone'),
        'topic': values.get('topic'),
        'description': values.get('description'),
        'website': values.get('website') || ''
      };

      const res = await fetch('/api/reclamos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      if (res.ok && data.ok) {
        form.reset();
        formPreview.textContent = 'Tu aviso fue enviado a la Junta Vecinal. Gracias por ayudar a cuidar el barrio.';
      } else {
        formPreview.textContent = data.error || 'No pudimos enviar el aviso. Revisá los datos e intentá más tarde.';
      }
    } catch (err) {
      formPreview.textContent = 'No pudimos conectar con el servidor. Revisá tu conexión e intentá de nuevo.';
    }
    return;
  }

  if (tag === 'EVENTOS VECINALES') {
    formPreview.textContent = 'Enviando propuesta de evento a la Junta Vecinal…';
    try {
      const payload = {
        'event-name': values.get('event-name'),
        'description': values.get('description'),
        'event-date': values.get('event-date'),
        'event-time': values.get('event-time'),
        'place': values.get('place'),
        'website': values.get('website') || ''
      };

      const res = await fetch('/api/eventos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      if (res.ok && data.ok) {
        form.reset();
        formPreview.textContent = data.mensaje || '¡Tu propuesta de evento fue enviada con éxito! Aparecerá en Novedades del barrio una vez aprobada por la Junta Vecinal.';
        loadEvents();
      } else {
        formPreview.textContent = data.error || 'No pudimos enviar la propuesta. Revisá los campos e intentá más tarde.';
      }
    } catch (err) {
      formPreview.textContent = 'No pudimos conectar con el servidor. Revisá tu conexión e intentá de nuevo.';
    }
    return;
  }
});

dialog.addEventListener('click', (event) => {
  if (event.target === dialog) dialog.close();
});

