/* ════════════════════════════════
   index.js  —  Login logic
   ════════════════════════════════ */

function doLogin() {
  const u = document.getElementById('inp-user').value.trim();
  const p = document.getElementById('inp-pass').value.trim();
  const err = document.getElementById('err');
  if (!u || !p) { err.textContent='Por favor completa todos los campos.'; err.classList.add('show'); return; }
  err.classList.remove('show');

  // Nutriólogo (único)
  if ((u==='erazo@correo.com'||u==='5500000001') && p==='Erazo2026!') {
    window.location.href='../templates/nutriologo.html'; return;
  }

  // Buscar paciente por email o teléfono + contraseña
  const pac = DB.patients.find(pt => (pt.email===u || pt.telefono===u) && pt.pass===p);
  if (pac) { window.location.href='../templates/paciente.html'; return; }

  err.textContent='Credenciales incorrectas.';
  err.classList.add('show');
}

document.addEventListener('DOMContentLoaded', () => {
  Settings.load();
  document.addEventListener('keydown', e => { if(e.key==='Enter') doLogin(); });
});
