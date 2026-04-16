# app.py  —  Punto de entrada de Erazo System
# ─────────────────────────────────────────────────────────────────────────────
import os
from flask       import Flask, render_template, redirect, url_for
from flask_login import LoginManager, login_required, current_user
from flask_bcrypt import Bcrypt
from dotenv      import load_dotenv

# Módulos propios
from PYTHON.conection_db.db              import get_db_connection
from PYTHON.authentication.login         import User
from PYTHON.routes.auth                  import auth_bp
from PYTHON.modulos.pacientes.pacientes  import pacientes_bp

# ─────────────────────────────────────────────────
# Carga variables de entorno
# ─────────────────────────────────────────────────
load_dotenv()

# ─────────────────────────────────────────────────
# Crear la app
# ─────────────────────────────────────────────────
app = Flask(
    __name__,
    template_folder='templates',
    static_folder='static',
)
app.secret_key = os.getenv('SECRET_KEY', 'erazo-secret-key-cambiar-en-produccion')

# ─────────────────────────────────────────────────
# Extensiones
# ─────────────────────────────────────────────────
bcrypt       = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Debes iniciar sesión para acceder.'


@login_manager.user_loader
def load_user(user_id):
    """Recarga el usuario desde la BD en cada request."""
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT id_usuario, correo, nombre_completo, rol FROM usuarios WHERE id_usuario = %s",
        (user_id,)
    )
    row = cursor.fetchone()
    cursor.close(); conn.close()
    if row:
        return User(row['id_usuario'], row['correo'], row['nombre_completo'], row['rol'])
    return None


# ─────────────────────────────────────────────────
# Registrar Blueprints
# ─────────────────────────────────────────────────
app.register_blueprint(auth_bp)
app.register_blueprint(pacientes_bp)

# Importar y registrar el resto de módulos
# (se añadirán conforme se desarrollen)
# from PYTHON.modules.expedientes.expedientes import expedientes_bp
# app.register_blueprint(expedientes_bp)
# from PYTHON.modules.planes.planes import planes_bp
# app.register_blueprint(planes_bp)
# from PYTHON.modules.citas.citas import citas_bp
# app.register_blueprint(citas_bp)


# ─────────────────────────────────────────────────
# Rutas principales (dashboards)
# ─────────────────────────────────────────────────
main_bp = __import__('flask', fromlist=['Blueprint']).Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.rol == 'NUTRIOLOGO':
            return redirect(url_for('main.dashboard_nutriologo'))
        return redirect(url_for('main.dashboard_paciente'))
    return redirect(url_for('auth.login'))

@main_bp.route('/nutriologo')
@login_required
def dashboard_nutriologo():
    if current_user.rol != 'NUTRIOLOGO':
        return redirect(url_for('main.dashboard_paciente'))
    return render_template('nutriologo.html', usuario=current_user)

@main_bp.route('/paciente')
@login_required
def dashboard_paciente():
    if current_user.rol != 'PACIENTE':
        return redirect(url_for('main.dashboard_nutriologo'))
    return render_template('paciente.html', usuario=current_user)

app.register_blueprint(main_bp)


# ─────────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────────
if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(
        host  = os.getenv('FLASK_HOST', '0.0.0.0'),
        port  = int(os.getenv('FLASK_PORT', 5000)),
        debug = debug_mode,
    )
