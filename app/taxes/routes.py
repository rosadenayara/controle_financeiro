"""
app/taxes/routes.py
Blueprint do painel de impostos.
"""
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from app.taxes.calculos import (
    resumo_clt, resumo_pj_simples, resumo_mei,
    calcular_ir_renda_fixa, calcular_iof,
    calcular_ir_acoes, calcular_ir_dolar,
    comparar_investimentos,
)
from app.models import Salary, MarketData

taxes_bp = Blueprint("taxes", __name__, url_prefix="/impostos")


@taxes_bp.route("/")
@login_required
def painel():
    salario = Salary.query.filter_by(user_id=current_user.id).order_by(Salary.id.desc()).first()
    resultado_salario = None
    if salario:
        reg = (salario.regime or "CLT").upper()
        try:
            if reg == "CLT":
                resultado_salario = resumo_clt(salario.bruto)
            elif reg == "PJ":
                resultado_salario = resumo_pj_simples(salario.bruto, salario.pro_labore or 0)
            elif reg == "MEI":
                resultado_salario = resumo_mei(salario.bruto, salario.tipo_atividade or "comercio")
        except Exception:
            pass
    return render_template("taxes/painel_impostos.html",
                           salario=salario, resultado_salario=resultado_salario)


@taxes_bp.route("/api/salario", methods=["POST"])
@login_required
def api_salario():
    data = request.get_json(silent=True) or {}
    regime = data.get("regime", "clt")

    try:
        if regime == "clt":
            bruto = float(data.get("salario_bruto", 0))
            return jsonify(resumo_clt(bruto))
        elif regime == "pj":
            fat = float(data.get("faturamento_mensal", 0))
            pl  = float(data.get("pro_labore", 0))
            return jsonify(resumo_pj_simples(fat, pl))
        elif regime == "mei":
            fat = float(data.get("faturamento_mensal", 0))
            tipo = data.get("tipo_atividade", "comercio")
            return jsonify(resumo_mei(fat, tipo))
        return jsonify({"erro": "Regime inválido"}), 400
    except (ValueError, TypeError) as e:
        return jsonify({"erro": f"Dados inválidos: {e}"}), 422


@taxes_bp.route("/api/investimento", methods=["POST"])
@login_required
def api_investimento():
    data = request.get_json(silent=True) or {}
    tipo = data.get("tipo")

    try:
        if tipo == "renda_fixa":
            rendimento = float(data.get("rendimento", 0))
            dias = int(data.get("dias", 365))
            iof = calcular_iof(rendimento, dias)
            resultado = calcular_ir_renda_fixa(rendimento - iof, dias)
            resultado["iof"] = iof
            return jsonify(resultado)
        elif tipo == "acoes":
            lucro = float(data.get("lucro", 0))
            modalidade = data.get("modalidade", "swing")
            valor_venda = data.get("valor_venda_mensal")
            valor_venda = float(valor_venda) if valor_venda is not None else None
            return jsonify(calcular_ir_acoes(lucro, modalidade, valor_venda))
        elif tipo == "dolar":
            lucro = float(data.get("lucro_reais", 0))
            return jsonify(calcular_ir_dolar(lucro))
        return jsonify({"erro": "Tipo inválido"}), 400
    except (ValueError, TypeError) as e:
        return jsonify({"erro": f"Dados inválidos: {e}"}), 422


@taxes_bp.route("/api/comparar", methods=["POST"])
@login_required
def api_comparar():
    data = request.get_json(silent=True) or {}
    try:
        valor     = float(data.get("valor", 1000))
        prazo     = int(data.get("prazo_dias", 365))
        cdi_anual = float(data.get("cdi_anual", 0.1065))
        return jsonify(comparar_investimentos(valor, prazo, cdi_anual))
    except (ValueError, TypeError) as e:
        return jsonify({"erro": f"Dados inválidos: {e}"}), 422


@taxes_bp.route("/api/mercado", methods=["GET"])
@login_required
def api_mercado():
    """Retorna os dados de mercado mais recentes de cada ticker."""
    from sqlalchemy import func
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
        .order_by(MarketData.tipo, MarketData.ticker)
        .all()
    )
    return jsonify([{
        "ticker":        r.ticker,
        "nome":          r.nome,
        "tipo":          r.tipo,
        "valor":         r.valor,
        "variacao_dia":  r.variacao_dia,
        "data":          r.data_referencia.isoformat(),
        "atualizado_em": r.atualizado_em.isoformat() if r.atualizado_em else None,
    } for r in registros])


@taxes_bp.route("/api/etl/executar", methods=["POST"])
@login_required
def api_etl_executar():
    """Dispara o pipeline ETL manualmente (admin/dev)."""
    from app.services.market_etl import executar_pipeline_etl
    resultado = executar_pipeline_etl(current_app._get_current_object())
    return jsonify(resultado)
