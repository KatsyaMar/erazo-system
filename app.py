import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import generate_password_hash 

# Importaciones de los modulos locales
from PYTHON.conection_db.db import get_db_connection 
from PYTHON.authentication.login import verificar_usuario, User
from PYTHON.utils.decorators import role_required
# Importacion de las rutas
from PYTHON.routes.auth import auth_bp


#=============================================================================================================================================

app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')

app.secret_key = '3da823b9d88ef74aa34a18ef8d56bf9113bfaf6fabaf050e'

# Configuración de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

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

#=============================================================================================================================================


# Ruta index
@app.route('/')
def index():
    # Pese a que ya hay una funcion que verifica, esto no se toca d: (el sistema muere si lo tocas xD)
    if current_user.is_authenticated:
        if current_user.rol == 'NUTRIOLOGO':
            return redirect(url_for('dashboard_nutriologo'))
        return redirect(url_for('dashboard_paciente'))
    return redirect(url_for('auth.login'))

# Ruta de login
app.register_blueprint(auth_bp)

# Rutas de dashboard

# Nutriologo
@app.route('/nutriologo')
@login_required 
@role_required('NUTRIOLOGO')
def dashboard_nutriologo(): return render_template('nutriologo.html', usuario=current_user)

# Paciente
@app.route('/paciente')
@login_required
@role_required('PACIENTE')
def dashboard_paciente(): return render_template('paciente.html', usuario = current_user)














# ESTA RUTA SE VA A BORRAR EN PRODUCCION, SOLO SE USA PARA CREAR USUARIOS DE PRUEBA

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        nombre = request.form.get('nombre_completo')
        correo = request.form.get('correo')
        telefono = request.form.get('telefono')
        rol = request.form.get('rol')
        password = request.form.get('contrasena')
        
        password_hash = generate_password_hash(password).decode('utf-8')

        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            query = """INSERT INTO usuarios (nombre_completo, correo, telefono, rol, contrasena) 
                       VALUES (%s, %s, %s, %s, %s)"""
            cursor.execute(query, (nombre, correo, telefono, rol, password_hash))
            conn.commit()
            flash('Registro exitoso. Ahora puedes iniciar sesión.', 'success')
            return redirect(url_for('auth.login'))
        except Exception:
            conn.rollback()
            flash('El correo o teléfono ya existen.', 'error')
        finally:
            cursor.close()
            conn.close()

    return render_template('register.html')

# DE AQUI PARA ARRIBA SE VA A BORRAR EN PRODUCCION














# Redirigimos al index por si el usuario es Cesar (usted no profe, el de mi equipo) y escribió la URL mal xd
@app.errorhandler(404)
def page_not_found(e):
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
    