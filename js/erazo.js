/* ════════════════════════════════════════════════
   erazo.js  —  Datos compartidos + utilidades
   Sistema Erazo · Gestión Nutricional
   ════════════════════════════════════════════════ */

const DB = {
  patients: [
    { id:1, nombre:'Ana García López',     edad:28, estatura:1.62, peso:65, telefono:'5512340001', email:'ana@erazo.com',     pass:'ERA-1234', activo:true },
    { id:2, nombre:'Carlos Mendoza Ruiz',  edad:35, estatura:1.75, peso:82, telefono:'5512340002', email:'carlos@erazo.com',  pass:'ERA-5678', activo:true },
    { id:3, nombre:'Sofía Torres Vega',    edad:22, estatura:1.58, peso:54, telefono:'5512340003', email:'sofia@erazo.com',   pass:'ERA-9012', activo:true },
    { id:4, nombre:'Luis Hernández Cruz',  edad:45, estatura:1.80, peso:95, telefono:'5512340004', email:'luis@erazo.com',    pass:'ERA-3456', activo:true },
    { id:5, nombre:'María Reyes Jiménez',  edad:31, estatura:1.65, peso:70, telefono:'5512340005', email:'maria@erazo.com',   pass:'ERA-7890', activo:true },
  ],

  expedientes: [
    { id:1, pacienteId:1, objetivo:'Reducción de peso 5 kg en 3 meses', diagnostico:'Sobrepeso grado I', observaciones:'Paciente con buen seguimiento', historial:'Hipotiroidismo controlado' },
    { id:2, pacienteId:2, objetivo:'Ganar masa muscular y mejorar rendimiento', diagnostico:'Normopeso, déficit proteico', observaciones:'Entrena 4 veces por semana', historial:'Sin antecedentes relevantes' },
  ],

  planes: [
    { id:1, pacienteId:1, calorias:1800, alimentos:'Avena, pollo, verduras, frutas, legumbres', observacion:'Evitar azúcares refinados y bebidas calóricas', horarios:[
      { hora:'07:00', comida:'Desayuno',         detalle:'Avena con fruta y leche descremada. 1 taza avena (80 g), 1 pieza fruta, 250 ml leche descremada.' },
      { hora:'10:00', comida:'Colación matutina', detalle:'Manzana con almendras. 1 manzana mediana (150 g), 20 g almendras (aprox. 15 piezas).' },
      { hora:'14:00', comida:'Comida',            detalle:'Pollo a la plancha 150 g + arroz integral 60 g + ensalada mixta sin límite. Usar aceite de oliva (1 cdita).' },
      { hora:'17:00', comida:'Merienda',          detalle:'Yogurt natural sin azúcar 150 g. Puede agregar 1 cdita de semillas de chía.' },
      { hora:'20:00', comida:'Cena',              detalle:'Sopa de verduras (300 ml) con 2 tostadas integrales. Evitar sal extra.' },
    ]},
  ],

  citas: [
    { id:1, fecha:'2026-04-12', hora:'10:00', pacienteId:1, motivo:'Seguimiento mensual', observacion:'' },
    { id:2, fecha:'2026-04-15', hora:'11:30', pacienteId:2, motivo:'Primera consulta', observacion:'Traer estudios de laboratorio' },
    { id:3, fecha:'2026-04-20', hora:'09:00', pacienteId:3, motivo:'Revisión de plan alimenticio', observacion:'' },
  ],

  // Horarios disponibles para citas (slots)
  slotsDisponibles: ['09:00','10:00','11:00','12:00','16:00','17:00','18:00'],

  _next: { p:6, e:3, pl:2, c:4 },
};

/* ══ HELPERS ══ */
function initials(name) { return name.trim().split(/\s+/).slice(0,2).map(w=>w[0]).join('').toUpperCase(); }
function patientById(id) { return DB.patients.find(p=>p.id===id); }
function hasExp(pid)      { return DB.expedientes.some(e=>e.pacienteId===pid); }
function expByPid(pid)    { return DB.expedientes.find(e=>e.pacienteId===pid); }
function planByPid(pid)   { return DB.planes.find(pl=>pl.pacienteId===pid); }
function citasByPid(pid)  { return DB.citas.filter(c=>c.pacienteId===pid); }
function q(id)            { return document.getElementById(id); }

function filterList(query, arr, keyFn) {
  const t=query.toLowerCase();
  return arr.filter(x=>keyFn(x).toLowerCase().includes(t));
}

/* ══ MODAL HELPERS ══ */
function openModal(id)  { const el=q(id); if(el) el.classList.add('open'); }
function closeModal(id) { const el=q(id); if(el) el.classList.remove('open'); }

/* ══ TOAST ══ */
function showToast(msg, ms=2800) {
  let t=q('_toast');
  if(!t){ t=document.createElement('div'); t.id='_toast'; t.className='toast'; document.body.appendChild(t); }
  t.textContent=msg; t.classList.add('show');
  clearTimeout(t._t); t._t=setTimeout(()=>t.classList.remove('show'),ms);
}

/* ══ FECHA HELPERS ══ */
const MONTHS=['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];
const DAYS  =['Dom','Lun','Mar','Mié','Jue','Vie','Sáb'];

function dateStr(date) { return date.toISOString().split('T')[0]; }
function addDays(date, n) { const d=new Date(date); d.setDate(d.getDate()+n); return d; }

/* ══ PASSWORD GENERATOR ══ */
function generatePass() {
  const chars='ABCDEFGHJKMNPQRSTUVWXYZ23456789';
  let p='ERA-';
  for(let i=0;i<4;i++) p+=chars[Math.floor(Math.random()*chars.length)];
  return p;
}

/* ══ SETTINGS (accesibilidad) ══ */
const Settings = {
  fontSize: 16,
  theme: 'light',
  vision: 'normal',

  apply() {
    document.documentElement.style.setProperty('--font-size-base', this.fontSize+'px');
    document.documentElement.setAttribute('data-theme', this.theme);
    document.documentElement.setAttribute('data-vision', this.vision);
  },

  load() {
    try {
      const s = JSON.parse(sessionStorage.getItem('erazo_settings')||'{}');
      if(s.fontSize) this.fontSize = s.fontSize;
      if(s.theme)    this.theme    = s.theme;
      if(s.vision)   this.vision   = s.vision;
    } catch(e){}
    this.apply();
  },

  save() {
    sessionStorage.setItem('erazo_settings', JSON.stringify({ fontSize:this.fontSize, theme:this.theme, vision:this.vision }));
    this.apply();
  },

  changeFontSize(delta) {
    this.fontSize = Math.min(22, Math.max(12, this.fontSize + delta));
    this.save();
    return this.fontSize;
  },

  setTheme(t)  { this.theme=t;  this.save(); },
  setVision(v) { this.vision=v; this.save(); },
};

/* ══ SETTINGS MODAL BUILDER ══ */
function buildSettingsModal(modalId) {
  const modal = q(modalId);
  if(!modal) return;

  // Sync UI state
  const fs = modal.querySelector('#cfg-fs-val');
  if(fs) fs.textContent = Settings.fontSize+'px';

  const darkToggle = modal.querySelector('#cfg-dark');
  if(darkToggle) darkToggle.checked = Settings.theme==='dark';

  modal.querySelectorAll('.vision-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.v === Settings.vision);
  });
}

function initSettingsHandlers(modalId) {
  const modal = q(modalId);
  if(!modal) return;

  modal.querySelector('#cfg-fs-minus')?.addEventListener('click', () => {
    const v = Settings.changeFontSize(-1);
    modal.querySelector('#cfg-fs-val').textContent = v+'px';
  });
  modal.querySelector('#cfg-fs-plus')?.addEventListener('click', () => {
    const v = Settings.changeFontSize(1);
    modal.querySelector('#cfg-fs-val').textContent = v+'px';
  });
  modal.querySelector('#cfg-dark')?.addEventListener('change', e => {
    Settings.setTheme(e.target.checked ? 'dark' : 'light');
  });
  modal.querySelectorAll('.vision-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      modal.querySelectorAll('.vision-btn').forEach(b=>b.classList.remove('active'));
      btn.classList.add('active');
      Settings.setVision(btn.dataset.v);
    });
  });
}
