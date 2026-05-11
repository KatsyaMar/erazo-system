# PYTHON/routes/auth.py
# ─────────────────────────────────────────────────────────────────────────────
# Módulo de autenticación: login, logout y recuperación de contraseña
# ─────────────────────────────────────────────────────────────────────────────
import smtplib
import os
from email.mime.text      import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime             import datetime, timedelta

from flask               import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login         import login_user, logout_user, current_user
from flask_bcrypt        import generate_password_hash
from itsdangerous        import URLSafeTimedSerializer, SignatureExpired, BadSignature

from PYTHON.conection_db.db          import get_db_connection
from PYTHON.authentication.login     import verificar_usuario

auth_bp = Blueprint('auth', __name__)


# ──────────────────────────────────────────────────
# LOGIN
# ──────────────────────────────────────────────────
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Si ya está autenticado, redirigir a su panel
    if current_user.is_authenticated:
        return _redirect_by_rol(current_user.rol)

    if request.method == 'POST':
        correo    = request.form.get('correo', '').strip()
        contrasena = request.form.get('contrasena', '')

        # Validar campos vacíos
        if not correo or not contrasena:
            flash('Por favor, llene todos los campos.', 'error')
            return render_template('index.html', correo_enviado=correo)

        conn   = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Verificar existencia del correo
        cursor.execute(
            "SELECT id_usuario, contrasena, rol, intentos_fallidos, bloqueo_hasta "
            "FROM usuarios WHERE correo = %s",
            (correo,)
        )
        user_data = cursor.fetchone()

        if not user_data:
            cursor.close(); conn.close()
            flash('Correo incorrecto', 'error')
            return render_template('index.html', correo_enviado=correo)

        # Verificar bloqueo
        ahora = datetime.now()
        if user_data['bloqueo_hasta'] and ahora < user_data['bloqueo_hasta']:
            mins_rest = int((user_data['bloqueo_hasta'] - ahora).total_seconds() / 60) + 1
            flash(f'Cuenta bloqueada. Intente en {mins_rest} minuto(s).', 'error')
            cursor.close(); conn.close()
            return render_template('index.html', correo_enviado=correo)

        # Verificar contraseña
        user = verificar_usuario(conn, correo, contrasena)

        if user:
            # Éxito: reiniciar intentos
            cursor.execute(
                "UPDATE usuarios SET intentos_fallidos = 0, bloqueo_hasta = NULL, estado = 'ACTIVO' "
                "WHERE id_usuario = %s",
                (user_data['id_usuario'],)
            )
            conn.commit(); cursor.close(); conn.close()
            login_user(user)
            flash('Inicio de sesión exitoso', 'success')
            return _redirect_by_rol(user.rol)

        else:
            # Fallo: incrementar intentos
            nuevos = user_data['intentos_fallidos'] + 1
            bloqueo_time = None
            nuevo_estado = 'ACTIVO'

            if nuevos >= 5:
                bloqueo_time = ahora + timedelta(minutes=15)
                nuevo_estado = 'BLOQUEADO'
                msg = 'Demasiados intentos. Cuenta bloqueada por 15 minutos.'
            else:
                msg = f'Contraseña incorrecta. Te quedan {5 - nuevos} intento(s).'

            cursor.execute(
                "UPDATE usuarios SET intentos_fallidos = %s, bloqueo_hasta = %s, estado = %s "
                "WHERE correo = %s",
                (nuevos, bloqueo_time, nuevo_estado, correo)
            )
            conn.commit(); cursor.close(); conn.close()
            flash(msg, 'error')
            return render_template('index.html', correo_enviado=correo)

    return render_template('index.html')


# ──────────────────────────────────────────────────
# LOGOUT
# ──────────────────────────────────────────────────
@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


# ──────────────────────────────────────────────────
# RECUPERAR CONTRASEÑA — solicitar enlace
# ──────────────────────────────────────────────────
@auth_bp.route('/solicitar-recuperacion', methods=['GET', 'POST'])
def solicitar_recuperacion():
    if request.method == 'POST':
        correo = request.form.get('correo', '').strip()

        conn   = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id_usuario FROM usuarios WHERE correo = %s", (correo,))
        usuario = cursor.fetchone()
        cursor.close(); conn.close()

        if usuario:
            s      = URLSafeTimedSerializer(current_app.secret_key)
            token  = s.dumps(correo, salt='recuperacion-pass')
            enlace = url_for('auth.restablecer_contrasena', token=token, _external=True)
            enviado = _enviar_correo_recuperacion(correo, enlace)

            if enviado:
                flash('Se ha enviado un enlace de recuperación a su correo electrónico', 'success')
            else:
                flash('Hubo un error al enviar el correo. Intente más tarde.', 'error')
        else:
            flash('El correo electrónico no se encuentra registrado', 'error')

        return redirect(url_for('auth.solicitar_recuperacion'))

    return render_template('index.html', mostrar_recuperacion=True)


# ──────────────────────────────────────────────────
# RECUPERAR CONTRASEÑA — restablecer
# ──────────────────────────────────────────────────
@auth_bp.route('/restablecer-contrasena/<token>', methods=['GET', 'POST'])
def restablecer_contrasena(token):
    s = URLSafeTimedSerializer(current_app.secret_key)
    try:
        correo = s.loads(token, salt='recuperacion-pass', max_age=1800)
    except SignatureExpired:
        flash('El enlace ha expirado. Solicita uno nuevo.', 'error')
        return redirect(url_for('auth.solicitar_recuperacion'))
    except BadSignature:
        flash('El enlace es inválido.', 'error')
        return redirect(url_for('auth.solicitar_recuperacion'))

    if request.method == 'POST':
        nueva     = request.form.get('nueva_contrasena', '')
        confirmar = request.form.get('confirmar_contrasena', '')

        if nueva != confirmar:
            flash('Las contraseñas no coinciden.', 'error')
            return redirect(url_for('auth.restablecer_contrasena', token=token))

        if len(nueva) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'error')
            return redirect(url_for('auth.restablecer_contrasena', token=token))

        hashed = generate_password_hash(nueva).decode('utf-8')
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET contrasena = %s WHERE correo = %s", (hashed, correo))
        conn.commit(); cursor.close(); conn.close()

        flash('La contraseña se actualizó correctamente', 'success')
        return redirect(url_for('auth.login'))

    return render_template('index.html', mostrar_reset=True, token=token)


# ──────────────────────────────────────────────────
# HELPERS PRIVADOS
# ──────────────────────────────────────────────────
def _redirect_by_rol(rol):
    if rol == 'NUTRIOLOGO':
        return redirect(url_for('main.dashboard_nutriologo'))
    return redirect(url_for('main.dashboard_paciente'))


def _enviar_correo_recuperacion(destinatario, enlace):
    remitente = os.getenv('MAIL_USER', 'dla140505@gmail.com')
    password  = os.getenv('MAIL_PASS', '')

    msg             = MIMEMultipart()
    msg['From']     = remitente
    msg['To']       = destinatario
    msg['Subject']  = 'Recuperación de contraseña – Erazo System'

    cuerpo = (
        f"Hola,\n\nHas solicitado restablecer tu contraseña.\n"
        f"Haz clic en el siguiente enlace (expira en 30 minutos):\n\n{enlace}\n\n"
        f"Si no solicitaste este cambio, ignora este correo."
    )
    msg.attach(MIMEText(cuerpo, 'plain'))

    try:
        servidor = smtplib.SMTP('smtp.gmail.com', 587)
        servidor.starttls()
        servidor.login(remitente, password)
        servidor.send_message(msg)
        servidor.quit()
        return True
    except Exception as e:
        current_app.logger.error(f'Error enviando correo: {e}')
        return False
