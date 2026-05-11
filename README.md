# Sistema Erazo — Módulo de Gestión de Pacientes

## Estructura del proyecto

```
erazo_flask/
├── app.py                          ← Punto de entrada Flask
├── requirements.txt                ← Dependencias Python
├── .env.example                    ← Variables de entorno (copiar como .env)
│
├── PYTHON/
│   ├── conection_db/
│   │   └── db.py                   ← Conexión a MySQL
│   ├── authentication/
│   │   └── login.py                ← Modelo User + verificar_usuario()
│   └── pacientes/
│       └── pacientes_db.py         ← CRUD de pacientes
│
├── templates/
│   ├── index.html                  ← Login (Jinja2)
│   ├── nutriologo.html             ← Dashboard nutriólogo (Jinja2)
│   └── paciente.html               ← Dashboard paciente
│
├── static/
│   ├── global.css
│   ├── index.css
│   ├── nutriologo.css
│   └── paciente.css
│
└── js/                             ← JS del frontend estático (referencia)
```

## Instalación

```bash
# 1. Crear entorno virtual
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar base de datos
# - Ejecutar erazo_system.sql en MySQL
# - Copiar .env.example como .env y ajustar credenciales

# 4. Arrancar
python app.py
```

## Rutas del módulo de pacientes

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/nutriologo` | Lista pacientes activos (con búsqueda ?q=) |
| POST | `/pacientes/registrar` | Alta de nuevo paciente + genera contraseña |
| GET | `/pacientes/<id>` | Consulta individual (JSON para modal) |
| POST | `/pacientes/<id>/modificar` | Modificación de datos (teléfono inmutable) |
| POST | `/pacientes/<id>/desactivar` | Baja lógica (estado ACTIVO → INACTIVO) |

## Credenciales de prueba (nutriólogo)

Crear el primer usuario nutriólogo directamente en la base de datos:

```sql
INSERT INTO usuarios (telefono, nombre_completo, correo, contrasena, rol)
VALUES (
  '5500000001',
  'Dra. Erazo',
  'erazo@correo.com',
  -- Generar hash con: python -c "from flask_bcrypt import generate_password_hash; print(generate_password_hash('Erazo2026!').decode())"
  '$2b$12$HASH_GENERADO_AQUI',
  'NUTRIOLOGO'
);
```

## Notas técnicas

- **Baja lógica**: los pacientes nunca se eliminan físicamente. Solo cambia `estado = 'INACTIVO'` en `usuarios`.
- **Contraseñas**: se generan automáticamente con formato `ERA-XXXX` y se almacenan hasheadas con bcrypt.
- **IMC**: calculado automáticamente por MySQL como columna generada en `pacientes`.
- **Búsqueda**: filtra por nombre completo, correo o teléfono (LIKE).
- **Teléfono**: actúa como identificador único y no puede modificarse.
