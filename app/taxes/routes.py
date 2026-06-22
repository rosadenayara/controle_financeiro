"""
app/taxes/routes.py
Blueprint do painel de impostos.
"""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.taxes.calculos import (
    resumo_clt, resumo_pj_simples, resumo_mei,
    calcular_ir_renda_fixa, calcular_ir_acoes,
    calcular_ir_dolar, comparar_investimentos,
)

taxes_bp = Blueprint("taxes", __name__, url_prefix="/impostos")


@taxes_bp.route("/")
@login_required
def painel():
    """Página principal do painel de impostos."""
    return render_template("taxes/painel.html")


@taxes_bp.route("/api/salario", methods=["POST"])
@login_required
def api_salario():
    """Calcula descontos de salário conforme regime escolhido."""
    data = request.get_json()
    regime = data.get("regime", "clt")
    
    if regime == "clt":
        bruto = float(data.get("salario_bruto", 0))
        return jsonify(resumo_clt(bruto))

    elif regime == "pj":
        fat = float(data.get("faturamento_mensal", 0))
        pl  = float(data.get("pro_labore", 0))
        return jsonify(resumo_pj_simples(fat, pl))

    elif regime == "mei":
        fat = float(data.get("faturamento_mensal", 0))
        return jsonify(resumo_mei(fat))

    return jsonify({"erro": "Regime inválido"}), 400


@taxes_bp.route("/api/investimento", methods=["POST"])
@login_required
def api_investimento():
    """Calcula IR sobre diferentes tipos de investimento."""
    data = request.get_json()
    tipo = data.get("tipo")

    if tipo == "renda_fixa":
        rendimento = float(data.get("rendimento", 0))
        dias = int(data.get("dias", 365))
        return jsonify(calcular_ir_renda_fixa(rendimento, dias))

    elif tipo == "acoes":
        lucro = float(data.get("lucro", 0))
        modalidade = data.get("modalidade", "swing")  # swing | day | fii
        return jsonify(calcular_ir_acoes(lucro, modalidade))

    elif tipo == "dolar":
        lucro = float(data.get("lucro_reais", 0))
        return jsonify(calcular_ir_dolar(lucro))

    return jsonify({"erro": "Tipo inválido"}), 400


@taxes_bp.route("/api/comparar", methods=["POST"])
@login_required
def api_comparar():
    """Compara rendimento líquido de CDB, LCI, Tesouro e Poupança."""
    data = request.get_json()
    valor     = float(data.get("valor", 1000))
    prazo     = int(data.get("prazo_dias", 365))
    cdi_anual = float(data.get("cdi_anual", 0.1065))
    return jsonify(comparar_investimentos(valor, prazo, cdi_anual))