// Helper: parsea fecha YYYY-MM-DD sin conversión de timezone
function parseFecha(str) {
  const [y, m, d] = str.split('-').map(Number);
  return new Date(y, m - 1, d);
}

// =============================================
// ERAZO SYSTEM — paciente.js
// =============================================

/* ===== NAVEGACIÓN ===== */
function showView(key, btn) {
  document.querySelectorAll('.content-view').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
  const view = document.getElementById('view-' + key);
  if (view) view.classList.add('active');
  if (btn) btn.classList.add('active');
  window.scrollTo({ top: 0, behavior: 'smooth' });
  if (key === 'plan')   loadPlan();
  if (key === 'citas')  loadCitas();
  if (key === 'expediente') cargarExpediente();
}

/* ===== MODALES ===== */
function openModal(id) {
  document.getElementById(id).classList.add('show');
  if (id === 'modalNuevaCita') { renderMiniCal(); renderTimePicker(); }
}
function closeModal(id) { document.getElementById(id).classList.remove('show'); }
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.modal-overlay').forEach(m => {
    m.addEventListener('click', e => { if (e.target === m) closeModal(m.id); });
  });
  // Cargar inicio
  loadPlanResumen();
  loadProximaCita();
});

/* ===== PLAN ALIMENTICIO ===== */
function loadPlan() {
  fetch('/api/mi-plan')
    .then(r => r.json())
    .then(data => {
      const body = document.getElementById('planContent');
      const cajitaPlan = document.getElementById('statPlan'); // Buscamos la tarjeta de arriba

      if (!body) return;

      if (data.tiene_plan && data.pdf_url) {
        // Si hay plan, cambiamos el texto a "Activo"
        if (cajitaPlan) cajitaPlan.textContent = 'Activo';

        body.innerHTML = `
          <div class="pdf-container">
            <div class="pdf-toolbar">
              <span>${data.nombre_plan || 'Plan alimenticio'}</span>
              <a href="${data.pdf_url}" download class="dl-btn">
                <svg viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                Descargar PDF
              </a>
            </div>
            <iframe src="${data.pdf_url}" title="Mi plan alimenticio"></iframe>
          </div>`;
      } else {
        // Si no hay plan, aseguramos que diga "Sin plan"
        if (cajitaPlan) cajitaPlan.textContent = 'Sin plan';

        body.innerHTML = `
          <div class="no-plan-state">
            <svg viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            <p>Tu nutriólogo aún no ha subido tu plan alimenticio.<br>Está pendiente de asignación.</p>
          </div>`;
      }
    })
    .catch(() => {
      const body = document.getElementById('planContent');
      if (body) body.innerHTML = `<p style="color:var(--t-cla);padding:1.5rem;font-size:0.83rem;">No se pudo cargar el plan.</p>`;
    });
}

function loadPlanResumen() {
  fetch('/api/mi-plan')
    .then(r => r.json())
    .then(data => {
      const el = document.getElementById('quickPlanResumen');
      const cajitaPlan = document.getElementById('statPlan'); 
      
      if (!el) return;

      if (data.tiene_plan) {
        if (cajitaPlan) cajitaPlan.textContent = 'Activo'; // Actualiza desde el resumen

        el.innerHTML = `
          <div style="display:flex;align-items:center;gap:0.75rem;padding:0.6rem 0;border-bottom:1px solid #f2f0ea;">
            <div style="width:8px;height:8px;border-radius:50%;background:var(--teal)"></div>
            <span style="font-size:0.83rem;font-weight:500;">Plan activo</span>
            <a href="${data.pdf_url}" download style="margin-left:auto;font-size:0.75rem;color:var(--teal);font-weight:500;text-decoration:none;">Descargar PDF</a>
          </div>
          <p style="font-size:0.75rem;color:var(--t-cla);margin-top:0.75rem;">Revisa la pestaña "Mi Plan" para ver el detalle completo.</p>`;
      } else {
        if (cajitaPlan) cajitaPlan.textContent = 'Sin plan'; // Actualiza desde el resumen

        el.innerHTML = `<p style="font-size:0.82rem;color:var(--t-cla);">Tu nutriólogo aún no ha subido tu plan alimenticio.</p>`;
      }
    });
}

/* Cargar estado del plan desde que se entra a la pagina*/
document.addEventListener('DOMContentLoaded', () => {
    loadPlan();
    loadPlanResumen();
});

/* ===== CITAS ===== */
function loadCitas() {
  fetch('/api/mis-citas')
    .then(r => r.json())
    .then(citas => {
      const list = document.getElementById('citasList');
      if (!list) return;
      if (!citas.length) {
        list.innerHTML = `<div style="text-align:center;padding:2rem;color:var(--t-cla);font-size:0.83rem;">No tienes citas registradas</div>`;
        return;
      }
      list.innerHTML = citas.map(c => {
        const fecha  = parseFecha(c.fecha_cita);
        const dia    = fecha.getDate();
        const meses  = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];
        const mes    = meses[fecha.getMonth()];
        const puedeCanc = c.estado !== 'CANCELADA' && c.estado !== 'FINALIZADA';
        return `<div class="cita-card-p">
          <div class="cita-date-box"><div class="d">${dia}</div><div class="m">${mes}</div></div>
          <div class="cita-info">
            <h4>${c.motivo_consulta}</h4>
            <p>Con Lic. Edson Erazo Espinoza</p>
            <div class="hora-tag">🕐 ${c.hora_cita.slice(0,5)}</div>
            <div style="margin-top:0.45rem"><span class="badge badge-${c.estado.toLowerCase()}">${c.estado}</span></div>
            ${puedeCanc ? `<div class="cita-actions-btns">
              <button class="cit-btn red" onclick="solicitarCancelacion(${c.id_cita}, '${c.fecha_cita}')">Cancelar cita</button>
            </div>` : ''}
          </div>
        </div>`;
      }).join('');
    });
}

function loadProximaCita() {
  fetch('/api/mis-citas?proxima=true')
    .then(r => r.json())
    .then(data => {
      const el = document.getElementById('proximaCitaInfo');
      if (!el) return;
      if (data.cita) {
        const c = data.cita;
        const fecha = parseFecha(c.fecha_cita);
        const meses = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];
        el.innerHTML = `
          <div style="text-align:center;">
            <div style="background:var(--marino);width:56px;height:56px;border-radius:10px;display:flex;flex-direction:column;align-items:center;justify-content:center;margin:0 auto 0.65rem;">
              <span style="font-size:1.3rem;font-weight:500;color:#fff;line-height:1">${fecha.getDate()}</span>
              <span style="font-size:0.6rem;text-transform:uppercase;letter-spacing:0.05em;color:var(--lima)">${meses[fecha.getMonth()]}</span>
            </div>
            <p style="font-size:0.86rem;font-weight:500;margin-bottom:0.2rem">${c.hora_cita.slice(0,5)}</p>
            <p style="font-size:0.76rem;color:var(--t-cla);margin-bottom:0.65rem">${c.motivo_consulta}</p>
            <span class="badge badge-${c.estado.toLowerCase()}">${c.estado}</span>
            <div style="margin-top:0.8rem;">
              <button class="cit-btn red" onclick="solicitarCancelacion(${c.id_cita}, '${c.fecha_cita}')">Cancelar</button>
            </div>
          </div>`;
      } else {
        el.innerHTML = `<p style="font-size:0.82rem;color:var(--t-cla);text-align:center;">Sin citas próximas</p>
          <div style="margin-top:0.75rem;text-align:center;">
            <button class="cit-btn" onclick="openModal('modalNuevaCita')">Agendar cita</button>
          </div>`;
      }
    });
}

/* ===== AGENDAR CITA ===== */
let miniCalDate   = new Date();
let selectedDate  = null;
let selectedTime  = null;
const MESES_MINI  = ['Enero','Feb','Mar','Abril','Mayo','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];
const DIAS_MINI   = ['D','L','M','M','J','V','S'];

function changeMinCal(d) { miniCalDate.setMonth(miniCalDate.getMonth() + d); renderMiniCal(); }

function renderMiniCal() {
  const y = miniCalDate.getFullYear(), m = miniCalDate.getMonth();
  const el = document.getElementById('miniCalTitle');
  if (el) el.textContent = `${MESES_MINI[m]} ${y}`;
  const grid  = document.getElementById('miniCalGrid');
  if (!grid) return;
  const today    = new Date();
  const firstDay = new Date(y, m, 1).getDay();
  const daysInMo = new Date(y, m + 1, 0).getDate();
  const daysInPr = new Date(y, m, 0).getDate();
  let html = DIAS_MINI.map(d => `<div class="mc-name">${d}</div>`).join('');
  for (let i = firstDay - 1; i >= 0; i--) html += `<div class="mc-day other">${daysInPr - i}</div>`;
  for (let d = 1; d <= daysInMo; d++) {
    const date   = new Date(y, m, d);
    const isPast = date < new Date(today.getFullYear(), today.getMonth(), today.getDate());
    // Bloquear domingos (0) y sábados (6) opcionalmente
    const isTod  = date.getTime() === new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime();
    const dateStr = `${y}-${String(m+1).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
    const isSelec = selectedDate === dateStr;
    html += `<div class="mc-day ${isTod?'today':''} ${isPast?'unavail':''} ${isSelec?'selected':''}"
      ${!isPast ? `onclick="selectMiniDay('${dateStr}', this)"` : ''}>${d}</div>`;
  }
  grid.innerHTML = html;
}

function selectMiniDay(dateStr, el) {
  selectedDate = dateStr;
  document.querySelectorAll('.mc-day').forEach(d => d.classList.remove('selected'));
  el.classList.add('selected');
  renderTimePicker(dateStr);
}

function renderTimePicker(dateStr) {
  const tp = document.getElementById('timePicker');
  if (!tp) return;
  const horas = ['09:00','09:30','10:00','10:30','11:00','11:30','13:00','13:30','14:00','14:30','15:00','16:00','16:30','17:00','17:30'];

  if (!dateStr) {
    tp.innerHTML = horas.map(h => `<div class="time-slot-btn" onclick="selectTime('${h}', this)">${h}</div>`).join('');
    return;
  }

  fetch(`/api/citas/disponibilidad?fecha=${dateStr}`)
    .then(r => r.json())
    .then(data => {
      tp.innerHTML = horas.map(h => {
        const taken = data.ocupadas?.includes(h);
        return `<div class="time-slot-btn ${taken ? 'taken' : ''}"
          ${!taken ? `onclick="selectTime('${h}', this)"` : ''}>${h}</div>`;
      }).join('');
    })
    .catch(() => {
      tp.innerHTML = horas.map(h => `<div class="time-slot-btn" onclick="selectTime('${h}', this)">${h}</div>`).join('');
    });
}

function selectTime(h, el) {
  selectedTime = h;
  document.querySelectorAll('.time-slot-btn').forEach(b => b.classList.remove('selected'));
  el.classList.add('selected');
}

function guardarCita() {
  const motivo  = document.getElementById('citaMotivo').value.trim();
  const alertEl = document.getElementById('alertCitaPaciente');
  if (!selectedDate || !selectedTime || !motivo) {
    alertEl.className = 'inline-alert alert-warn'; alertEl.style.display = 'block';
    alertEl.textContent = 'Selecciona fecha, hora y motivo de consulta.';
    return;
  }
  fetch('/api/mis-citas', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fecha_cita: selectedDate, hora_cita: selectedTime, motivo_consulta: motivo })
  })
    .then(r => r.json())
    .then(data => {
      if (data.error) {
        alertEl.className = 'inline-alert alert-warn'; alertEl.style.display = 'block';
        alertEl.textContent = data.error;
      } else {
        closeModal('modalNuevaCita');
        selectedDate = null; selectedTime = null;
        loadCitas(); loadProximaCita();
        showToast('Cita registrada correctamente.');
      }
    })
    .catch(() => showToast('Error al registrar la cita', 'error'));
}

/* ===== CANCELAR CITA ===== */
function solicitarCancelacion(id, fecha) {
  const hoy = new Date();
  const fCita = parseFecha(fecha);
  const diff = (fCita - hoy) / (1000 * 60 * 60);
  document.getElementById('cancelCitaId').value = id;
  if (diff < 48) {
    document.getElementById('cancelWarning').style.display = 'block';
    document.getElementById('btnConfirmCancel').style.display = 'none';
  } else {
    document.getElementById('cancelWarning').style.display = 'none';
    document.getElementById('btnConfirmCancel').style.display = 'inline-flex';
  }
  openModal('modalCancelar');
}

function confirmarCancelacion() {
  const id = document.getElementById('cancelCitaId').value;
  fetch(`/api/mis-citas/${id}`, { method: 'DELETE' })
    .then(r => r.json())
    .then(data => {
      if (data.error) showToast(data.error, 'error');
      else { closeModal('modalCancelar'); loadCitas(); loadProximaCita(); showToast('Cita cancelada correctamente.'); }
    });
}

/* ===== TOAST ===== */
function showToast(msg, type = 'success') {
  const t = document.createElement('div');
  t.style.cssText = `position:fixed;bottom:1.5rem;right:1.5rem;background:${type === 'success' ? 'var(--marino)' : 'var(--rojo)'};color:#fff;padding:0.72rem 1.2rem;border-radius:10px;font-size:0.82rem;z-index:999;box-shadow:0 4px 20px rgba(0,0,0,0.15);max-width:320px;`;
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3200);
}

/* ========= Cargar plan desde paciente ========*/
document.addEventListener('DOMContentLoaded', () => {
    cargarExpediente();
});

function cargarExpediente() {
  fetch('/api/paciente/expediente')
    .then(r => r.json())
    .then(data => {
      const cont = document.getElementById('expedienteContent');

      if (data.error) {
        cont.innerHTML = `
          <div style="background: #fee2e2; border-left: 4px solid #dc2626; padding: 1rem; border-radius: 8px; color: #991b1b;">
            ⚠️ ${data.error}
          </div>
        `;
        return;
      }

      cont.innerHTML = `
        <style>
          .expediente-modern {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            max-width: 100%;
          }
          .metric-grid-modern {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
          }
          .metric-card {
            background: linear-gradient(135deg, #007576 0%, #2F4858 100%);
            border-radius: 20px;
            padding: 1.5rem 1rem;
            text-align: center;
            color: white;
            box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1);
            transition: transform 0.2s;
          }
          .metric-card:hover {
            transform: translateY(-3px);
          }
          .metric-value {
            font-size: 2rem;
            font-weight: 800;
            line-height: 1.2;
          }
          .metric-label {
            font-size: 0.85rem;
            opacity: 0.9;
            margin-top: 0.5rem;
            letter-spacing: 0.5px;
          }
          .section-title {
            font-size: 1.1rem;
            font-weight: 600;
            color: #1f2937;
            margin: 1.5rem 0 1rem 0;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid #e5e7eb;
          }
          .info-row {
            display: flex;
            background: #f9fafb;
            border-radius: 16px;
            margin-bottom: 0.75rem;
            overflow: hidden;
            transition: all 0.2s;
          }
          .info-label {
            width: 180px;
            background: #f3f4f6;
            padding: 1rem;
            font-weight: 600;
            color: #374151;
            font-size: 0.9rem;
            border-right: 1px solid #e5e7eb;
          }
          .info-content {
            flex: 1;
            padding: 1rem;
            color: #111827;
            background: white;
            word-break: break-word;
          }
          .empty-message {
            color: #9ca3af;
            font-style: italic;
          }
          @media (max-width: 640px) {
            .info-row {
              flex-direction: column;
            }
            .info-label {
              width: 100%;
              border-right: none;
              border-bottom: 1px solid #e5e7eb;
            }
            .metric-value {
              font-size: 1.5rem;
            }
          }
        </style>

        <div class="expediente-modern">
          <!-- Tarjetas de métricas principales -->
          <div class="metric-grid-modern">
            <div class="metric-card">
              <div class="metric-value">${parseFloat(data.peso).toFixed(1)} kg</div>
              <div class="metric-label">Peso actual</div>
            </div>
            <div class="metric-card">
              <div class="metric-value">${parseFloat(data.estatura).toFixed(2)} m</div>
              <div class="metric-label">Estatura</div>
            </div>
            <div class="metric-card">
              <div class="metric-value">${parseFloat(data.imc).toFixed(1)}</div>
              <div class="metric-label">Índice de Masa Corporal</div>
            </div>
          </div>

          <!-- Información detallada -->
          <div class="section-title">📋 Información clínica</div>
          
          ${renderField('🎯 Objetivo Nutricional', data.objetivo_nutricional)}
          ${renderField('🩺 Diagnóstico Inicial', data.diagnostico_inicial)}
          ${renderField('📝 Observaciones Médicas', data.observaciones_medicas)}
          ${renderField('📚 Historial Clínico', data.historial_clinico)}
          ${renderField('✨ Nuevas Observaciones', data.nuevas_observaciones || 'Sin observaciones')}
        </div>
      `;
    });
}

// Función auxiliar para renderizar cada campo
function renderField(label, content) {
  const hasContent = content && content.trim() !== '' && content !== 'Sin observaciones';
  return `
    <div class="info-row">
      <div class="info-label">${label}</div>
      <div class="info-content ${!hasContent ? 'empty-message' : ''}">
        ${hasContent ? content.replace(/\n/g, '<br>') : '— Sin información registrada —'}
      </div>
    </div>
  `;
}
