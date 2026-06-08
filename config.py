import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Linha adicionada para puxar a chave do arquivo .env
    SECRET_KEY = os.getenv('SECRET_KEY', 'chave-padrao-caso-nao-encontre')