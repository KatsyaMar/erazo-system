// =============================================
// ERAZO SYSTEM — index.js
// =============================================

document.addEventListener('DOMContentLoaded', () => {
  // Enter key para submit
  document.addEventListener('keydown', e => {
    if (e.key !== 'Enter') return;
    const rec = document.getElementById('recoveryForm');
    if (rec && rec.style.display === 'block') handleRecovery();
    else handleLogin();
  });
});

/* ===== HELPERS ===== */
function showAlert(id, msg) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = msg;
  el.style.display = 'block';
}
function hideAlerts() {
  ['errorAlert', 'successAlert', 'recErrorAlert', 'recSuccessAlert'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = 'none';
  });
}

/* ===== LOGIN ===== */
function handleLogin() {
  hideAlerts();
  const email    = document.getElementById('email').value.trim();
  const password = document.getElementById('password').value;
  const emailRx  = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  if (!email || !password) {
    showAlert('errorAlert', 'Por favor, llene todos los campos.');
    return;
  }
  if (!emailRx.test(email)) {
    showAlert('errorAlert', 'El formato del correo electrónico no es válido.');
    return;
  }

  // El form se envía por Flask (POST /login). Este JS solo valida client-side.
  document.getElementById('loginFormEl').submit();
}

/* ===== RECUPERACIÓN ===== */
function handleRecovery() {
  hideAlerts();
  const email = document.getElementById('recEmail').value.trim();
  const emailRx = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!email) {
    showAlert('recErrorAlert', 'El correo electrónico es obligatorio.');
    return;
  }
  if (!emailRx.test(email)) {
    showAlert('recErrorAlert', 'El formato del correo electrónico no es válido.');
    return;
  }
  document.getElementById('recoveryFormEl').submit();
}

/* ===== TOGGLE FORMULARIOS ===== */
function toggleRecovery() {
  /*hideAlerts();
  const login    = document.getElementById('loginForm');
  const recovery = document.getElementById('recoveryForm');
  const showLogin = recovery.style.display === 'block';
  login.style.display    = showLogin ? 'block' : 'none';
  recovery.style.display = showLogin ? 'none'  : 'block';
  */
  hideAlerts();
  const login = document.getElementById('loginForm');
  const recovery = document.getElementById('recoveryForm');

  const isVisible = window.getComputedStyle(recovery).display !== 'none';

  if (isVisible) {
    recovery.style.display = 'none';
    login.style.display = 'block';
  } else {
    recovery.style.display = 'block';
    login.style.display = 'none';
  }
}
