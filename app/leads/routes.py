from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from ..models import Lead, db

leads_bp = Blueprint('leads', __name__)


# ── Listagem ──────────────────────────────────────────────────────────────────

@leads_bp.route('/')
@login_required
def listar_leads():
    # Filtros via query string
    status_filtro = request.args.get('status', '')
    origem_filtro = request.args.get('origem', '')
    busca         = request.args.get('busca', '').strip()

    query = Lead.query.filter_by(imobiliaria_id=current_user.imobiliaria_id)

    if status_filtro:
        query = query.filter(Lead.status == status_filtro)
    if origem_filtro:
        query = query.filter(Lead.origem == origem_filtro)
    if busca:
        like = f"%{busca}%"
        query = query.filter(
            db.or_(
                Lead.nome.ilike(like),
                Lead.telefone.ilike(like),
                Lead.email.ilike(like)
            )
        )

    page       = request.args.get('page', 1, type=int)
    pagination = query.order_by(Lead.data_contato.desc()).paginate(page=page, per_page=15, error_out=False)
    leads      = pagination.items

    totais = {
        'total':       Lead.query.filter_by(imobiliaria_id=current_user.imobiliaria_id).count(),
        'novo':        Lead.query.filter_by(imobiliaria_id=current_user.imobiliaria_id, status='Novo').count(),
        'qualificado': Lead.query.filter_by(imobiliaria_id=current_user.imobiliaria_id, status='Qualificado').count(),
        'arquivado':   Lead.query.filter_by(imobiliaria_id=current_user.imobiliaria_id, status='Arquivado').count(),
    }

    return render_template(
        'admin/leads/listar_leads.html',
        leads=leads,
        pagination=pagination,
        totais=totais,
        status_filtro=status_filtro,
        origem_filtro=origem_filtro,
        busca=busca
    )


# ── Novo Lead (manual) ────────────────────────────────────────────────────────

@leads_bp.route('/novo', methods=['GET', 'POST'])
@login_required
def novo_lead():
    if request.method == 'POST':
        try:
            lead = Lead(
                imobiliaria_id=current_user.imobiliaria_id,
                nome=request.form.get('nome', '').strip(),
                telefone=request.form.get('telefone', '').strip(),
                email=request.form.get('email', '').strip() or None,
                origem=request.form.get('origem', 'Manual'),
                status='Novo',
                mensagem=request.form.get('mensagem', '').strip() or None,
                data_contato=datetime.utcnow()
            )
            db.session.add(lead)
            db.session.commit()
            flash(f"Lead '{lead.nome}' cadastrado com sucesso!", "success")
            return redirect(url_for('leads.listar_leads'))
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao cadastrar lead: {e}", "danger")

    return render_template('admin/leads/form_lead.html', lead=None)


# ── Editar Lead ───────────────────────────────────────────────────────────────

@leads_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_lead(id):
    lead = Lead.query.filter_by(
        id=id, imobiliaria_id=current_user.imobiliaria_id).first_or_404()

    if request.method == 'POST':
        try:
            lead.nome     = request.form.get('nome', '').strip()
            lead.telefone = request.form.get('telefone', '').strip()
            lead.email    = request.form.get('email', '').strip() or None
            lead.origem   = request.form.get('origem', lead.origem)
            lead.status   = request.form.get('status', lead.status)
            lead.mensagem = request.form.get('mensagem', '').strip() or None
            db.session.commit()
            flash(f"Lead '{lead.nome}' atualizado com sucesso!", "success")
            return redirect(url_for('leads.listar_leads'))
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao atualizar: {e}", "danger")

    return render_template('admin/leads/form_lead.html', lead=lead)


# ── Ações Rápidas (AJAX ou redirect) ─────────────────────────────────────────

@leads_bp.route('/qualificar/<int:id>', methods=['POST'])
@login_required
def qualificar_lead(id):
    lead = Lead.query.filter_by(
        id=id, imobiliaria_id=current_user.imobiliaria_id).first_or_404()
    lead.status = 'Qualificado'
    db.session.commit()
    if request.is_json:
        return jsonify({"ok": True, "status": lead.status})
    flash(f"Lead '{lead.nome}' qualificado!", "success")
    return redirect(url_for('leads.listar_leads'))


@leads_bp.route('/arquivar/<int:id>', methods=['POST'])
@login_required
def arquivar_lead(id):
    lead = Lead.query.filter_by(
        id=id, imobiliaria_id=current_user.imobiliaria_id).first_or_404()
    lead.status = 'Arquivado'
    db.session.commit()
    if request.is_json:
        return jsonify({"ok": True, "status": lead.status})
    flash(f"Lead '{lead.nome}' arquivado.", "info")
    return redirect(url_for('leads.listar_leads'))


@leads_bp.route('/excluir/<int:id>', methods=['POST'])
@login_required
def excluir_lead(id):
    lead = Lead.query.filter_by(
        id=id, imobiliaria_id=current_user.imobiliaria_id).first_or_404()
    try:
        nome = lead.nome
        db.session.delete(lead)
        db.session.commit()
        flash(f"Lead '{nome}' excluído.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao excluir: {e}", "danger")
    return redirect(url_for('leads.listar_leads'))


# ── API pública: receber leads de fontes externas ─────────────────────────────
# Será consumida futuramente pelo site, WhatsApp, Facebook, Instagram.
# Autenticação via header  X-Imobifacil-Token  (api_token da imobiliária).

@leads_bp.route('/api/receber', methods=['POST'])
def api_receber_lead():
    """
    Endpoint público para receber leads de integrações externas.
    Body JSON esperado:
    {
        "nome":     "João Silva",
        "telefone": "11999999999",
        "email":    "joao@email.com",       (opcional)
        "origem":   "Site" | "WhatsApp" | "Facebook" | "Instagram",
        "mensagem": "Tenho interesse no AP001"  (opcional)
    }
    Header obrigatório:
        X-Imobifacil-Token: <api_token da imobiliária>
    """
    from ..models import Imobiliaria

    token = request.headers.get('X-Imobifacil-Token')
    if not token:
        return jsonify({"erro": "Token ausente"}), 401

    imobiliaria = Imobiliaria.query.filter_by(api_token=token).first()
    if not imobiliaria:
        return jsonify({"erro": "Token inválido"}), 401

    dados = request.get_json(silent=True) or {}
    nome     = dados.get('nome', '').strip()
    telefone = dados.get('telefone', '').strip()

    if not nome or not telefone:
        return jsonify({"erro": "Campos 'nome' e 'telefone' são obrigatórios"}), 400

    origens_validas = {'Site', 'WhatsApp', 'Facebook', 'Instagram', 'Manual'}
    origem = dados.get('origem', 'Site')
    if origem not in origens_validas:
        origem = 'Site'

    try:
        lead = Lead(
            imobiliaria_id=imobiliaria.id,
            nome=nome,
            telefone=telefone,
            email=dados.get('email', '').strip() or None,
            origem=origem,
            status='Novo',
            mensagem=dados.get('mensagem', '').strip() or None,
            data_contato=datetime.utcnow()
        )
        db.session.add(lead)
        db.session.commit()
        return jsonify({"ok": True, "lead_id": lead.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": str(e)}), 500