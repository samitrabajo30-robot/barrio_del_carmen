const businesses = [];
let selectedCategory = 'Todos';

const businessList = document.querySelector('#business-list');
const searchInput = document.querySelector('#business-search');

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
  businessList.innerHTML = filtered.map((business) => `<article class="business-card"><span class="tag">${business.category}</span><h3>${business.name}</h3><p>${business.description}</p></article>`).join('');
}

searchInput.addEventListener('input', renderBusinesses);
document.querySelectorAll('.category-chip').forEach((button) => button.addEventListener('click', () => {
  document.querySelector('.category-chip.active')?.classList.remove('active');
  button.classList.add('active');
  selectedCategory = button.dataset.category;
  renderBusinesses();
}));
renderBusinesses();

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
    tag: 'AVISOS Y QUEJAS', title: 'Contanos qué pasa.', copy: 'La Junta Vecinal recibirá este aviso para darle seguimiento. No hace falta que escribas tu nombre ni teléfono.',
    fields: [['Fecha del problema', 'date', 'problem-date'], ['Horario aproximado', 'time', 'problem-time'], ['Zona del barrio', 'text', 'zone'], ['Tema', 'select', 'topic'], ['Descripción', 'textarea', 'description']],
  },
  event: {
    tag: 'EVENTOS VECINALES', title: 'Compartí tu evento.', copy: 'Esta vista previa te muestra la información que se pediría para invitar a los vecinos.',
    fields: [['Nombre del evento', 'text', 'event-name'], ['Descripción', 'textarea', 'description'], ['Fecha', 'date', 'event-date'], ['Horario', 'time', 'event-time'], ['Lugar', 'text', 'place']],
  },
};

document.querySelectorAll('.open-form').forEach((button) => button.addEventListener('click', () => {
  const config = forms[button.dataset.form];
  document.querySelector('#dialog-tag').textContent = config.tag;
  document.querySelector('#dialog-title').textContent = config.title;
  document.querySelector('#dialog-copy').textContent = config.copy;
  const isComplaint = button.dataset.form === 'complaint';
  dialogNotice.textContent = isComplaint
    ? 'El aviso se enviará de forma privada a la Junta Vecinal. No se publicará en la página.'
    : 'La publicación de eventos todavía no está activada. Esta opción muestra una vista previa y no guarda ni envía el mensaje.';
  dialogSubmit.innerHTML = isComplaint ? 'Enviar aviso <span>↗</span>' : 'Ver vista previa <span>↗</span>';
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

  if (document.querySelector('#dialog-tag').textContent === 'AVISOS Y QUEJAS') {
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

  const preview = [...values.entries()].filter(([key]) => key !== 'website').map(([key, value]) => `${key.replaceAll('-', ' ')}: ${value}`);
  formPreview.textContent = `Vista previa (no enviada): ${preview.join(' · ')}`;
});

dialog.addEventListener('click', (event) => {
  if (event.target === dialog) dialog.close();
});
