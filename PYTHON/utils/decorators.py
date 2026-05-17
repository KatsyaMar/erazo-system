from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Verifica si el usuario está autenticado
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            # Verifica si tiene el rol necesario
            if current_user.rol != role:
                flash('No tienes permiso para acceder a esta sección.', 'error')
                
                # Redirecciona
                match current_user.rol:
                    case 'NUTRIOLOGO':
                        return redirect(url_for('dashboard_nutriologo'))
                    case 'PACIENTE':
                        return redirect(url_for('dashboard_paciente'))
                    case _:
                        return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator