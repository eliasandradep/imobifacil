import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'chave-secreta-muito-dificil'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///imobifacil.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_AS_ASCII = False  # Permite acentos no JSON da API

    # Domínio base da plataforma (sem http://).
    # Se definido, subdomínios no formato slug.BASE_DOMAIN são roteados automaticamente.
    # Exemplo: "imobifacil.com"  →  minha-imob.imobifacil.com
    BASE_DOMAIN = os.environ.get('BASE_DOMAIN', '').strip().lower().lstrip('.')

    # Hosts que pertencem à própria plataforma (não são sites de imobiliárias)
    PLATFORM_HOSTS = {'localhost', '127.0.0.1', '0.0.0.0'}