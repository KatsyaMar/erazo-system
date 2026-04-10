/* ════════════════════════════════
   paciente.js
   ════════════════════════════════ */

const PAC_ID=1;

/* ══ NAV ══ */
const PAC_PAGES=['inicio','expediente','plan','citas'];
const PAC_META={
  inicio:     {t:'Inicio',           s:'Resumen de tu estado nutricional'},
  expediente: {t:'Mi Expediente',    s:'Información médica registrada por la nutrióloga'},
  plan:       {t:'Plan Alimenticio', s:'Plan personalizado asignado por la nutrióloga'},
  citas:      {t:'Mis Citas',        s:'Consultas programadas y calendario de disponibilidad'},
};
function showPage(name,el){
  PAC_PAGES.forEach(p=>q('pg-'+p).classList.toggle('hidden',p!==name));
  document.querySelectorAll('.nav-item').forEach(n=>n.classList.remove('active'));
  if(el) el.classList.add('active');
  q('tb-title').textContent=PAC_META[name].t;
  q('tb-sub').textContent=PAC_META[name].s;
  if(name==='citas'){renderPacCalendar();renderMisCitas();}
  if(name==='plan') renderPlanTab();
}

/* ══ CREDENCIALES ══ */
function openCredsModal(){
  const p=patientById(PAC_ID);
  q('cred-modal-user').value=p.email||p.telefono;
  q('cred-modal-pass').value=p.pass;
  openModal('m-creds');
}
function saveCredentials(){
  const p=patientById(PAC_ID);
  const u=q('cred-modal-user').value.trim();
  const pw=q('cred-modal-pass').value.trim();
  if(!u||!pw){showToast('⚠ Completa ambos campos');return;}
  if(pw.length<6){showToast('⚠ La contraseña debe tener al menos 6 caracteres');return;}
  if(u.includes('@')) p.email=u; else p.telefono=u;
  p.pass=pw;
  closeModal('m-creds');
  showToast('✅ Credenciales actualizadas');
}

/* ══ PLAN ══ */
function renderPlanTab(){
  const plan=planByPid(PAC_ID);
  if(!plan){
    q('plan-cal-val').textContent='—';
    q('plan-alimentos-val').textContent='Sin plan asignado aún.';
    q('plan-obs-val').textContent='—';
    q('plan-tbody').innerHTML='';
    return;
  }
  q('plan-cal-val').textContent=plan.calorias.toLocaleString();
  q('plan-alimentos-val').textContent=plan.alimentos;
  q('plan-obs-val').textContent=plan.observacion||'—';
  q('plan-tbody').innerHTML=plan.horarios.map((h,i)=>`
    <tr class="plan-horario-row" onclick="togglePlanRow(${i})">
      <td><strong>${h.hora}</strong></td>
      <td>${h.comida}</td>
      <td style="color:var(--text-soft);font-size:.78rem">Toca para ver detalle ▾</td>
    </tr>
    <tr class="plan-expand-row" id="plan-exp-${i}">
      <td colspan="3">${h.detalle||'Sin detalles adicionales.'}</td>
    </tr>`).join('');
}
function togglePlanRow(i){
  q('plan-exp-'+i).classList.toggle('open');
}

/* ══ CITAS PACIENTE ══ */
let pY=new Date().getFullYear(),pM=new Date().getMonth();
function changePacMonth(d){pM+=d;if(pM>11){pM=0;pY++;}if(pM<0){pM=11;pY--;}renderPacCalendar();}

function renderPacCalendar(){
  q('pac-cal-label').textContent=`${MONTHS[pM]} ${pY}`;
  const first=new Date(pY,pM,1).getDay(), days=new Date(pY,pM+1,0).getDate();
  const today=new Date();today.setHours(0,0,0,0);
  let html=DAYS.map(d=>`<div class="cal-dh">${d}</div>`).join('');
  for(let i=0;i<first;i++) html+=`<div class="cal-day empty"></div>`;
  for(let d=1;d<=days;d++){
    const ds=`${pY}-${String(pM+1).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
    const dayDate=new Date(ds+'T00:00:00');
    const isToday=today.getTime()===dayDate.getTime();
    const hasEvent=DB.citas.some(c=>c.fecha===ds&&c.pacienteId===PAC_ID);
    const dow=dayDate.getDay();
    const isPast=dayDate<today&&!isToday;
    const isWeekend=dow===0||dow===6;
    let cls='cal-day';
    if(isToday)          cls+=' today';
    else if(hasEvent)    cls+=' has-event';
    else if(isWeekend||isPast) cls+=' unavailable';
    else                 cls+=' available';
    const clickable=!isWeekend&&!isPast;
    html+=`<div class="${cls}" ${clickable?`onclick="selectPacDay('${ds}',${d})"`:''}">${d}</div>`;
  }
  q('pac-cal-grid').innerHTML=html;
}
function selectPacDay(ds,d){
  q('pac-cal-date').value=ds;
  q('pac-day-title').textContent=`${d} de ${MONTHS[pM]} ${pY}`;
  const miCita=DB.citas.find(c=>c.fecha===ds&&c.pacienteId===PAC_ID);
  const today=new Date();today.setHours(0,0,0,0);
  const dayDate=new Date(ds+'T00:00:00');
  const diffDays=Math.floor((dayDate-today)/(1000*60*60*24));
  const canModify=diffDays>=2;
  q('btn-pac-mod-cita').style.display=miCita&&canModify?'inline-flex':'none';
  q('btn-pac-del-cita').style.display=miCita&&canModify?'inline-flex':'none';
  q('msg-no-modify').style.display=miCita&&!canModify?'block':'none';
  openModal('m-pac-cal-day');
}
function openPacNuevaCita(){
  closeModal('m-pac-cal-day');
  const d=q('pac-cal-date').value;
  q('pac-cf-id').value='';q('pac-cita-title').textContent='Nueva Cita';
  q('pac-cf-fecha').value=d;q('pac-cf-motivo').value='';q('pac-cf-obs').value='';
  const taken=DB.citas.filter(c=>c.fecha===d).map(c=>c.hora);
  const avail=DB.slotsDisponibles.filter(s=>!taken.includes(s));
  q('pac-cf-hora').innerHTML=avail.length
    ?avail.map(s=>`<option value="${s}">${s}</option>`).join('')
    :'<option value="">Sin horarios disponibles</option>';
  openModal('m-pac-cita-form');
}
function openPacEditCita(){
  closeModal('m-pac-cal-day');
  const d=q('pac-cal-date').value;
  const c=DB.citas.find(c=>c.fecha===d&&c.pacienteId===PAC_ID);
  if(!c) return;
  q('pac-cf-id').value=c.id;q('pac-cita-title').textContent='Modificar Cita';
  q('pac-cf-fecha').value=c.fecha;q('pac-cf-motivo').value=c.motivo;q('pac-cf-obs').value=c.observacion;
  const taken=DB.citas.filter(x=>x.fecha===d&&x.id!==c.id).map(x=>x.hora);
  const avail=DB.slotsDisponibles.filter(s=>!taken.includes(s));
  q('pac-cf-hora').innerHTML=avail.map(s=>`<option value="${s}" ${s===c.hora?'selected':''}>${s}</option>`).join('');
  openModal('m-pac-cita-form');
}
function savePacCita(){
  const id=q('pac-cf-id').value,fecha=q('pac-cf-fecha').value,hora=q('pac-cf-hora').value,
        motivo=q('pac-cf-motivo').value.trim(),obs=q('pac-cf-obs').value.trim();
  if(!hora||!motivo){showToast('⚠ Completa los campos obligatorios');return;}
  if(id){const c=DB.citas.find(c=>c.id===+id);Object.assign(c,{fecha,hora,motivo,observacion:obs});}
  else  {DB.citas.push({id:DB._next.c++,fecha,hora,pacienteId:PAC_ID,motivo,observacion:obs});}
  closeModal('m-pac-cita-form');renderPacCalendar();renderMisCitas();showToast('✅ Cita guardada');
}
function openPacDelCita(){
  closeModal('m-pac-cal-day');
  const d=q('pac-cal-date').value;
  const c=DB.citas.find(c=>c.fecha===d&&c.pacienteId===PAC_ID);
  if(!c) return;
  q('pac-del-cita-id').value=c.id;
  q('pac-del-cita-info').textContent=`${c.fecha} a las ${c.hora}`;
  openModal('m-pac-del-cita');
}
function confirmPacDelCita(){
  DB.citas=DB.citas.filter(c=>c.id!==+q('pac-del-cita-id').value);
  closeModal('m-pac-del-cita');renderPacCalendar();renderMisCitas();
  showToast('🗑 Cita eliminada. Recuerda que deberás liquidar el costo de consulta.');
}
function renderMisCitas(){
  const mis=DB.citas.filter(c=>c.pacienteId===PAC_ID).sort((a,b)=>a.fecha.localeCompare(b.fecha)||a.hora.localeCompare(b.hora));
  const el=q('mis-citas-list');
  const today=new Date();today.setHours(0,0,0,0);
  if(!mis.length){el.innerHTML='<p style="color:var(--text-soft);font-size:.88rem">No tienes citas registradas.</p>';return;}
  el.innerHTML=mis.map(c=>{
    const d=new Date(c.fecha+'T00:00:00');
    const isPast=d<today;
    const diffDays=Math.floor((d-today)/(1000*60*60*24));
    const canMod=diffDays>=2;
    return `<div class="cita-item">
      <div class="cita-cal" style="${isPast?'background:var(--text-soft)':''}"><span class="day">${d.getDate()}</span><span class="mon">${MONTHS[d.getMonth()].slice(0,3)}</span></div>
      <div class="cita-info">
        <h4>${c.motivo}</h4>
        <p>${c.hora} · ${isPast?'Pasada':'Próxima'}</p>
        ${c.observacion?`<p style="font-size:.76rem">${c.observacion}</p>`:''}
      </div>
      ${!isPast&&canMod?`<div class="cita-actions">
        <button class="btn btn-warning btn-sm" onclick="editCitaList('${c.fecha}')">✏</button>
        <button class="btn btn-danger  btn-sm" onclick="delCitaList('${c.fecha}')">🗑</button>
      </div>`:''}
      ${!isPast&&!canMod?`<span class="badge badge-orange" style="flex-shrink:0;align-self:center">Confirmada</span>`:''}
    </div>`;
  }).join('');
}
function editCitaList(fecha){
  q('pac-cal-date').value=fecha;
  const d=new Date(fecha+'T00:00:00');
  q('pac-day-title').textContent=`${d.getDate()} de ${MONTHS[d.getMonth()]} ${d.getFullYear()}`;
  openPacEditCita();
}
function delCitaList(fecha){
  q('pac-cal-date').value=fecha;
  openPacDelCita();
}

/* ══ INIT ══ */
document.addEventListener('DOMContentLoaded',()=>{
  Settings.load();
  renderPlanTab();
  renderMisCitas();
  initSettingsHandlers('m-settings');
});
