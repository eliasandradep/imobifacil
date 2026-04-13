from flask import Blueprint, request, jsonify, g
from functools import wraps

api_bp = Blueprint('api', __name__)

# Decorador para validar o Token da SendPulse
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('X-Imobikey-Token')
        if not token:
            return jsonify({"erro": "Token ausente"}), 401
        
        from ..models import Imobiliaria
        imob = Imobiliaria.query.filter_by(api_token=token).first()
        if not imob:
            return jsonify({"erro": "Token inválido"}), 401
            
        # Armazena a imobiliária dona do token para usar na rota
        g.current_imob = imob
        return f(*args, **kwargs)
    return decorated

@api_bp.route('/status', methods=['GET'])
def status():
    return jsonify({"status": "ImobiKey API Online"}), 200

# Rota que a SendPulse chamará para cadastrar leads
@api_bp.route('/leads', methods=['POST'])
@token_required
def cadastrar_lead():
    dados = request.get_json()
    from ..models import Lead, db
    
    novo_lead = Lead(
        imobiliaria_id=g.current_imob.id,
        nome=dados.get('nome'),
        telefone=dados.get('telefone') or dados.get('whatsapp', ''),
        origem='WhatsApp'
    )
    
    db.session.add(novo_lead)
    db.session.commit()
    
    return jsonify({"mensagem": "Lead cadastrado com sucesso"}), 201