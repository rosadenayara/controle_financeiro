"""
app/investimentos/routes.py
Painel de investimentos: cotações, comparador, carteira pessoal e simulador de aportes.
"""
from datetime import datetime as dt
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import func
from app.models import MarketData
from app.extensions import db

inv_bp = Blueprint("investimentos", __name__, url_prefix="/investimentos")

# ── Tickers exibidos por seção ────────────────────────────────────────────────
_INDICADORES = ["SELIC", "CDI", "IPCA"]
_ATIVOS      = ["BOVA11.SA", "PETR4.SA", "VALE3.SA", "ITUB4.SA", "IVVB11.SA", "BRL=X"]

_TIPO_LABEL = {
    'cdb': 'CDB', 'lci': 'LCI/LCA',
    'tesouro_selic': 'Tesouro Selic', 'tesouro_ipca': 'Tesouro IPCA+',
    'poupanca': 'Poupança', 'acoes': 'Ações', 'fii': 'FII', 'etf': 'ETF',
}

_TIPO_COR = {
    'cdb': '#0d6efd', 'lci': '#198754',
    'tesouro_selic': '#6610f2', 'tesouro_ipca': '#d63384',
    'poupanca': '#0dcaf0', 'acoes': '#fd7e14', 'fii': '#20c997', 'etf': '#ffc107',
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ultimas_cotacoes() -> dict:
    subq = (
        MarketData.query
        .with_entities(MarketData.ticker, func.max(MarketData.data_referencia).label("ultima"))
        .group_by(MarketData.ticker)
        .subquery()
    )
    registros = (
        MarketData.query
        .join(subq, (MarketData.ticker == subq.c.ticker) &
                    (MarketData.data_referencia == subq.c.ultima))
        .all()
    )
    return {r.ticker: {
        "nome":         r.nome or r.ticker,
        "tipo":         r.tipo,
        "valor":        r.valor,
        "variacao_dia": r.variacao_dia,
        "data":         r.data_referencia.isoformat(),
    } for r in registros}


def _cdi_anual(cotacoes: dict) -> float:
    cdi_diario = cotacoes.get("CDI", {}).get("valor")
    if cdi_diario:
        return round((1 + cdi_diario / 100) ** 252 - 1, 6)
    return 0.1065


def _ipca_anual(cotacoes: dict) -> float:
    ipca_mensal = cotacoes.get("IPCA", {}).get("valor")
    if ipca_mensal:
        return round((1 + ipca_mensal / 100) ** 12 - 1, 6)
    return 0.0600


def _gerar_alertas(cotacoes: dict) -> list:
    alertas = []
    for ticker, d in cotacoes.items():
        var  = d.get("variacao_dia")
        nome = d.get("nome", ticker)
        if var is None:
            continue
        if var <= -5:
            alertas.append({"nivel": "danger",  "icone": "bi-exclamation-triangle-fill",
                             "msg": f"{nome} caiu {abs(var):.2f}% hoje — queda forte."})
        elif var <= -3:
            alertas.append({"nivel": "warning", "icone": "bi-arrow-down-circle-fill",
                             "msg": f"{nome} caiu {abs(var):.2f}% hoje."})
        elif var >= 5:
            alertas.append({"nivel": "success", "icone": "bi-arrow-up-circle-fill",
                             "msg": f"{nome} subiu {var:.2f}% hoje — alta expressiva."})
        elif var >= 3:
            alertas.append({"nivel": "info",    "icone": "bi-arrow-up-circle",
                             "msg": f"{nome} subiu {var:.2f}% hoje."})

    dolar = cotacoes.get("BRL=X", {}).get("valor")
    if dolar and dolar > 6.0:
        alertas.append({"nivel": "warning", "icone": "bi-currency-dollar",
                         "msg": f"Dólar acima de R$ 6 (atual: R$ {dolar:.2f}). Fique atento a importações e investimentos no exterior."})

    ipca = cotacoes.get("IPCA", {}).get("valor")
    if ipca and ipca > 0.5:
        alertas.append({"nivel": "warning", "icone": "bi-graph-up-arrow",
                         "msg": f"IPCA de {ipca:.2f}% no mês — inflação acima de 0,5%. Prefira ativos que superem o IPCA."})

    selic_diaria = cotacoes.get("SELIC", {}).get("valor")
    if selic_diaria:
        selic_anual = (1 + selic_diaria / 100) ** 252 - 1
        if selic_anual < 0.08:
            alertas.append({"nivel": "info", "icone": "bi-info-circle",
                             "msg": f"Selic anualizada em {selic_anual*100:.1f}% a.a. — renda fixa menos atrativa. Considere diversificar."})
    return alertas


def _calcular_posicao(item, cdi_anual: float, ipca_anual: float, cotacoes: dict) -> dict:
    from datetime import date
    hoje = date.today()
    dias = max(0, (hoje - item.data_entrada).days)
    anos = dias / 365.25
    v0   = item.valor_investido

    if item.tipo == 'cdb':
        taxa = cdi_anual * (item.pct_cdi or 1.0)
        valor_atual = v0 * (1 + taxa) ** anos
    elif item.tipo == 'lci':
        taxa = cdi_anual * (item.pct_cdi or 0.92)
        valor_atual = v0 * (1 + taxa) ** anos
    elif item.tipo == 'tesouro_selic':
        valor_atual = v0 * (1 + cdi_anual) ** anos
    elif item.tipo == 'tesouro_ipca':
        taxa = (1 + ipca_anual) * (1 + (item.spread_ipca or 0.06)) - 1
        valor_atual = v0 * (1 + taxa) ** anos
    elif item.tipo == 'poupanca':
        taxa = min(cdi_anual * 0.70, 0.0617)
        valor_atual = v0 * (1 + taxa) ** anos
    elif item.tipo in ('acoes', 'fii', 'etf'):
        if item.ticker and item.preco_entrada and item.ticker in cotacoes:
            valor_atual = v0 * (cotacoes[item.ticker]['valor'] / item.preco_entrada)
        else:
            valor_atual = v0
    else:
        valor_atual = v0

    rendimento   = valor_atual - v0
    rend_pct     = (rendimento / v0 * 100) if v0 > 0 else 0.0
    cdi_bench    = ((1 + cdi_anual) ** anos - 1) * 100

    return {
        'id':             item.id,
        'tipo':           item.tipo,
        'tipo_label':     _TIPO_LABEL.get(item.tipo, item.tipo.upper()),
        'cor':            _TIPO_COR.get(item.tipo, '#6c757d'),
        'nome':           item.nome or _TIPO_LABEL.get(item.tipo, item.tipo.upper()),
        'valor_investido': v0,
        'valor_atual':    round(valor_atual, 2),
        'rendimento':     round(rendimento, 2),
        'rendimento_pct': round(rend_pct, 2),
        'cdi_bench_pct':  round(cdi_bench, 2),
        'vs_cdi_pct':     round(rend_pct / cdi_bench * 100, 1) if cdi_bench > 0 else None,
        'dias':           dias,
        'data_entrada':   item.data_entrada.strftime('%d/%m/%Y'),
        'positivo':       rendimento >= 0,
    }


def _resumo_carteira(posicoes: list):
    if not posicoes:
        return None
    total_inv  = sum(p['valor_investido'] for p in posicoes)
    total_atu  = sum(p['valor_atual']     for p in posicoes)
    rend       = total_atu - total_inv
    rend_pct   = (rend / total_inv * 100) if total_inv > 0 else 0.0

    por_tipo = {}
    for p in posicoes:
        lbl = p['tipo_label']
        por_tipo.setdefault(lbl, {'valor': 0.0, 'cor': p['cor']})
        por_tipo[lbl]['valor'] += p['valor_atual']

    dist = sorted(
        [{'tipo': t, 'valor': round(v['valor'], 2), 'cor': v['cor'],
          'pct': round(v['valor'] / total_atu * 100, 1)}
         for t, v in por_tipo.items()],
        key=lambda x: -x['valor']
    ) if total_atu > 0 else []

    max_pct = max((d['pct'] for d in dist), default=0)
    return {
        'total_investido': round(total_inv, 2),
        'total_atual':     round(total_atu, 2),
        'rendimento':      round(rend, 2),
        'rendimento_pct':  round(rend_pct, 2),
        'distribuicao':    dist,
        'concentrado':     max_pct > 70,
        'concentrado_em':  dist[0]['tipo'] if dist and max_pct > 70 else None,
    }


# ── Rotas principais ──────────────────────────────────────────────────────────

@inv_bp.route("/")
@login_required
def painel():
    from app.models import PortfolioItem

    cotacoes   = _ultimas_cotacoes()
    alertas    = _gerar_alertas(cotacoes)
    cdi_anual  = _cdi_anual(cotacoes)
    ipca_anual = _ipca_anual(cotacoes)

    indicadores = {t: cotacoes[t] for t in _INDICADORES if t in cotacoes}
    ativos      = {t: cotacoes[t] for t in _ATIVOS      if t in cotacoes}
    sem_dados   = not cotacoes

    items    = PortfolioItem.query.filter_by(user_id=current_user.id).order_by(PortfolioItem.data_entrada).all()
    carteira = [_calcular_posicao(i, cdi_anual, ipca_anual, cotacoes) for i in items]

    return render_template(
        "investimentos/painel.html",
        indicadores=indicadores,
        ativos=ativos,
        alertas=alertas,
        cdi_anual_pct=round(cdi_anual * 100, 2),
        ipca_anual_pct=round(ipca_anual * 100, 2),
        sem_dados=sem_dados,
        carteira=carteira,
        resumo_carteira=_resumo_carteira(carteira),
    )


@inv_bp.route("/carteira")
@login_required
def carteira():
    from flask import redirect, url_for
    return redirect(url_for("investimentos.painel"))


# ── API: Comparador ───────────────────────────────────────────────────────────

@inv_bp.route("/api/comparar", methods=["POST"])
@login_required
def api_comparar():
    from app.taxes.calculos import comparar_investimentos

    data = request.get_json(silent=True) or {}
    try:
        valor      = float(data.get("valor", 10_000))
        prazo_dias = int(data.get("prazo_dias", 365))

        cdi_override = data.get("cdi_anual")
        if cdi_override is not None:
            cdi_anual = float(cdi_override) / 100
        else:
            cdi_anual = _cdi_anual(_ultimas_cotacoes())

        ipca_anual = float(data.get("ipca_anual", 6)) / 100

        investimentos_raw = data.get("investimentos")
        if investimentos_raw:
            investimentos = []
            for inv in investimentos_raw:
                item = {"tipo": inv["tipo"]}
                for k in ("pct_cdi", "retorno_anual", "spread", "ipca_anual"):
                    if k in inv:
                        item[k] = float(inv[k]) / 100
                investimentos.append(item)
            return jsonify(comparar_investimentos(valor, prazo_dias, cdi_anual,
                                                  investimentos=investimentos,
                                                  ipca_anual=ipca_anual))

        bolsa_raw = data.get("retorno_bolsa_anual")
        retorno_bolsa = float(bolsa_raw) / 100 if bolsa_raw is not None else None
        return jsonify(comparar_investimentos(valor, prazo_dias, cdi_anual, retorno_bolsa))
    except (ValueError, TypeError) as e:
        return jsonify({"erro": str(e)}), 422


# ── API: Carteira ─────────────────────────────────────────────────────────────

@inv_bp.route("/api/carteira/adicionar", methods=["POST"])
@login_required
def api_carteira_adicionar():
    from app.models import PortfolioItem

    d = request.get_json(silent=True) or {}
    try:
        item = PortfolioItem(
            user_id         = current_user.id,
            tipo            = d['tipo'],
            nome            = d.get('nome', '').strip() or None,
            valor_investido = float(d['valor_investido']),
            data_entrada    = dt.strptime(d['data_entrada'], '%Y-%m-%d').date(),
            pct_cdi         = float(d['pct_cdi'])     if d.get('pct_cdi')     else None,
            spread_ipca     = float(d['spread_ipca'])  if d.get('spread_ipca') else None,
            ticker          = d.get('ticker', '').strip().upper() or None,
            preco_entrada   = float(d['preco_entrada']) if d.get('preco_entrada') else None,
        )
        db.session.add(item)
        db.session.commit()
        return jsonify({'ok': True, 'id': item.id})
    except (KeyError, ValueError) as e:
        return jsonify({'ok': False, 'erro': str(e)}), 422


@inv_bp.route("/api/carteira/remover/<int:item_id>", methods=["POST"])
@login_required
def api_carteira_remover(item_id):
    from app.models import PortfolioItem

    item = PortfolioItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    return jsonify({'ok': True})


# ── API: Simulador ────────────────────────────────────────────────────────────

@inv_bp.route("/api/simular-aportes", methods=["POST"])
@login_required
def api_simular_aportes():
    from app.taxes.calculos import simular_aportes

    d = request.get_json(silent=True) or {}
    try:
        aporte   = float(d.get('aporte', 500))
        cdi_pct  = float(d.get('cdi_pct',  _cdi_anual(_ultimas_cotacoes()) * 100))
        ipca_pct = float(d.get('ipca_pct', _ipca_anual(_ultimas_cotacoes()) * 100))
        return jsonify(simular_aportes(aporte, cdi_pct / 100, ipca_pct / 100))
    except (ValueError, TypeError) as e:
        return jsonify({'erro': str(e)}), 422


# ── API: ETL ──────────────────────────────────────────────────────────────────

@inv_bp.route("/api/etl/executar", methods=["POST"])
@login_required
def api_etl_executar():
    from app.services.market_etl import executar_pipeline_etl
    resultado = executar_pipeline_etl(current_app._get_current_object())
    return jsonify(resultado)
