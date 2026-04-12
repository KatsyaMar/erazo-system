# PYTHON/routes/auth.py
from flask import render_template, request, redirect, url_for, flash, current_app
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from flask_bcrypt import generate_password_hash
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from datetime import datetime, timedelta
from PYTHON.conection_db.db import get_db_connection
from PYTHON.authentication.login import verificar_usuario

# =======Definimos el blueprint=======
auth_bp = Blueprint('auth', __name__)


# ===========RUTA DE LOGIN===========
@auth_bp.route('/login', methods=['GET', 'POST'])
def login(): 
    if current_user.is_authenticated:
        if current_user.rol == 'NUTRIOLOGO':
            return redirect(url_for('dashboard_nutriologo'))
        return redirect(url_for('dashboard_paciente'))
    
    # =======Validacion del metodo=======
    
    if request.method == 'POST':
        
        # =======Lógica del metodo POST=======
        
        #Obtiene las credenciales del formulario
        correo = request.form.get('correo')
        contrasena = request.form.get('contrasena')
        
        # Verifica que no vengan vacios, si no, salta un mensaje de error
        if not correo or not contrasena:
            flash('Por favor, llene todos los campos.', 'error')
            # Reedirige al login
            return render_template('login.html', correo_enviado=correo)
        
        # Si se verifico que los campos no estan vacios. Se inicia la coneccion con la base de datos
        conn = get_db_connection()
        # Nos regresa los datos como un diccionario
        cursor = conn.cursor(dictionary=True)
        
        
        # Consulta para verificar si el corrreo existe
        cursor.execute("SELECT id_usuario, contrasena, rol, intentos_fallidos, bloqueo_hasta FROM usuarios WHERE correo = %s", (correo,))
        # Si existe, lo guarda en 'user_data'
        user_data = cursor.fetchone()
        
        # Si el correo no existe, se cierra la coneccion y salta un error
        if not user_data:
            # Cierra coneccion con BD
            conn.close()
            flash('Correo incorrecto', 'error')
            
            #Reedirige al login
            return render_template('login.html', correo_enviado=correo)

        # Verifica que el usuario no este bloqueado por intentos fallidos (que tonto xD)
        
        # Iniciamos una variable que tome el tiempo actual
        ahora = datetime.now()
        
        #Verifica si existen datos en 'bloqueo_hasta' y si el tiempo actual es menor al tiempo de bloqueo
        if user_data['bloqueo_hasta'] and ahora < user_data['bloqueo_hasta']:
            
            # Si el tiempo es menor, se calcula el tiempo restante (una simple resta) y se muestra el mensaje de error
            tiempo_restante = int((user_data['bloqueo_hasta'] - ahora).total_seconds() / 60)
            flash(f'Cuenta bloqueada por seguridad.\nIntente en {tiempo_restante} minutos.', 'error')
            
            # Cierra coneccion con BD
            conn.close()
            return render_template('login.html', correo_enviado=correo)

        # Verificamos la contraseña usando la función 'verificar_usuario' que se encuentra en 'PYTHON/authentication/login.py'
        user = verificar_usuario(conn, correo, contrasena)
        
        # EN CASO DE EXITO
        
        #Compara que lo anterior no haya retornado 'None'
        if user:
            # Si el usuario es valido, se reinician los inentos fallidos y se pone en 'ACTIVO'
            cursor.execute("""UPDATE usuarios SET intentos_fallidos = 0, 
                              bloqueo_hasta = NULL, estado = 'ACTIVO' 
                              WHERE id_usuario = %s""", (user_data['id_usuario'],))
            
            # Guarda los datos en la tabla y cierra la coneccion con la BD
            conn.commit()
            conn.close()
            
            # login_user() es una funcion de flask que inicia la sesion del usuario.
            login_user(user)
            flash('Inicio de sesión exitoso', 'success')
            
            # Reedirigimos a su panel correspondiente
            if user.rol == 'NUTRIOLOGO':
                return redirect(url_for('dashboard_nutriologo'))
            return redirect(url_for('dashboard_paciente'))
        
        
        
        
        # EN CASO DE FALLO
        else:
            
            # Si se equivoco de contraseña, agrega 1 a sus intentos fallidos y los guarda en la variable
            nuevos_intentos = user_data['intentos_fallidos'] + 1
            
            # Declaramos variables
            bloqueo_hasta_time = None
            nuevo_estado = 'ACTIVO'
            
            # Verifica si los intentos son mayores o iguales a 5
            if nuevos_intentos >= 5:
                
                # En caso de que si, lo bloquea por 15 minutos (le suma 15 minutos al tiempo actual) y cambia su estado a 'BLOQUEADO'
                bloqueo_hasta_time = ahora + timedelta(minutes=15)
                nuevo_estado = 'BLOQUEADO'
                mensaje_final = 'Demasiados intentos. Cuenta bloqueada por 15 minutos.'
                
                # Si no, le muestra el mensaje de contraseña incorrecta
            else:
                mensaje_final = f'Contraseña incorrecta,\nTe quedan {5 - nuevos_intentos} intentos'
                
            # Actualiza tabla con un commit y cierra la coneccion con la BD    
            cursor.execute("""UPDATE usuarios SET intentos_fallidos = %s, 
                              bloqueo_hasta = %s, estado = %s 
                              WHERE correo = %s""", (nuevos_intentos, bloqueo_hasta_time, nuevo_estado, correo))
            conn.commit()
            conn.close()
            
            # Manda el mensaje y reedirige a el login
            flash(mensaje_final, 'error')
            return render_template('login.html', correo_enviado=correo)
        
    # =======Si no es POST solamente muestra el login=======    
    return render_template('login.html')

# ===========RUTA DE LOGOUT===========
@auth_bp.route('/logout')
def logout():
    
    # logout_user es de flask, lo desloguea
    logout_user()
    
    #Reedirige a login
    return redirect(url_for('auth.login'))





# ===========ENVIO DE CORREO PARA RECUPERACION DE CONTRASEÑA===========
# RUTA SOLICITAR RECUPERACION
@auth_bp.route('/solicitar-recuperacion', methods=['GET', 'POST'])
def solicitar_recuperacion():
    if request.method == 'POST':
        correo = request.form.get('correo')
        
        # Conecta, ejecuta, obtiene y cierra 
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id_usuario FROM usuarios WHERE correo = %s", (correo,))
        usuario = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if usuario:
            # Generar token seguro usando la secret_key de la app
            s = URLSafeTimedSerializer(current_app.secret_key)
            
            # Codificamos el correo dentro del token
            token = s.dumps(correo, salt='recuperacion-pass')
            
            # Crear enlace absoluto (_external=True) para enviarlo por correo
            enlace = url_for('auth.restablecer_contrasena', token=token, _external=True)
            
            # Enviar el correo
            enviado = enviar_correo_recuperacion(correo, enlace)
            
            if enviado:
                flash('Se ha enviado un enlace de recuperación a su correo electrónico', 'success')
            else:
                flash('Hubo un error al intentar enviar el correo. Intente más tarde.', 'error')
        else:
            flash('El correo electrónico no se encuentra registrado', 'error')
            
        return redirect(url_for('auth.solicitar_recuperacion'))
        
    return render_template('recuperacion_contrasena/solicitar_correo.html')



# RUTA VALIDAR ENLACES
@auth_bp.route('/restablecer-contrasena/<token>', methods=['GET', 'POST'])
def restablecer_contrasena(token):
    s = URLSafeTimedSerializer(current_app.secret_key)
    
    try:
        # Intentamos decodificar el token. max_age=1800 significa que expira en 30 minutos (1800 segs)
        correo = s.loads(token, salt='recuperacion-pass', max_age=1800)
    except SignatureExpired:
        flash('El enlace de recuperación ha expirado. Por favor, solicita uno nuevo.', 'error')
        return redirect(url_for('auth.solicitar_recuperacion'))
    except BadSignature:
        flash('El enlace de recuperación es inválido.', 'error')
        return redirect(url_for('auth.solicitar_recuperacion'))
        
    # Si llegamos aquí, el token es válido y no ha expirado. Procedemos.
    if request.method == 'POST':
        nueva_contrasena = request.form.get('nueva_contrasena')
        confirmar_contrasena = request.form.get('confirmar_contrasena')
        
        if nueva_contrasena != confirmar_contrasena:
            flash('Las contraseñas no coinciden.', 'error')
            return redirect(url_for('auth.restablecer_contrasena', token=token))
            
        # Encriptar nueva contraseña y actualizar en DB
        password_hash = generate_password_hash(nueva_contrasena).decode('utf-8')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET contrasena = %s WHERE correo = %s", (password_hash, correo))
        conn.commit()
        cursor.close()
        conn.close()
        
        # Mensaje
        flash('La contraseña se actualizó correctamente', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('recuperacion_contrasena/restablecer_contrasena.html')


# Metodos

def enviar_correo_recuperacion(destinatario, enlace):
    remitente = "dla140505@gmail.com"
    password = "uyco hlrh pusv euqc"
    
    mensaje = MIMEMultipart()
    mensaje['From'] = remitente
    mensaje['To'] = destinatario
    mensaje['Subject'] = "Recuperación de contraseña - Erazo System"
    
    cuerpo = f"""
    Hola,
    
    Has solicitado restablecer tu contraseña. Haz clic en el siguiente enlace para crear una nueva (este enlace expira en 30 minutos):
    
    {enlace}
    
    Si no solicitaste este cambio, ignora este correo.
    """
    mensaje.attach(MIMEText(cuerpo, 'plain'))
    
    try:
        servidor = smtplib.SMTP('smtp.gmail.com', 587)
        servidor.starttls()
        servidor.login(remitente, password)
        servidor.send_message(mensaje)
        servidor.quit()
        return True
    except Exception as e:
        print(f"Error enviando correo: {e}")
        return False


# Chatgpt es un pndjo (Copia y pega esta verdad) (♡•ω•♡)