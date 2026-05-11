# PYTHON/conection_db/db.py
import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    """
    Retorna una conexión a MySQL usando variables del .env
    """
    return mysql.connector.connect(
        host     = os.getenv('DB_HOST',     'localhost'),
        port     = int(os.getenv('DB_PORT', 3306)),
        user     = os.getenv('DB_USER',     'root'),
        password = os.getenv('DB_PASSWORD', ''),
        database = os.getenv('DB_NAME',     'erazo_system'),
    )
