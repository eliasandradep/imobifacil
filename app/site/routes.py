from flask import Blueprint, render_template, g, abort, request
from ..models import Imovel, TipoImovel

site_bp = Blueprint('site', __name__)

@site_bp.route('/')
def index():
    if not g.imobiliaria:
        return "Imobiliária não configurada para este domínio.", 404

    # ── Filtros de busca ────────────────────────────────────────
    finalidade = request.args.get('finalidade', '').strip()
    tipo_id    = request.args.get('tipo_id',    '', type=str)
    cidade     = request.args.get('cidade',     '').strip()
    preco_max  = request.args.get('preco_max',  '', type=str)
    quartos    = request.args.get('quartos',    '', type=str)

    query = Imovel.query.filter_by(imobiliaria_id=g.imobiliaria.id)

    if finalidade:
        query = query.filter(Imovel.finalidade == finalidade)
    if tipo_id:
        query = query.filter(Imovel.tipo_id == int(tipo_id))
    if cidade:
        like = f"%{cidade}%"
        from ..models import db
        query = query.filter(
            db.or_(Imovel.cidade.ilike(like), Imovel.bairro.ilike(like))
        )
    if preco_max:
        query = query.filter(Imovel.preco <= float(preco_max))
    if quartos:
        query = query.filter(Imovel.quartos >= int(quartos))

    page       = request.args.get('page', 1, type=int)
    per_page   = int(g.imobiliaria.layout_grid or 3) * 3   # linhas fixas: 3
    pagination = (query.order_by(Imovel.id.desc())
                       .paginate(page=page, per_page=per_page, error_out=False))

    tipos = TipoImovel.query.filter_by(imobiliaria_id=g.imobiliaria.id).all()

    filtros_ativos = any([finalidade, tipo_id, cidade, preco_max, quartos])

    return render_template('site/index.html',
                           imoveis=pagination.items,
                           pagination=pagination,
                           tipos=tipos,
                           filtros=dict(finalidade=finalidade, tipo_id=tipo_id,
                                        cidade=cidade, preco_max=preco_max,
                                        quartos=quartos),
                           filtros_ativos=filtros_ativos)

@site_bp.route('/imovel/<int:id>')
def detalhes(id):
    imovel = Imovel.query.filter_by(id=id, imobiliaria_id=g.imobiliaria.id).first_or_404()
    return render_template('site/detalhes.html', imovel=imovel)
