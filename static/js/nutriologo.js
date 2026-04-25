// =============================================
// ERAZO SYSTEM — nutriologo.js
// =============================================

/* ===== NAVEGACIÓN SIDEBAR ===== */
const SECTION_META = {
  pacientes:     { title: 'Gestión de Pacientes',        desc: 'Administra los pacientes registrados en el sistema' },
  expedientes:   { title: 'Gestión de Expedientes',      desc: 'Crea y gestiona expedientes clínicos digitales' },
  planes:        { title: 'Planes Alimenticios',          desc: 'Sube y gestiona planes alimenticios en PDF' },
  citas:         { title: 'Gestión de Citas',             desc: 'Administra la agenda de citas y consultas' },
  configuracion: { title: 'Configuración',                desc: 'Ajusta las preferencias del sistema' },
};

function showSection(key) {
  document.querySelectorAll('.content-section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  const sec = document.getElementById('sec-' + key);
  if (sec) sec.classList.add('active');
  const meta = SECTION_META[key];
  if (meta) {
    document.getElementById('sectionTitle').textContent = meta.title;
    document.getElementById('sectionDesc').textContent  = meta.desc;
  }
  if (event && event.currentTarget) event.currentTarget.classList.add('active');
  if (key === 'citas') renderCalendar();
  if (key === 'expedientes') loadExpedientesList();
  if (key === 'planes') loadPlanesList();
}

/* ===== MODALES ===== */
function openModal(id) {
  document.getElementById(id).classList.add('show');
}

function closeModal(id) {
  document.getElementById(id).classList.remove('show');
  document.querySelectorAll(`#${id} .inline-alert`).forEach(a => {
    a.className = 'inline-alert';
    a.textContent = '';
  });
  const imc = document.getElementById('imcDisplay');
  if (imc) imc.textContent = '—';
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.modal-overlay').forEach(m => {
    m.addEventListener('click', e => { if (e.target === m) closeModal(m.id); });
  });
  renderPatients();
});

/* ===== IMC ===== */
function calcIMC() {
  const peso = parseFloat(document.getElementById('pPeso')?.value);
  const est  = parseFloat(document.getElementById('pEstatura')?.value);
  const el   = document.getElementById('imcDisplay');
  if (!el) return;
  if (peso > 0 && est > 0) {
    const v = (peso / (est * est)).toFixed(1);
    const cat = v < 18.5 ? 'Bajo peso' : v < 25 ? 'Normal' : v < 30 ? 'Sobrepeso' : 'Obesidad';
    el.textContent = `${v} – ${cat}`;
  } else {
    el.textContent = '—';
  }
}

/* ===== PACIENTES — Filtros ===== */
let filtroEstado = 'activo';
let filtroTexto  = '';

function filterByStatus(status, btn) {
  filtroEstado = status;
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  renderPatients();
}
function filterPatients(val) {
  filtroTexto = val.toLowerCase();
  renderPatients();
}

/* ===== RENDER PACIENTES (fetch desde Flask) ===== */
function renderPatients() {
  fetch(`/api/pacientes?estado=${filtroEstado}&q=${encodeURIComponent(filtroTexto)}`)
    .then(r => r.json())
    .then(data => {
      const tbody = document.getElementById('tbodyPacientes');
      if (!tbody) return;
      if (!data.length) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:2rem;color:var(--t-cla);">No se encontraron pacientes</td></tr>`;
        return;
      }
      tbody.innerHTML = data.map(p => {
        const activo   = p.estado === 'ACTIVO';
        const initials = p.nombre_completo.split(' ').slice(0,2).map(x => x[0]).join('').toUpperCase();
        const acciones = activo
          ? `<button class="act-btn teal" onclick="consultarPaciente(${p.id_usuario})">Consultar</button>
             <button class="act-btn"     onclick="modificarPaciente(${p.id_usuario})">Modificar</button>
             <button class="act-btn red" onclick="darBajaPaciente(${p.id_usuario}, '${p.nombre_completo}')">Dar de baja</button>`
          : `<button class="act-btn teal"  onclick="consultarPaciente(${p.id_usuario})">Consultar</button>
             <button class="act-btn green" onclick="darAltaPaciente(${p.id_usuario}, '${p.nombre_completo}')">Dar de alta</button>`;
        return `<tr>
          <td><div class="patient-name">
            <div class="p-avatar">${initials}</div>
            <div><div style="font-weight:500">${p.nombre_completo}</div>
            <div style="font-size:0.7rem;color:var(--t-cla)">Edad: ${p.edad} años</div></div>
          </div></td>
          <td>${p.telefono}</td>
          <td style="font-size:0.8rem;color:var(--t-cla)">${p.correo}</td>
          <td><span style="font-weight:500;color:var(--teal)">${parseFloat(p.imc).toFixed(1)}</span></td>
          <td><span class="badge badge-${p.estado.toLowerCase()}">${p.estado}</span></td>
          <td><div class="actions-cell">${acciones}</div></td>
        </tr>`;
      }).join('');
    })
    .catch(() => {
      const tbody = document.getElementById('tbodyPacientes');
      if (tbody) tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:2rem;color:var(--t-cla);">Error al cargar pacientes</td></tr>`;
    });
}

/* ===== CONSULTAR PACIENTE ===== */
function consultarPaciente(id) {
  fetch(`/api/pacientes/${id}`)
    .then(r => r.json())
    .then(p => {
      document.getElementById('modalConsultarNombre').textContent = p.nombre_completo;
      document.getElementById('dTel').textContent      = p.telefono;
      document.getElementById('dCorreo').textContent   = p.correo;
      document.getElementById('dEdad').textContent     = `${p.edad} años`;
      document.getElementById('dPeso').textContent     = `${p.peso} kg`;
      document.getElementById('dEstat').textContent    = `${p.estatura} m`;
      document.getElementById('dIMC').textContent      = `${parseFloat(p.imc).toFixed(1)}`;
      document.getElementById('dEstado').innerHTML     = `<span class="badge badge-${p.estado.toLowerCase()}">${p.estado}</span>`;
      document.getElementById('dFechaReg').textContent = p.fecha_registro || '—';
      openModal('modalConsultarPaciente');
    })
    .catch(() => showToast('Error al obtener datos del paciente', 'error'));
}

/* ===== MODIFICAR PACIENTE — cargar datos ===== */
function modificarPaciente(id) {
  fetch(`/api/pacientes/${id}`)
    .then(r => r.json())
    .then(p => {
      document.getElementById('mPacienteId').value    = p.id_usuario;
      document.getElementById('mNombre').value        = p.nombre_completo;
      document.getElementById('mCorreo').value        = p.correo;
      document.getElementById('mEdad').value          = p.edad;
      document.getElementById('mPeso').value          = p.peso;
      document.getElementById('mEstatura').value      = p.estatura;
      calcIMCModificar();
      openModal('modalModificarPaciente');
    })
    .catch(() => showToast('Error al obtener datos del paciente', 'error'));
}

function calcIMCModificar() {
  const peso = parseFloat(document.getElementById('mPeso')?.value);
  const est  = parseFloat(document.getElementById('mEstatura')?.value);
  const el   = document.getElementById('mImcDisplay');
  if (!el) return;
  if (peso > 0 && est > 0) {
    const v = (peso / (est * est)).toFixed(1);
    const cat = v < 18.5 ? 'Bajo peso' : v < 25 ? 'Normal' : v < 30 ? 'Sobrepeso' : 'Obesidad';
    el.textContent = `${v} – ${cat}`;
  } else {
    el.textContent = '—';
  }
}

/* ===== DAR DE BAJA ===== */
function darBajaPaciente(id, nombre) {
  document.getElementById('bajaPacienteId').value    = id;
  document.getElementById('bajaPacienteNombre').textContent = nombre;
  openModal('modalDarBaja');
}

function confirmarBaja() {
  const id = document.getElementById('bajaPacienteId').value;
  fetch(`/api/pacientes/${id}/baja`, { method: 'POST', headers: { 'Content-Type': 'application/json' } })
    .then(r => r.json())
    .then(data => {
      closeModal('modalDarBaja');
      showToast(data.message || 'Paciente dado de baja correctamente');
      renderPatients();
    })
    .catch(() => showToast('Error al dar de baja al paciente', 'error'));
}

/* ===== DAR DE ALTA ===== */
function darAltaPaciente(id, nombre) {
  if (!confirm(`¿Dar de alta a ${nombre}?`)) return;
  fetch(`/api/pacientes/${id}/alta`, { method: 'POST', headers: { 'Content-Type': 'application/json' } })
    .then(r => r.json())
    .then(data => {
      showToast(data.message || 'Paciente dado de alta correctamente');
      renderPatients();
    })
    .catch(() => showToast('Error al dar de alta al paciente', 'error'));
}

/* ===== GUARDAR NUEVO PACIENTE ===== */
function guardarPaciente() {
  const nombre   = document.getElementById('pNombre').value.trim();
  const tel      = document.getElementById('pTel').value.trim();
  const correo   = document.getElementById('pCorreo').value.trim();
  const pass     = document.getElementById('pPass').value;
  const edad     = document.getElementById('pEdad').value;
  const peso     = document.getElementById('pPeso').value;
  const estatura = document.getElementById('pEstatura').value;
  const alertEl  = document.getElementById('alertPaciente');

  if (!nombre || !tel || !correo || !pass || !edad || !peso || !estatura) {
    alertEl.className = 'inline-alert error show';
    alertEl.textContent = 'Datos incompletos, favor de llenar todos los campos.';
    return;
  }

  fetch('/api/pacientes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nombre_completo: nombre, telefono: tel, correo, contrasena: pass, edad: parseInt(edad), peso: parseFloat(peso), estatura: parseFloat(estatura) })
  })
    .then(r => r.json())
    .then(data => {
      if (data.error) {
        alertEl.className = 'inline-alert error show';
        alertEl.textContent = data.error;
      } else {
        closeModal('modalNuevoPaciente');
        renderPatients();
        showToast('Paciente registrado correctamente');
      }
    })
    .catch(() => {
      alertEl.className = 'inline-alert error show';
      alertEl.textContent = 'Error al registrar el paciente.';
    });
}

/* ===== GUARDAR MODIFICACIÓN PACIENTE ===== */
function guardarModificacion() {
  const id       = document.getElementById('mPacienteId').value;
  const nombre   = document.getElementById('mNombre').value.trim();
  const correo   = document.getElementById('mCorreo').value.trim();
  const edad     = document.getElementById('mEdad').value;
  const peso     = document.getElementById('mPeso').value;
  const estatura = document.getElementById('mEstatura').value;
  const alertEl  = document.getElementById('alertModificar');

  if (!nombre || !correo) {
    alertEl.className = 'inline-alert error show';
    alertEl.textContent = 'El nombre y correo son obligatorios.';
    return;
  }

  fetch(`/api/pacientes/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nombre_completo: nombre, correo, edad: parseInt(edad), peso: parseFloat(peso), estatura: parseFloat(estatura) })
  })
    .then(r => r.json())
    .then(data => {
      if (data.error) {
        alertEl.className = 'inline-alert error show';
        alertEl.textContent = data.error;
      } else {
        closeModal('modalModificarPaciente');
        renderPatients();
        showToast('Paciente actualizado correctamente');
      }
    })
    .catch(() => {
      alertEl.className = 'inline-alert error show';
      alertEl.textContent = 'Error al modificar el paciente.';
    });
}

setTimeout(() => {
  document.querySelectorAll('.flash-messages li').forEach(el => {
    el.style.transition = 'opacity 0.4s ease';
    
    setTimeout(() => {
      el.style.opacity = '0';
      setTimeout(() => el.remove(), 400);
    }, 3000);
  });
}, 200);


/* ===== EXPEDIENTES ===== */
function loadExpedientesList() {
  fetch('/api/pacientes?estado=activo&con_expediente=true')
    .then(r => r.json())
    .then(data => {
      const list = document.getElementById('expPacientesList');
      if (!list) return;
      if (!data.length) {
        list.innerHTML = `<div class="empty-state"><svg viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/></svg><p>Sin expedientes</p></div>`;
        return;
      }
      list.innerHTML = data.map(p => {
        const ini = p.nombre_completo.split(' ').slice(0,2).map(x=>x[0]).join('').toUpperCase();
        return `<div class="patient-list-item" onclick="showExpDetail(${p.id_usuario}, this)">
          <div class="p-avatar">${ini}</div>
          <div style="flex:1"><div style="font-size:0.83rem;font-weight:500">${p.nombre_completo}</div>
          <div style="font-size:0.7rem;color:var(--t-cla)">${p.telefono}</div></div>
          <button class="act-btn" onclick="event.stopPropagation();modificarExpediente(${p.id_usuario})">Modificar</button>
        </div>`;
      }).join('');
    });
}

function showExpDetail(idUsuario, el) {
  document.querySelectorAll('.patient-list-item').forEach(x => x.classList.remove('selected'));
  el.classList.add('selected');
  fetch(`/api/expedientes/${idUsuario}`)
    .then(r => r.json())
    .then(exp => {
      document.getElementById('expDetailTitle').textContent = `Expediente – ${exp.nombre_completo}`;
      document.getElementById('expDetailBody').innerHTML = `
        <div class="metric-grid">
          <div class="metric-box"><div class="val">${exp.peso}kg</div><div class="lbl">Peso</div></div>
          <div class="metric-box"><div class="val">${exp.estatura}m</div><div class="lbl">Estatura</div></div>
          <div class="metric-box"><div class="val">${parseFloat(exp.imc).toFixed(1)}</div><div class="lbl">IMC</div></div>
        </div>
        <div class="exp-field"><label>Objetivo Nutricional</label><p>${exp.objetivo_nutricional}</p></div>
        <div class="exp-field"><label>Diagnóstico Inicial</label><p>${exp.diagnostico_inicial}</p></div>
        <div class="exp-field"><label>Observaciones Médicas</label><p>${exp.observaciones_medicas}</p></div>
        <div class="exp-field"><label>Historial Clínico</label><p>${exp.historial_clinico}</p></div>
        ${exp.nuevas_observaciones ? `<div class="exp-field"><label>Nuevas Observaciones</label><p>${exp.nuevas_observaciones}</p></div>` : ''}
        <div style="display:flex;gap:0.5rem;margin-top:1rem;">
          <button class="btn-primary" style="font-size:0.78rem" onclick="modificarExpediente(${idUsuario})">Modificar</button>
          <button class="btn-danger" onclick="eliminarExpediente(${exp.id_expediente})">Eliminar</button>
        </div>`;
    })
    .catch(() => showToast('Error al cargar expediente', 'error'));
}

function guardarExpediente() {
  const alertEl = document.getElementById('alertExp');
  const tel     = document.getElementById('expTelefono').value.trim();
  const obj     = document.getElementById('expObjetivo').value.trim();
  const diag    = document.getElementById('expDiag').value.trim();
  const obs     = document.getElementById('expObs').value.trim();
  const hist    = document.getElementById('expHistorial').value.trim();
  if (!tel || !obj || !diag || !obs || !hist) {
    alertEl.className = 'inline-alert error show';
    alertEl.textContent = 'Todos los datos son obligatorios, favor de rellenarlos.';
    return;
  }
  fetch('/api/expedientes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ telefono: tel, objetivo_nutricional: obj, diagnostico_inicial: diag, observaciones_medicas: obs, historial_clinico: hist })
  })
    .then(r => r.json())
    .then(data => {
      if (data.error) { alertEl.className = 'inline-alert error show'; alertEl.textContent = data.error; }
      else { closeModal('modalAsignarExp'); loadExpedientesList(); showToast('Expediente creado correctamente'); }
    });
}

function modificarExpediente(idUsuario) {
  document.getElementById('modExpUsuarioId').value = idUsuario;
  openModal('modalModificarExp');
}
function guardarModificacionExp() {
  const idU  = document.getElementById('modExpUsuarioId').value;
  const obs  = document.getElementById('modExpObs').value.trim();
  const peso = document.getElementById('modExpPeso').value;
  const est  = document.getElementById('modExpEstatura').value;
  const obj  = document.getElementById('modExpObjetivo').value.trim();
  if (!obs && !peso && !est && !obj) {
    const al = document.getElementById('alertModExp');
    al.className = 'inline-alert error show'; al.textContent = 'Ingresa al menos un campo a modificar.';
    return;
  }
  fetch(`/api/expedientes/${idU}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nuevas_observaciones: obs, peso: peso ? parseFloat(peso) : null, estatura: est ? parseFloat(est) : null, objetivo_nutricional: obj || null })
  })
    .then(r => r.json())
    .then(data => {
      if (data.error) { const al = document.getElementById('alertModExp'); al.className='inline-alert error show'; al.textContent=data.error; }
      else { closeModal('modalModificarExp'); loadExpedientesList(); showToast('Expediente actualizado correctamente'); }
    });
}
function eliminarExpediente(idExp) {
  if (!confirm('¿Eliminar este expediente? Esta acción no se puede deshacer.')) return;
  fetch(`/api/expedientes/${idExp}`, { method: 'DELETE' })
    .then(r => r.json())
    .then(data => {
      if (data.error) showToast(data.error, 'error');
      else { loadExpedientesList(); document.getElementById('expDetailTitle').textContent = 'Selecciona un paciente'; document.getElementById('expDetailBody').innerHTML = '<div class="empty-state"><p>Selecciona un paciente para ver su expediente</p></div>'; showToast('Expediente eliminado correctamente'); }
    });
}

/* ===== PLANES PDF ===== */
function loadPlanesList() {
  fetch('/api/pacientes?estado=activo&con_expediente=true')
    .then(r => r.json())
    .then(data => {
      const list = document.getElementById('planPacientesList');
      if (!list) return;
      list.innerHTML = data.map(p => {
        const ini = p.nombre_completo.split(' ').slice(0,2).map(x=>x[0]).join('').toUpperCase();
        return `<div class="patient-list-item" onclick="selectPlanPaciente(${p.id_usuario}, '${p.nombre_completo}', this)">
          <div class="p-avatar">${ini}</div>
          <div style="flex:1"><div style="font-size:0.83rem;font-weight:500">${p.nombre_completo}</div>
          <div style="font-size:0.7rem;color:var(--t-cla)">${p.telefono}</div></div>
        </div>`;
      }).join('');
    });
}

let selectedPlanUserId = null;
function selectPlanPaciente(id, nombre, el) {
  selectedPlanUserId = id;
  document.querySelectorAll('.patient-list-item').forEach(x => x.classList.remove('selected'));
  el.classList.add('selected');
  document.getElementById('planPacienteNombre').textContent = nombre;
  fetch(`/api/planes/${id}`)
    .then(r => r.json())
    .then(plan => {
      const panel = document.getElementById('planViewPanel');
      if (plan.tiene_plan && plan.pdf_url) {
        panel.innerHTML = `
          <div class="pdf-viewer-panel">
            <div class="pdf-bar">
              <span class="pdf-name">Plan de ${nombre}</span>
              <div class="pdf-actions">
                <a href="${plan.pdf_url}" download class="pdf-btn">Descargar</a>
                <button class="pdf-btn" onclick="triggerPlanUpload()">Reemplazar PDF</button>
              </div>
            </div>
            <iframe src="${plan.pdf_url}" title="Plan alimenticio"></iframe>
          </div>`;
      } else {
        panel.innerHTML = `
          <div class="pdf-drop-zone" id="dropZone" onclick="triggerPlanUpload()" ondragover="handleDragOver(event)" ondragleave="handleDragLeave(event)" ondrop="handleDrop(event)">
            <svg viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="15" y2="15"/></svg>
            <p>Arrastra el PDF aquí o <span>selecciona el archivo</span></p>
            <p style="font-size:0.72rem;margin-top:0.5rem;">Solo archivos .pdf</p>
          </div>
          <input type="file" id="planPdfInput" accept=".pdf" style="display:none" onchange="uploadPlanPDF(this.files[0])">`;
      }
    })
    .catch(() => {
      document.getElementById('planViewPanel').innerHTML = `<div style="padding:1.5rem;color:var(--t-cla);font-size:0.83rem;">No se pudo cargar el plan.</div>`;
    });
}

function triggerPlanUpload() {
  document.getElementById('planPdfInput').click();
}
function handleDragOver(e)  { e.preventDefault(); document.getElementById('dropZone')?.classList.add('dragover'); }
function handleDragLeave(e) { document.getElementById('dropZone')?.classList.remove('dragover'); }
function handleDrop(e) {
  e.preventDefault();
  document.getElementById('dropZone')?.classList.remove('dragover');
  const file = e.dataTransfer.files[0];
  if (file && file.type === 'application/pdf') uploadPlanPDF(file);
  else showToast('Solo se permiten archivos PDF', 'error');
}
function uploadPlanPDF(file) {
  if (!selectedPlanUserId) return;
  if (!file || file.type !== 'application/pdf') { showToast('Solo se permiten archivos PDF', 'error'); return; }
  const form = new FormData();
  form.append('pdf', file);
  form.append('id_usuario', selectedPlanUserId);
  fetch('/api/planes/upload', { method: 'POST', body: form })
    .then(r => r.json())
    .then(data => {
      if (data.error) showToast(data.error, 'error');
      else { showToast('Plan alimenticio subido correctamente'); selectPlanPaciente(selectedPlanUserId, document.getElementById('planPacienteNombre').textContent, document.querySelector('.patient-list-item.selected')); }
    })
    .catch(() => showToast('Error al subir el plan', 'error'));
}

/* ===== CITAS — CALENDARIO ===== */
let calDate = new Date();
const MESES = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];
const DIAS  = ['Dom','Lun','Mar','Mié','Jue','Vie','Sáb'];

function changeMonth(d) { calDate.setMonth(calDate.getMonth() + d); renderCalendar(); }

function renderCalendar() {
  const y = calDate.getFullYear(), m = calDate.getMonth();
  document.getElementById('calMonthYear').textContent = `${MESES[m]} ${y}`;
  const today     = new Date();
  const firstDay  = new Date(y, m, 1).getDay();
  const daysInMo  = new Date(y, m + 1, 0).getDate();
  const daysInPre = new Date(y, m, 0).getDate();
  let html = DIAS.map(d => `<div class="cal-day-name">${d}</div>`).join('');
  for (let i = firstDay - 1; i >= 0; i--) html += `<div class="cal-day other-month">${daysInPre - i}</div>`;
  for (let d = 1; d <= daysInMo; d++) {
    const isToday = d === today.getDate() && m === today.getMonth() && y === today.getFullYear();
    html += `<div class="cal-day ${isToday ? 'today' : ''}" id="calDay${d}" onclick="selectDay(${d})">${d}</div>`;
  }
  let remaining = 42 - firstDay - daysInMo;
  if (remaining < 0) remaining += 7;
  for (let d = 1; d <= remaining; d++) html += `<div class="cal-day other-month">${d}</div>`;
  document.getElementById('calGrid').innerHTML = html;

  // Cargar citas del mes
  fetch(`/api/citas/mes?year=${y}&month=${m + 1}`)
    .then(r => r.json())
    .then(data => {
      data.forEach(item => {
        const el = document.getElementById(`calDay${item.dia}`);
        if (el) { el.classList.add('has-cita'); if (item.lleno) el.classList.add('full'); }
      });
    })
    .catch(() => {});

  // Mostrar agenda del día actual o del 1ero
  const dayToShow = (m === today.getMonth() && y === today.getFullYear()) ? today.getDate() : 1;
  renderAgenda(dayToShow, y, m);
}

function selectDay(d) {
  document.querySelectorAll('.cal-day').forEach(el => el.classList.remove('selected'));
  const el = document.getElementById(`calDay${d}`);
  if (el) el.classList.add('selected');
  renderAgenda(d, calDate.getFullYear(), calDate.getMonth());
}

function renderAgenda(day, y, m) {
  document.getElementById('agendaDayTitle').textContent = `Agenda – ${day} ${MESES[m]}`;
  const slots   = document.getElementById('agendaSlots');
  const horas   = ['09:00','09:30','10:00','10:30','11:00','11:30','12:00','12:30','13:00','13:30','14:00','14:30','15:00','15:30','16:00','16:30','17:00','17:30'];
  const fechaStr = `${y}-${String(m+1).padStart(2,'0')}-${String(day).padStart(2,'0')}`;

  fetch(`/api/citas/dia?fecha=${fechaStr}`)
    .then(r => r.json())
    .then(citas => {
      slots.innerHTML = horas.map(h => {
        const cita = citas.find(c => c.hora_cita.slice(0,5) === h);
        if (cita) {
          return `<div class="time-slot-row">
            <div class="time-label">${h}</div>
            <div style="flex:1">
              <div class="cita-card ${cita.estado.toLowerCase()}">
                <div class="cita-name">${cita.nombre_completo}</div>
                <div class="cita-motivo">${cita.motivo_consulta}</div>
                <div class="cita-actions">
                  <button class="act-btn red" onclick="cancelarCita(${cita.id_cita}, '${cita.nombre_completo}')">Cancelar</button>
                </div>
              </div>
            </div>
          </div>`;
        }
        return `<div class="time-slot-row"><div class="time-label">${h}</div><div style="flex:1"><div class="slot-empty"></div></div></div>`;
      }).join('');
    })
    .catch(() => { if (slots) slots.innerHTML = ''; });
}

/* ===== GUARDAR CITA (nutriólogo) ===== */
function guardarCita() {
  const tel    = document.getElementById('citaTel').value.trim();
  const fecha  = document.getElementById('citaFecha').value;
  const hora   = document.getElementById('citaHora').value;
  const motivo = document.getElementById('citaMotivo').value.trim();
  const alertEl = document.getElementById('alertCita');
  if (!tel || !fecha || !hora || !motivo) {
    alertEl.className = 'inline-alert error show'; alertEl.textContent = 'Todos los campos obligatorios deben completarse.'; return;
  }
  fetch('/api/citas', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ telefono: tel, fecha_cita: fecha, hora_cita: hora, motivo_consulta: motivo })
  })
    .then(r => r.json())
    .then(data => {
      if (data.error) { alertEl.className = 'inline-alert error show'; alertEl.textContent = data.error; }
      else { closeModal('modalNuevaCita'); renderCalendar(); showToast('Cita registrada correctamente'); }
    });
}

function cancelarCita(id, nombre) {
  if (!confirm(`¿Cancelar la cita de ${nombre}?`)) return;
  fetch(`/api/citas/${id}`, { method: 'DELETE' })
    .then(r => r.json())
    .then(data => {
      if (data.error) showToast(data.error, 'error');
      else { renderCalendar(); showToast('Cita cancelada correctamente'); }
    });
}

/* ===== TOAST ===== */
function showToast(msg, type = 'success') {
  const t = document.createElement('div');
  t.style.cssText = `position:fixed;bottom:1.5rem;right:1.5rem;background:${type === 'success' ? 'var(--marino)' : 'var(--rojo)'};color:#fff;padding:0.75rem 1.25rem;border-radius:10px;font-size:0.83rem;z-index:999;box-shadow:0 4px 20px rgba(0,0,0,0.15);max-width:320px;animation:fadeIn 0.2s ease;`;
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3200);
}
