const config = window.BARRIO_CONFIG || {};
const configured = Boolean(config.supabaseUrl && config.supabaseAnonKey && window.supabase?.createClient);
const client = configured ? window.supabase.createClient(config.supabaseUrl, config.supabaseAnonKey) : null;
const status = document.querySelector('#recovery-status');
const form = document.querySelector('#new-password-form');
const passwordMessage = document.querySelector('#password-message');
const backToLogin = document.querySelector('#back-to-login');

function showError(message) {
  status.textContent = message;
  backToLogin.hidden = false;
}

if (!client) {
  showError('No se pudo conectar con Supabase. Volvé al acceso e intentá más tarde.');
} else {
  const hashParams = new URLSearchParams(window.location.hash.slice(1));
  const linkError = hashParams.get('error_description');
  if (linkError) {
    showError('El enlace no es válido o ya venció. Volvé al acceso y solicitá uno nuevo.');
  }

  client.auth.onAuthStateChange((event) => {
    if (event === 'PASSWORD_RECOVERY') {
      window.history.replaceState(null, document.title, `${window.location.pathname}${window.location.search}`);
      status.textContent = 'El enlace está verificado. Elegí una contraseña nueva.';
      form.hidden = false;
      backToLogin.hidden = true;
    }
  });
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const values = new FormData(form);
  const password = values.get('password');
  if (password !== values.get('password-confirmation')) {
    passwordMessage.textContent = 'Las contraseñas no coinciden.';
    return;
  }

  const button = form.querySelector('button[type="submit"]');
  button.disabled = true;
  passwordMessage.textContent = 'Guardando…';
  const { error } = await client.auth.updateUser({ password });
  button.disabled = false;
  if (error) {
    passwordMessage.textContent = 'No se pudo guardar la contraseña. Revisá que cumpla los requisitos e intentá de nuevo.';
    return;
  }

  await client.auth.signOut();
  form.hidden = true;
  status.textContent = 'La contraseña se cambió correctamente. Ya podés iniciar sesión.';
  backToLogin.hidden = false;
});
