/* ════════════════════════════════
   nutriologo.js
   ════════════════════════════════ */

/* ══ NAV ══ */
const PAGES = ['pacientes','expedientes','planes','citas'];
const META  = {
  pacientes:   { t:'Gestión de Pacientes',  s:'Registra, modifica y gestiona pacientes' },
  expedientes: { t:'Expedientes Clínicos',   s:'Crea y gestiona expedientes médicos' },
  planes:      { t:'Planes Alimenticios',    s:'Asigna planes a pacientes con expediente' },
  citas:       { t:'Agendar Citas',          s:'Administra el calendario de consultas' },
};
function showPage(name, el) {
  PAGES.forEach(p => q('pg-'+p).classList.toggle('hidden', p!==name));
  document.querySelectorAll('.nav-item').forEach(n=>n.classList.remove('active'));
  if(el) el.classList.add('active');
  q('tb-title').textContent = META[name].t;
  q('tb-sub').textContent   = META[name].s;
  if(name==='pacientes')   renderPac();
  if(name==='expedientes') { renderExp(); renderNoExp(); }
  if(name==='planes')      renderPlanes();
  if(name==='citas')       { renderCalendar(); showCitasList(); }
}

/* ══ PACIENTES ══ */
function renderPac() {
  const list=filterList(q('s-pac').value||'', DB.patients, p=>p.nombre);
  const el=q('list-pac');
  el.innerHTML=list.length ? list.map(p=>`
    <div class="patient-card">
      <div class="p-avatar">${initials(p.nombre)}</div>
      <div class="p-info"><h4>${p.nombre}</h4><p>${p.edad} años · ${p.peso}kg · ${p.estatura}m · ${p.telefono}</p></div>
      <div class="p-actions">
        <button class="btn btn-warning btn-sm" onclick="openEditPac(${p.id})">✏ Modificar</button>
        <button class="btn btn-danger  btn-sm" onclick="openDelPac(${p.id})">🗑 Eliminar</button>
      </div>
    </div>`).join('')
  : '<p style="padding:20px;color:var(--text-soft);font-size:.88rem">No se encontraron pacientes.</p>';
}
function addPac() {
  const n=q('ap-nom').value.trim(),e=q('ap-edad').value,es=q('ap-est').value,
        pe=q('ap-peso').value,t=q('ap-tel').value.trim(),em=q('ap-email').value.trim();
  if(!n||!e||!es||!pe||!t){showToast('⚠ Completa los campos obligatorios');return;}
  const pass=generatePass(), id=DB._next.p++;
  DB.patients.push({id,nombre:n,edad:+e,estatura:+es,peso:+pe,telefono:t,email:em,pass,activo:true});
  q('cred-user').textContent=em||t;
  q('cred-pass').textContent=pass;
  closeModal('m-add-pac');
  ['ap-nom','ap-edad','ap-est','ap-peso','ap-tel','ap-email'].forEach(id=>q(id).value='');
  openModal('m-cred');
  renderPac();
}
function openEditPac(id){
  const p=patientById(id);
  q('ep-id').value=id;q('ep-nom').value=p.nombre;q('ep-edad').value=p.edad;
  q('ep-est').value=p.estatura;q('ep-peso').value=p.peso;q('ep-tel').value=p.telefono;q('ep-email').value=p.email;
  openModal('m-edit-pac');
}
function saveEditPac(){
  const p=patientById(+q('ep-id').value);
  p.nombre=q('ep-nom').value.trim();p.edad=+q('ep-edad').value;
  p.estatura=+q('ep-est').value;p.peso=+q('ep-peso').value;
  p.telefono=q('ep-tel').value.trim();p.email=q('ep-email').value.trim();
  closeModal('m-edit-pac');renderPac();showToast('✅ Paciente actualizado');
}
function openDelPac(id){
  q('del-pac-id').value=id;q('del-pac-name').textContent=patientById(id).nombre;
  openModal('m-del-pac');
}
function confirmDelPac(){
  DB.patients=DB.patients.filter(p=>p.id!==+q('del-pac-id').value);
  closeModal('m-del-pac');renderPac();showToast('🗑 Paciente eliminado');
}

/* ══ EXPEDIENTES ══ */
function renderExp(){
  const list=filterList(q('s-exp').value||'',DB.patients.filter(p=>hasExp(p.id)),p=>p.nombre);
  const el=q('list-exp');
  el.innerHTML=list.length?list.map(p=>`
    <div class="patient-card" style="cursor:pointer" onclick="showExpDetail(${p.id})">
      <div class="p-avatar">${initials(p.nombre)}</div>
      <div class="p-info"><h4>${p.nombre}</h4><p>${p.edad} años</p></div>
      <button class="btn btn-warning btn-sm" onclick="event.stopPropagation();openEditExp(${p.id})">✏</button>
    </div>`).join('')
  :'<p style="padding:16px;color:var(--text-soft);font-size:.88rem">No hay expedientes.</p>';
}
function showExpDetail(pid){
  const exp=expByPid(pid),p=patientById(pid);
  q('exp-detail').innerHTML=`
    <div>
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:18px">
        <div class="p-avatar" style="width:50px;height:50px;font-size:1.1rem">${initials(p.nombre)}</div>
        <div><h3 style="font-family:var(--font-display);font-size:1.2rem">${p.nombre}</h3>
        <p style="font-size:.82rem;color:var(--text-soft)">${p.edad} años · ${p.telefono}</p></div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
        <div class="card" style="background:var(--green-pale)"><p style="font-size:.7rem;font-weight:700;color:var(--green-dark);text-transform:uppercase;margin-bottom:6px">Objetivo Nutricional</p><p style="font-size:.88rem">${exp.objetivo}</p></div>
        <div class="card" style="background:var(--sand)"><p style="font-size:.7rem;font-weight:700;color:var(--text-mid);text-transform:uppercase;margin-bottom:6px">Diagnóstico</p><p style="font-size:.88rem">${exp.diagnostico}</p></div>
        <div class="card"><p style="font-size:.7rem;font-weight:700;color:var(--text-mid);text-transform:uppercase;margin-bottom:6px">Observaciones</p><p style="font-size:.88rem">${exp.observaciones}</p></div>
        <div class="card"><p style="font-size:.7rem;font-weight:700;color:var(--text-mid);text-transform:uppercase;margin-bottom:6px">Historial Clínico</p><p style="font-size:.88rem">${exp.historial}</p></div>
      </div>
    </div>`;
}
function renderNoExp(){
  const list=filterList(q('s-noexp').value||'',DB.patients.filter(p=>!hasExp(p.id)),p=>p.nombre);
  const el=q('list-noexp');
  el.innerHTML=list.length?list.map(p=>`
    <div class="patient-card" style="cursor:pointer" onclick="selectExpPac(${p.id},'${p.nombre.replace(/'/g,"\\'")}')">
      <div class="p-avatar">${initials(p.nombre)}</div>
      <div class="p-info"><h4>${p.nombre}</h4><p>${p.edad} años</p></div>
      <span class="badge badge-blue">Seleccionar</span>
    </div>`).join('')
  :'<p style="padding:10px;font-size:.85rem;color:var(--text-soft)">Todos los pacientes tienen expediente.</p>';
}
function openNuevoExp(){
  q('new-exp-form').style.display='none';
  q('btn-save-exp').style.display='none';
  q('s-noexp').value='';renderNoExp();
  openModal('m-new-exp');
}
function selectExpPac(id,name){
  q('ne-pid').value=id;q('new-exp-pname').textContent=name;
  q('new-exp-form').style.display='block';
  q('btn-save-exp').style.display='inline-flex';
}
function saveNewExp(){
  const pid=+q('ne-pid').value,obj=q('ne-obj').value.trim(),dia=q('ne-diag').value.trim(),
        obs=q('ne-obs').value.trim(),his=q('ne-hist').value.trim();
  if(!pid||!obj||!dia||!obs||!his){showToast('⚠ Completa todos los campos');return;}
  DB.expedientes.push({id:DB._next.e++,pacienteId:pid,objetivo:obj,diagnostico:dia,observaciones:obs,historial:his});
  closeModal('m-new-exp');
  ['ne-obj','ne-diag','ne-obs','ne-hist'].forEach(id=>q(id).value='');
  renderExp();showToast('✅ Expediente creado');
}
function openEditExp(pid){
  const exp=expByPid(pid);
  q('ee-id').value=exp.id;q('ee-obj').value=exp.objetivo;q('ee-diag').value=exp.diagnostico;
  q('ee-obs').value=exp.observaciones;q('ee-hist').value=exp.historial;
  openModal('m-edit-exp');
}
function saveEditExp(){
  const exp=DB.expedientes.find(e=>e.id===+q('ee-id').value);
  exp.objetivo=q('ee-obj').value.trim();exp.diagnostico=q('ee-diag').value.trim();
  exp.observaciones=q('ee-obs').value.trim();exp.historial=q('ee-hist').value.trim();
  closeModal('m-edit-exp');renderExp();showToast('✅ Expediente actualizado');
}

/* ══ PLANES ══ */
const DEF_HOR=[
  {hora:'07:00',comida:'Desayuno',         detalle:''},
  {hora:'10:00',comida:'Colación matutina', detalle:''},
  {hora:'14:00',comida:'Comida',            detalle:''},
  {hora:'17:00',comida:'Merienda',          detalle:''},
  {hora:'20:00',comida:'Cena',              detalle:''},
];
let selectedPlanPid=null;

function renderPlanes(){
  const list=filterList(q('s-plan').value||'',DB.patients.filter(p=>hasExp(p.id)),p=>p.nombre);
  const el=q('list-planes');
  el.innerHTML=list.length?list.map(p=>{
    const hp=planByPid(p.id);
    const sel=selectedPlanPid===p.id;
    return `<div class="plan-pac-card${sel?' selected':''}" onclick="showPlanDetail(${p.id})">
      <div class="plan-pac-top">
        <div class="p-avatar">${initials(p.nombre)}</div>
        <div class="p-info"><h4>${p.nombre}</h4><p>${p.edad} años · ${p.peso}kg</p></div>
      </div>
      <div class="plan-pac-body">
        <span>${hp?'<span class="badge badge-green">Plan asignado</span>':'<span class="badge badge-orange">Sin plan</span>'}</span>
        <div class="plan-pac-actions">
          ${!hp?`<button class="btn btn-primary btn-sm" onclick="event.stopPropagation();openPlanModal(${p.id},false)">＋ Asignar</button>`:''}
          ${hp ?`<button class="btn btn-warning btn-sm" onclick="event.stopPropagation();openPlanModal(${p.id},true)">✏ Modificar</button>`:''}
        </div>
      </div>
    </div>`;
  }).join('')
  :'<p style="padding:20px;color:var(--text-soft);font-size:.88rem">No hay pacientes con expediente.</p>';
}
function showPlanDetail(pid){
  selectedPlanPid=pid;
  renderPlanes();
  const plan=planByPid(pid),p=patientById(pid);
  const d=q('plan-detail');
  if(!plan){
    d.innerHTML=`<div style="text-align:center;padding:40px;color:var(--text-soft)">
      <p>Este paciente no tiene plan asignado.</p>
      <button class="btn btn-primary" style="margin-top:14px" onclick="openPlanModal(${pid},false)">＋ Asignar plan</button>
    </div>`;return;
  }
  d.innerHTML=`
    <div>
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:18px">
        <div class="p-avatar" style="width:48px;height:48px;font-size:1rem">${initials(p.nombre)}</div>
        <div><h3 style="font-family:var(--font-display);font-size:1.15rem">${p.nombre}</h3>
        <p style="font-size:.8rem;color:var(--text-soft)">${plan.calorias} kcal/día</p></div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:14px">
        <div class="card" style="background:var(--green-pale)">
          <p style="font-size:.7rem;font-weight:700;color:var(--green-dark);text-transform:uppercase;margin-bottom:4px">Calorías diarias</p>
          <p style="font-size:1.5rem;font-weight:700;color:var(--green-dark)">${plan.calorias} <span style="font-size:.85rem;font-weight:400">kcal</span></p>
        </div>
        <div class="card" style="background:var(--sand)">
          <p style="font-size:.7rem;font-weight:700;color:var(--text-mid);text-transform:uppercase;margin-bottom:4px">Alimentos</p>
          <p style="font-size:.85rem">${plan.alimentos}</p>
        </div>
      </div>
      <div class="card">
        <p style="font-size:.7rem;font-weight:700;color:var(--text-mid);text-transform:uppercase;margin-bottom:10px">Horarios de comida</p>
        <table style="width:100%;border-collapse:collapse">
          <thead><tr>
            <th style="background:var(--green-pale);color:var(--green-dark);font-size:.78rem;padding:8px 12px;text-align:left;width:80px">Hora</th>
            <th style="background:var(--green-pale);color:var(--green-dark);font-size:.78rem;padding:8px 12px;text-align:left">Tiempo</th>
            <th style="background:var(--green-pale);color:var(--green-dark);font-size:.78rem;padding:8px 12px;text-align:left">Detalle</th>
          </tr></thead>
          <tbody>${plan.horarios.map(h=>`<tr style="border-bottom:1px solid var(--border)">
            <td style="padding:9px 12px;font-weight:700;font-size:.83rem">${h.hora}</td>
            <td style="padding:9px 12px;font-size:.83rem">${h.comida}</td>
            <td style="padding:9px 12px;font-size:.8rem;color:var(--text-mid)">${h.detalle||'—'}</td>
          </tr>`).join('')}</tbody>
        </table>
      </div>
      ${plan.observacion?`<div class="card" style="margin-top:12px;background:var(--sand)"><p style="font-size:.7rem;font-weight:700;color:var(--text-mid);text-transform:uppercase;margin-bottom:4px">Observaciones</p><p style="font-size:.85rem">${plan.observacion}</p></div>`:''}
    </div>`;
}
function openPlanModal(pid,edit){
  const ex=planByPid(pid);
  q('pl-pid').value=pid;
  q('plan-title').textContent=edit?'Modificar Plan Alimenticio':'Asignar Plan Alimenticio';
  q('pl-cal').value=ex?ex.calorias:'';
  q('pl-ali').value=ex?ex.alimentos:'';
  q('pl-obs').value=ex?ex.observacion:'';
  const hrs=ex?ex.horarios:DEF_HOR;
  q('pl-horarios').innerHTML=hrs.map((h,i)=>`
    <div class="horario-row" id="hr-row-${i}">
      <div class="horario-row-head" onclick="toggleHorRow(${i})">
        <div class="hor-time-col">
          <input type="time" id="ph-h-${i}" value="${h.hora}" onclick="event.stopPropagation()"/>
          <input type="text" id="ph-c-${i}" value="${h.comida}" placeholder="Tiempo de comida" onclick="event.stopPropagation()"/>
        </div>
        <div class="hor-detail-col">
          <span class="hor-preview" id="ph-preview-${i}">${h.detalle||'Toca para agregar detalle de porciones…'}</span>
          <div class="hor-toggle-btn">▾</div>
        </div>
      </div>
      <div class="hor-expand">
        <label>Descripción y medidas exactas</label>
        <textarea id="ph-e-${i}" placeholder="Ej: 150 g pollo, 60 g arroz integral…" oninput="updatePreview(${i})">${h.detalle||''}</textarea>
      </div>
    </div>`).join('');
  openModal('m-plan');
}
function toggleHorRow(i){
  const row=document.getElementById('hr-row-'+i);
  row.classList.toggle('open');
}
function updatePreview(i){
  const val=q('ph-e-'+i).value;
  q('ph-preview-'+i).textContent=val||'Toca para agregar detalle de porciones…';
}
function savePlan(){
  const pid=+q('pl-pid').value,cal=q('pl-cal').value,ali=q('pl-ali').value.trim();
  if(!cal||!ali){showToast('⚠ Completa los campos obligatorios');return;}
  const horarios=[];
  for(let i=0;i<5;i++) horarios.push({hora:q(`ph-h-${i}`).value,comida:q(`ph-c-${i}`).value,detalle:q(`ph-e-${i}`).value});
  const idx=DB.planes.findIndex(pl=>pl.pacienteId===pid);
  const plan={id:idx>=0?DB.planes[idx].id:DB._next.pl++,pacienteId:pid,calorias:+cal,alimentos:ali,observacion:q('pl-obs').value,horarios};
  if(idx>=0) DB.planes[idx]=plan; else DB.planes.push(plan);
  closeModal('m-plan');
  renderPlanes();
  if(selectedPlanPid===pid) showPlanDetail(pid);
  showToast('✅ Plan guardado');
}

/* ══ CITAS — NUEVO SISTEMA ══ */
// Slots de trabajo: 09:00–18:00, cada hora (citas de 1 hora)
const WORK_SLOTS=['09:00','10:00','11:00','12:00','13:00','14:00','15:00','16:00','17:00'];

let cY=new Date().getFullYear(), cM=new Date().getMonth();
let selectedCalDate=null; // 'YYYY-MM-DD' o null

function changeMonth(d){
  cM+=d; if(cM>11){cM=0;cY++;} if(cM<0){cM=11;cY--;} renderCalendar();
}

/* Cuántas citas hay en una fecha */
function citasEnFecha(ds){ return DB.citas.filter(c=>c.fecha===ds); }

/* Renderizar calendario */
function renderCalendar(){
  q('cal-label').textContent=`${MONTHS[cM]} ${cY}`;
  const first=new Date(cY,cM,1).getDay(), days=new Date(cY,cM+1,0).getDate();
  const today=new Date(); today.setHours(0,0,0,0);
  let html=DAYS.map(d=>`<div class="cal-dh">${d}</div>`).join('');
  for(let i=0;i<first;i++) html+=`<div class="cal-day empty"></div>`;
  for(let d=1;d<=days;d++){
    const ds=`${cY}-${String(cM+1).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
    const dayDate=new Date(ds+'T00:00:00');
    const isToday=today.getTime()===dayDate.getTime();
    const isPast=dayDate<today;
    const cnt=citasEnFecha(ds).length;
    const isFull=cnt>=WORK_SLOTS.length;
    const isSelected=selectedCalDate===ds;
    let cls='cal-day';
    if(isPast)         cls+=' past';
    else if(isToday)   cls+=' today';
    else if(isFull)    cls+=' full';
    else if(cnt>0)     cls+=' partial';
    if(isSelected) cls+=' selected';
    const clickable=!isPast;
    html+=`<div class="${cls}" ${clickable?`onclick="selectDay('${ds}')"`:''}>${d}</div>`;
  }
  q('cal-grid').innerHTML=html;
}

/* Seleccionar día → mostrar horarios */
function selectDay(ds){
  selectedCalDate=ds;
  renderCalendar();
  showDaySlots(ds);
}

/* Panel derecho: horarios del día */
function showDaySlots(ds){
  const d=new Date(ds+'T00:00:00');
  const label=`${d.getDate()} de ${MONTHS[d.getMonth()]} ${d.getFullYear()}`;
  q('citas-panel-title').textContent=label;
  q('btn-volver-lista').style.display='inline-flex';

  const citasDelDia=citasEnFecha(ds);
  let html='';
  WORK_SLOTS.forEach(slot=>{
    const cita=citasDelDia.find(c=>c.hora===slot);
    if(cita){
      const p=patientById(cita.pacienteId);
      html+=`<div class="slot-item ocupado">
        <span class="slot-time">${slot}</span>
        <div class="slot-info">
          <div class="slot-pac">${p?p.nombre:'Paciente'}</div>
          <div class="slot-mot">${cita.motivo}</div>
        </div>
        <span class="slot-badge ocupado">Ocupado</span>
        <div class="slot-actions">
          <button class="btn btn-warning btn-sm" onclick="openEditCitaSlot(${cita.id})">✏</button>
          <button class="btn btn-danger  btn-sm" onclick="openDelCita(${cita.id})">🗑</button>
        </div>
      </div>`;
    } else {
      html+=`<div class="slot-item libre" onclick="openNuevaCita('${ds}','${slot}')">
        <span class="slot-time">${slot}</span>
        <span class="slot-badge libre">Disponible</span>
        <div style="flex:1;font-size:.78rem;color:var(--text-soft);margin-left:10px">Presiona para agendar</div>
      </div>`;
    }
  });
  q('citas-panel-body').innerHTML=`<div class="slot-grid">${html}</div>`;
}

/* Volver a lista de citas del mes */
function showCitasList(){
  selectedCalDate=null;
  renderCalendar();
  q('btn-volver-lista').style.display='none';
  q('citas-panel-title').textContent=`${MONTHS[cM]} ${cY}`;

  const citasMes=DB.citas.filter(c=>{
    const d=new Date(c.fecha+'T00:00:00');
    return d.getFullYear()===cY && d.getMonth()===cM;
  }).sort((a,b)=>a.fecha.localeCompare(b.fecha)||a.hora.localeCompare(b.hora));

  if(!citasMes.length){
    q('citas-panel-body').innerHTML='<p style="color:var(--text-soft);font-size:.88rem;padding:20px 0">No hay citas este mes.</p>';
    return;
  }
  let html='';
  citasMes.forEach(c=>{
    const p=patientById(c.pacienteId);
    const d=new Date(c.fecha+'T00:00:00');
    html+=`<div class="cita-card">
      <div class="cita-date-box"><span class="cd">${d.getDate()}</span><span class="cm">${MONTHS[d.getMonth()].slice(0,3)}</span></div>
      <div class="cita-body">
        <div class="c-pac">${p?p.nombre:'Paciente'}</div>
        <div class="c-hora">${c.hora} — 1 hora</div>
        <div class="c-mot">${c.motivo}</div>
      </div>
      <div class="cita-acts">
        <button class="btn btn-warning btn-sm" onclick="openEditCitaSlot(${c.id})">✏</button>
        <button class="btn btn-danger  btn-sm" onclick="openDelCita(${c.id})">🗑</button>
      </div>
    </div>`;
  });
  q('citas-panel-body').innerHTML=html;
}

/* Abrir modal nueva cita con fecha y hora prefijadas */
function openNuevaCita(fecha, hora){
  q('cf-id').value='';
  q('cf-fecha-txt').textContent=`${new Date(fecha+'T00:00:00').getDate()} de ${MONTHS[new Date(fecha+'T00:00:00').getMonth()]} — ${hora}`;
  q('cf-fecha-hidden').value=fecha;
  q('cf-hora-hidden').value=hora;
  q('cf-motivo').value='';q('cf-obs').value='';
  q('cf-pac-input').value='';
  q('cf-pac-id').value='';
  q('pac-dropdown').innerHTML='';q('pac-dropdown').classList.remove('open');
  openModal('m-cita-form');
}

/* Abrir modal editar cita existente */
function openEditCitaSlot(cid){
  const c=DB.citas.find(x=>x.id===cid);
  if(!c) return;
  const p=patientById(c.pacienteId);
  q('cf-id').value=c.id;
  q('cf-fecha-txt').textContent=`${new Date(c.fecha+'T00:00:00').getDate()} de ${MONTHS[new Date(c.fecha+'T00:00:00').getMonth()]} — ${c.hora}`;
  q('cf-fecha-hidden').value=c.fecha;
  q('cf-hora-hidden').value=c.hora;
  q('cf-motivo').value=c.motivo;
  q('cf-obs').value=c.observacion;
  q('cf-pac-input').value=p?p.nombre:'';
  q('cf-pac-id').value=c.pacienteId;
  q('pac-dropdown').classList.remove('open');
  openModal('m-cita-form');
}

/* Autocomplete de paciente en modal de cita */
function pacAutocomplete(){
  const val=q('cf-pac-input').value.trim();
  const dd=q('pac-dropdown');
  if(val.length<1){dd.classList.remove('open');return;}
  const matches=DB.patients.filter(p=>p.nombre.toLowerCase().includes(val.toLowerCase())).slice(0,5);
  if(!matches.length){dd.classList.remove('open');return;}
  dd.innerHTML=matches.map(p=>`
    <div class="pac-opt" onclick="selectPacCita(${p.id},'${p.nombre.replace(/'/g,"\\'")}')">
      <strong>${p.nombre.replace(new RegExp(val,'gi'),m=>`<mark style="background:var(--green-pale)">${m}</mark>`)}</strong>
      <span style="font-size:.75rem;color:var(--text-soft);margin-left:6px">${p.telefono}</span>
    </div>`).join('');
  dd.classList.add('open');
}
function selectPacCita(id,name){
  q('cf-pac-id').value=id;
  q('cf-pac-input').value=name;
  q('pac-dropdown').classList.remove('open');
}
document.addEventListener('click',e=>{
  if(!e.target.closest('.pac-autocomplete')) q('pac-dropdown')?.classList.remove('open');
});

function saveCita(){
  const id=q('cf-id').value;
  const fecha=q('cf-fecha-hidden').value, hora=q('cf-hora-hidden').value;
  const pid=+q('cf-pac-id').value, motivo=q('cf-motivo').value.trim(), obs=q('cf-obs').value.trim();
  if(!pid){showToast('⚠ Selecciona un paciente');return;}
  if(!motivo){showToast('⚠ Ingresa el motivo de consulta');return;}
  if(id){
    const c=DB.citas.find(c=>c.id===+id);
    Object.assign(c,{fecha,hora,pacienteId:pid,motivo,observacion:obs});
  } else {
    DB.citas.push({id:DB._next.c++,fecha,hora,pacienteId:pid,motivo,observacion:obs});
  }
  closeModal('m-cita-form');
  renderCalendar();
  if(selectedCalDate===fecha) showDaySlots(fecha); else showCitasList();
  showToast('✅ Cita guardada');
}

function openDelCita(cid){
  q('del-cita-id').value=cid;
  const c=DB.citas.find(c=>c.id===cid);
  if(c) q('del-cita-info').textContent=`${c.fecha} a las ${c.hora}`;
  openModal('m-del-cita');
}
function confirmDelCita(){
  const cid=+q('del-cita-id').value;
  const c=DB.citas.find(x=>x.id===cid);
  const fecha=c?c.fecha:null;
  DB.citas=DB.citas.filter(x=>x.id!==cid);
  closeModal('m-del-cita');
  renderCalendar();
  if(selectedCalDate&&selectedCalDate===fecha) showDaySlots(fecha); else showCitasList();
  showToast('🗑 Cita eliminada');
}

/* ══ INIT ══ */
document.addEventListener('DOMContentLoaded',()=>{
  Settings.load();
  renderPac();
  renderNoExp();
  initSettingsHandlers('m-settings');
});
