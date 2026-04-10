from datetime import date
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from ..models import Pessoa, TelefonePessoa, Lead, TIPOS_PESSOA, TIPOS_TELEFONE, db

pessoas_bp = Blueprint('pessoas', __name__)


def _pessoa_da_imob(id):
    """Retorna a pessoa garantindo que pertence à imobiliária do usuário logado."""
    return Pessoa.query.filter_by(
        id=id, imobiliaria_id=current_user.imobiliaria_id
    ).first_or_404()


def _salvar_telefones(pessoa, form):
    TelefonePessoa.query.filter_by(pessoa_id=pessoa.id).delete()
    for tipo, numero in zip(form.getlist('tel_tipo[]'), form.getlist('tel_numero[]')):
        numero = numero.strip()
        if numero:
            db.session.add(TelefonePessoa(pessoa_id=pessoa.id, tipo=tipo or 'Celular', numero=numero))


def _campos_pessoa(form):
    """Extrai do form todos os campos da Pessoa (exceto nome/tipo que são obrigatórios)."""
    raw_nasc = form.get('data_nascimento', '').strip()
    try:
        data_nasc = date.fromisoformat(raw_nasc) if raw_nasc else None
    except ValueError:
        data_nasc = None
    return dict(
        documento      = form.get('documento', '').strip() or None,
        email          = form.get('email', '').strip() or None,
        data_nascimento= data_nasc,
        cep            = form.get('cep', '').strip() or None,
        logradouro     = form.get('logradouro', '').strip() or None,
        numero         = form.get('numero_end', '').strip() or None,
        complemento    = form.get('complemento', '').strip() or None,
        bairro         = form.get('bairro', '').strip() or None,
        cidade         = form.get('cidade', '').strip() or None,
        estado         = form.get('estado', '').strip() or None,
        observacoes    = form.get('observacoes', '').strip() or None,
    )


# ── LISTAGEM ──────────────────────────────────────────────────────────────────

@pessoas_bp.route('/')
@login_required
def listar_pessoas():
    imob_id = current_user.imobiliaria_id
    tipo_f  = request.args.get('tipo', '')
    busca   = request.args.get('busca', '').strip()

    query = Pessoa.query.filter_by(imobiliaria_id=imob_id)

    if tipo_f:
        query = query.filter(Pessoa.tipo == tipo_f)
    if busca:
        like = f'%{busca}%'
        query = query.filter(
            db.or_(
                Pessoa.nome.ilike(like),
                Pessoa.email.ilike(like),
                Pessoa.documento.ilike(like),
            )
        )

    page       = request.args.get('page', 1, type=int)
    pagination = query.order_by(Pessoa.nome).paginate(page=page, per_page=20, error_out=False)

    # Contagem por tipo para os badges do filtro
    contagem = {t: Pessoa.query.filter_by(imobiliaria_id=imob_id, tipo=t).count()
                for t in TIPOS_PESSOA}

    return render_template('admin/pessoas/listar.html',
                           pessoas=pagination.items,
                           pagination=pagination,
                           tipos=TIPOS_PESSOA,
                           contagem=contagem,
                           tipo_f=tipo_f,
                           busca=busca)


# ── NOVA PESSOA ───────────────────────────────────────────────────────────────

@pessoas_bp.route('/nova', methods=['GET', 'POST'])
@login_required
def nova_pessoa():
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        if not nome:
            flash('O nome é obrigatório.', 'warning')
            return render_template('admin/pessoas/form.html',
                                   pessoa=None, tipos=TIPOS_PESSOA,
                                   tipos_tel=TIPOS_TELEFONE)

        pessoa = Pessoa(
            imobiliaria_id=current_user.imobiliaria_id,
            tipo=request.form.get('tipo', 'Cliente'),
            nome=nome,
            **_campos_pessoa(request.form),
        )
        db.session.add(pessoa)
        db.session.flush()
        _salvar_telefones(pessoa, request.form)
        db.session.commit()
        flash(f'Pessoa "{pessoa.nome}" cadastrada com sucesso!', 'success')
        return redirect(url_for('pessoas.ver_pessoa', id=pessoa.id))

    return render_template('admin/pessoas/form.html',
                           pessoa=None, tipos=TIPOS_PESSOA,
                           tipos_tel=TIPOS_TELEFONE)


# ── DETALHE ───────────────────────────────────────────────────────────────────

@pessoas_bp.route('/<int:id>')
@login_required
def ver_pessoa(id):
    pessoa = _pessoa_da_imob(id)
    leads  = Lead.query.filter_by(
        pessoa_id=id, imobiliaria_id=current_user.imobiliaria_id
    ).order_by(Lead.data_contato.desc()).all()
    return render_template('admin/pessoas/ver.html',
                           pessoa=pessoa, leads=leads)


# ── EDITAR ────────────────────────────────────────────────────────────────────

@pessoas_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_pessoa(id):
    pessoa = _pessoa_da_imob(id)

    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        if not nome:
            flash('O nome é obrigatório.', 'warning')
            return render_template('admin/pessoas/form.html',
                                   pessoa=pessoa, tipos=TIPOS_PESSOA,
                                   tipos_tel=TIPOS_TELEFONE)

        pessoa.tipo = request.form.get('tipo', pessoa.tipo)
        pessoa.nome = nome
        for k, v in _campos_pessoa(request.form).items():
            setattr(pessoa, k, v)
        _salvar_telefones(pessoa, request.form)
        db.session.commit()
        flash('Dados atualizados com sucesso!', 'success')
        return redirect(url_for('pessoas.ver_pessoa', id=pessoa.id))

    return render_template('admin/pessoas/form.html',
                           pessoa=pessoa, tipos=TIPOS_PESSOA,
                           tipos_tel=TIPOS_TELEFONE)


# ── EXCLUIR ───────────────────────────────────────────────────────────────────

@pessoas_bp.route('/<int:id>/excluir', methods=['POST'])
@login_required
def excluir_pessoa(id):
    pessoa = _pessoa_da_imob(id)
    # Desvincula leads antes de excluir
    Lead.query.filter_by(pessoa_id=id).update({'pessoa_id': None})
    nome = pessoa.nome
    db.session.delete(pessoa)
    db.session.commit()
    flash(f'Pessoa "{nome}" excluída.', 'success')
    return redirect(url_for('pessoas.listar_pessoas'))


# ── BUSCA AJAX (para vínculo no form de lead) ─────────────────────────────────

@pessoas_bp.route('/buscar')
@login_required
def buscar_pessoas():
    q    = request.args.get('q', '').strip()
    like = f'%{q}%'
    resultados = Pessoa.query.filter(
        Pessoa.imobiliaria_id == current_user.imobiliaria_id,
        db.or_(Pessoa.nome.ilike(like), Pessoa.documento.ilike(like))
    ).order_by(Pessoa.nome).limit(10).all()
    return jsonify([
        {'id': p.id, 'nome': p.nome, 'tipo': p.tipo,
         'telefone': p.telefones[0].numero if p.telefones else ''}
        for p in resultados
    ])


# ── CRIAR LEAD A PARTIR DA PESSOA ────────────────────────────────────────────

@pessoas_bp.route('/<int:id>/novo-lead', methods=['POST'])
@login_required
def novo_lead_da_pessoa(id):
    pessoa = _pessoa_da_imob(id)
    from datetime import datetime
    tel_principal = pessoa.telefones[0].numero if pessoa.telefones else ''
    lead = Lead(
        imobiliaria_id=current_user.imobiliaria_id,
        pessoa_id=pessoa.id,
        nome=pessoa.nome,
        telefone=tel_principal,
        email=pessoa.email or None,
        origem='Manual',
        status='Novo',
        data_contato=datetime.utcnow(),
    )
    db.session.add(lead)
    db.session.commit()
    flash(f'Lead criado para "{pessoa.nome}". Preencha os detalhes.', 'success')
    return redirect(url_for('leads.editar_lead', id=lead.id))


# ── VINCULAR / DESVINCULAR LEAD ───────────────────────────────────────────────

@pessoas_bp.route('/<int:pessoa_id>/vincular-lead/<int:lead_id>', methods=['POST'])
@login_required
def vincular_lead(pessoa_id, lead_id):
    _pessoa_da_imob(pessoa_id)
    lead = Lead.query.filter_by(
        id=lead_id, imobiliaria_id=current_user.imobiliaria_id
    ).first_or_404()
    lead.pessoa_id = pessoa_id
    db.session.commit()
    flash('Lead vinculado à pessoa.', 'success')
    return redirect(url_for('pessoas.ver_pessoa', id=pessoa_id))


@pessoas_bp.route('/<int:pessoa_id>/desvincular-lead/<int:lead_id>', methods=['POST'])
@login_required
def desvincular_lead(pessoa_id, lead_id):
    lead = Lead.query.filter_by(
        id=lead_id, imobiliaria_id=current_user.imobiliaria_id,
        pessoa_id=pessoa_id
    ).first_or_404()
    lead.pessoa_id = None
    db.session.commit()
    flash('Lead desvinculado.', 'success')
    return redirect(url_for('pessoas.ver_pessoa', id=pessoa_id))
