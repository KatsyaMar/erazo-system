import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import generate_password_hash # Nueva para registro

# Importaciones de tus módulos locales
from PYTHON.conection_db.db import get_db_connection 
from PYTHON.authentication.login import verificar_usuario, User

app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')

app.secret_key = 'tu_llave_secreta_aqui'

# Configuración de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id_usuario, correo, nombre_completo, rol FROM usuarios WHERE id_usuario = %s", (user_id,))
    data = cursor.fetchone()
    cursor.close()
    conn.close()
    if data:
        return User(data['id_usuario'], data['correo'], data['nombre_completo'], data['rol'])
    return None






# --- RUTAS DE AUTENTICACIÓN ---

@app.route('/')
def index():
    # Si el usuario ya inició sesión, lo mandamos a su dashboard correspondiente
    if current_user.is_authenticated:
        if current_user.rol == 'NUTRIOLOGO':
            return redirect(url_for('dashboard_nutriologo'))
        return redirect(url_for('dashboard_paciente'))
    
    # Si no hay sesión activa, la página por defecto es el Login
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    # SI YA ESTÁ LOGUEADO: Redirigir según su rol
    if current_user.is_authenticated:
        if current_user.rol == 'NUTRIOLOGO':
            return redirect(url_for('dashboard_nutriologo'))
        return redirect(url_for('dashboard_paciente'))

    if request.method == 'POST':
        # ... (todo tu código actual de login)
        correo = request.form.get('correo')
        contrasena = request.form.get('contrasena')
        
        conn = get_db_connection()
        user = verificar_usuario(conn, correo, contrasena)
        conn.close()

        if user:
            login_user(user)
            if user.rol == 'NUTRIOLOGO':
                return redirect(url_for('dashboard_nutriologo'))
            return redirect(url_for('dashboard_paciente'))
        
        flash('Correo o contraseña incorrectos', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    # SI YA ESTÁ LOGUEADO: No puede registrarse, redirigir a su dashboard
    if current_user.is_authenticated:
        if current_user.rol == 'NUTRIOLOGO':
            return redirect(url_for('dashboard_nutriologo'))
        return redirect(url_for('dashboard_paciente'))

    if request.method == 'POST':
        # ... (todo tu código actual de registro)
        nombre = request.form.get('nombre_completo')
        correo = request.form.get('correo')
        telefono = request.form.get('telefono')
        rol = request.form.get('rol')
        password = request.form.get('contrasena')
        
        # Encriptamos antes de guardar
        password_hash = generate_password_hash(password).decode('utf-8')

        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            query = """INSERT INTO usuarios (nombre_completo, correo, telefono, rol, contrasena) 
                       VALUES (%s, %s, %s, %s, %s)"""
            cursor.execute(query, (nombre, correo, telefono, rol, password_hash))
            conn.commit()
            flash('Registro exitoso. Ahora puedes iniciar sesión.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            conn.rollback()
            flash('El correo o teléfono ya existen.', 'error')
        finally:
            cursor.close()
            conn.close()

    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))










# --- LÓGICA DEL PANEL DE NUTRIÓLOGO ---

@app.route('/registro_paciente', methods=['POST'])
@login_required
def registro_paciente():
    if current_user.rol != 'NUTRIOLOGO':
        return redirect(url_for('login'))

    # Obtenemos datos del formulario
    telefono = request.form.get('telefono')
    nombre = request.form.get('nombre')
    edad = request.form.get('edad')
    peso = request.form.get('peso')
    estatura = request.form.get('estatura')
    correo = request.form.get('correo')
    password = request.form.get('contrasena')

    # Encriptamos la contraseña del paciente
    password_hash = generate_password_hash(password).decode('utf-8')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 1. Insertar en la tabla 'usuarios'
        query_user = """INSERT INTO usuarios (telefono, nombre_completo, correo, contrasena, rol) 
                        VALUES (%s, %s, %s, %s, 'PACIENTE')"""
        cursor.execute(query_user, (telefono, nombre, correo, password_hash))
        
        # Obtenemos el ID del usuario recién creado
        id_usuario = cursor.lastrowid

        # 2. Insertar en la tabla 'pacientes'
        query_paciente = """INSERT INTO pacientes (id_usuario, edad, peso, estatura) 
                            VALUES (%s, %s, %s, %s)"""
        cursor.execute(query_paciente, (id_usuario, edad, peso, estatura))

        conn.commit()
        flash(f'Paciente {nombre} registrado con éxito.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error al registrar: El correo o teléfono ya existen.', 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('dashboard_nutriologo'))








# --- LÓGICA DEL PANEL DE PACIENTE ---

@app.route('/agendar_cita_paciente', methods=['POST'])
@login_required
def agendar_cita_paciente():
    if current_user.rol != 'PACIENTE':
        return redirect(url_for('login'))
    
    # Aquí iría la lógica SQL para insertar en la tabla citas
    # Por ahora enviamos una confirmación visual
    fecha = request.form.get('fecha_paciente')
    flash(f'Solicitud de cita para el {fecha} enviada al nutriólogo.', 'success')
    return redirect(url_for('dashboard_paciente'))

@app.route('/cancelar_cita', methods=['POST'])
@login_required
def cancelar_cita():
    # En una fase real, aquí borrarías o cambiarías el estado en la DB
    flash('La cita ha sido cancelada correctamente.', 'info')
    return redirect(url_for('dashboard_paciente'))










# --- RUTAS DE DASHBOARD (TEMPORALES PARA PRUEBAS) ---
@app.route('/crear_expediente', methods=['POST'])
@login_required
def crear_expediente():
    flash('Funcionalidad de expediente en desarrollo', 'info')
    return redirect(url_for('dashboard_nutriologo'))

@app.route('/crear_plan', methods=['POST'])
@login_required
def crear_plan():
    flash('Funcionalidad de planes en desarrollo', 'info')
    return redirect(url_for('dashboard_nutriologo'))

@app.route('/crear_cita', methods=['POST'])
@login_required
def crear_cita():
    flash('Funcionalidad de citas en desarrollo', 'info')
    return redirect(url_for('dashboard_nutriologo'))
# --- RUTAS DE DASHBOARD ---

@app.route('/nutriologo')
@login_required
def dashboard_nutriologo():
    # Verificamos que solo un NUTRIOLOGO pueda entrar aquí
    if current_user.rol != 'NUTRIOLOGO':
        flash('No tienes permiso para acceder a esta sección.', 'error')
        return redirect(url_for('login'))
        
    # Renderizamos el HTML real de tu carpeta templates
    return render_template('nutriologo.html', usuario=current_user)

@app.route('/paciente')
@login_required
def dashboard_paciente():
    # Verificamos que solo un PACIENTE pueda entrar aquí
    if current_user.rol != 'PACIENTE':
        flash('Acceso restringido.', 'error')
        return redirect(url_for('login'))

    # Renderizamos el HTML real de tu carpeta templates
    return render_template('paciente.html', usuario=current_user)


if __name__ == '__main__':
    # El parámetro debug=True activa la recarga automática
    app.run(debug=True)