from app import create_app
import os

app = create_app()

if __name__ == '__main__':
    # host='0.0.0.0' permite acesso via IP na rede local
    # Necessário para testar roteamento por domínio real
    app.run(
        debug=os.environ.get('FLASK_DEBUG', 'true').lower() == 'true',
        host=os.environ.get('FLASK_HOST', '127.0.0.1'),
        port=int(os.environ.get('FLASK_PORT', 5000)),
    )