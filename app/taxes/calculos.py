"""
app/taxes/calculos.py
Cálculos tributários brasileiros — tabelas 2024
Substitui e expande o services.py original.
"""

# ── TABELAS OFICIAIS 2024 ────────────────────────────────────────────────────

FAIXAS_INSS = [
    (1_518.00,  0.075),
    (2_793.88,  0.090),
    (4_190.83,  0.120),
    (8_157.41,  0.140),
]

FAIXAS_IRPF = [
    (2_259.20,       0.000,   0.00),
    (2_826.65,       0.075, 169.44),
    (3_751.05,       0.150, 381.44),
    (4_664.68,       0.225, 662.77),
    (float("inf"),   0.275, 896.00),
]

DESCONTO_SIMPLIFICADO = 528.00
FGTS_ALIQUOTA = 0.08

IR_RENDA_FIXA = [
    (180,          0.225),
    (360,          0.200),
    (720,          0.175),
    (float("inf"), 0.150),
]

IOF_DIARIO = [
    100,96,93,90,86,83,80,76,73,70,
     66,63,60,56,53,50,46,43,40,36,
     33,30,26,23,20,16,13,10, 6, 3, 0
]

SIMPLES_ANEXO_III = [
    (180_000,      0.060,       0),
    (360_000,      0.112,   9_360),
    (720_000,      0.135,  17_640),
    (1_800_000,    0.160,  35_640),
    (3_600_000,    0.210, 125_640),
    (4_800_000,    0.330, 648_000),
]

FAIXAS_GANHO_CAPITAL = [
    (5_000_000,    0.150),
    (10_000_000,   0.175),
    (30_000_000,   0.200),
    (float("inf"), 0.225),
]


# ── PF / CLT ────────────────────────────────────────────────────────────────

def calcular_inss(salario_bruto: float) -> float:
    """INSS progressivo por faixas 2024 — sem teto fixo, calculado pelas faixas."""
    inss = 0.0
    limite_anterior = 0.0
    for limite, aliquota in FAIXAS_INSS:
        if salario_bruto <= limite_anterior:
            break
        base = min(salario_bruto, limite) - limite_anterior
        inss += base * aliquota
        limite_anterior = limite
        if salario_bruto <= limite:
            break
    return round(inss, 2)


def calcular_irpf(base: float) -> dict:
    """IRPF sobre base (bruto - INSS). Aplica desconto simplificado se vantajoso."""
    def _irpf_direto(b):
        for limite, aliq, ded in FAIXAS_IRPF:
            if b <= limite:
                return max(0.0, round(b * aliq - ded, 2))
        return 0.0

    irpf_normal = _irpf_direto(base)
    irpf_simplificado = _irpf_direto(max(0, base - DESCONTO_SIMPLIFICADO))
    irpf = min(irpf_normal, irpf_simplificado)
    efetiva = (irpf / base * 100) if base > 0 else 0.0

    return {
        "valor": irpf,
        "aliquota_efetiva": round(efetiva, 2),
        "usou_desconto_simplificado": irpf_simplificado < irpf_normal,
    }


def calcular_fgts(salario_bruto: float) -> float:
    return round(salario_bruto * FGTS_ALIQUOTA, 2)


def resumo_clt(salario_bruto: float) -> dict:
    inss = calcular_inss(salario_bruto)
    irpf_info = calcular_irpf(salario_bruto - inss)
    fgts = calcular_fgts(salario_bruto)
    total_desc = inss + irpf_info["valor"]
    liquido = salario_bruto - total_desc

    return {
        "regime": "CLT",
        "bruto": salario_bruto,
        "inss": inss,
        "irpf": irpf_info["valor"],
        "irpf_aliquota_efetiva": irpf_info["aliquota_efetiva"],
        "fgts": fgts,
        "liquido": round(liquido, 2),
        "total_descontos": round(total_desc, 2),
        "percentual_desconto": round(total_desc / salario_bruto * 100, 1) if salario_bruto else 0,
    }


# ── PJ ──────────────────────────────────────────────────────────────────────

def calcular_simples(receita_anual: float, faturamento_mensal: float) -> dict:
    for limite, aliq, ded in SIMPLES_ANEXO_III:
        if receita_anual <= limite:
            aliq_efetiva = (receita_anual * aliq - ded) / receita_anual
            return {
                "aliquota_nominal": round(aliq * 100, 1),
                "aliquota_efetiva": round(aliq_efetiva * 100, 2),
                "imposto_mensal": round(faturamento_mensal * aliq_efetiva, 2),
            }
    return {"aliquota_nominal": 0, "aliquota_efetiva": 0, "imposto_mensal": 0}


def resumo_pj_simples(faturamento_mensal: float, pro_labore: float) -> dict:
    receita_anual = faturamento_mensal * 12
    simples = calcular_simples(receita_anual, faturamento_mensal)
    inss_pl = calcular_inss(pro_labore)
    irpf_pl = calcular_irpf(pro_labore - inss_pl)
    total_imp = simples["imposto_mensal"] + inss_pl + irpf_pl["valor"]
    liquido = faturamento_mensal - total_imp

    return {
        "regime": "PJ Simples Nacional",
        "faturamento": faturamento_mensal,
        "simples_mensal": simples["imposto_mensal"],
        "aliquota_simples_efetiva": simples["aliquota_efetiva"],
        "pro_labore": pro_labore,
        "inss_pro_labore": inss_pl,
        "irpf_pro_labore": irpf_pl["valor"],
        "liquido_estimado": round(liquido, 2),
        "total_impostos": round(total_imp, 2),
        "percentual_desconto": round(total_imp / faturamento_mensal * 100, 1) if faturamento_mensal else 0,
    }


def resumo_mei(faturamento_mensal: float) -> dict:
    das = 79.90
    limite_mensal = 16_666.67
    excede = faturamento_mensal > limite_mensal
    return {
        "regime": "MEI",
        "faturamento": faturamento_mensal,
        "das_mensal": das,
        "liquido_estimado": round(faturamento_mensal - das, 2),
        "limite_mensal": limite_mensal,
        "excede_limite": excede,
        "alerta": "Faturamento acima do teto MEI (R$ 200k/ano). Considere migrar para Simples Nacional." if excede else None,
        "percentual_desconto": round(das / faturamento_mensal * 100, 1) if faturamento_mensal else 0,
    }


# ── INVESTIMENTOS ────────────────────────────────────────────────────────────

def calcular_ir_renda_fixa(rendimento: float, dias: int) -> dict:
    for limite, aliq in IR_RENDA_FIXA:
        if dias <= limite:
            ir = round(rendimento * aliq, 2)
            return {
                "rendimento_bruto": rendimento,
                "aliquota": aliq * 100,
                "ir": ir,
                "rendimento_liquido": round(rendimento - ir, 2),
            }
    return {}


def calcular_iof(rendimento: float, dias: int) -> float:
    if dias >= 30:
        return 0.0
    aliq = IOF_DIARIO[min(dias, 30)] / 100
    return round(rendimento * aliq, 2)


def calcular_ir_acoes(lucro: float, tipo: str = "swing") -> dict:
    aliquotas = {"swing": 0.15, "day": 0.20, "fii": 0.20}
    aliq = aliquotas.get(tipo, 0.15)
    ir = round(lucro * aliq, 2) if lucro > 0 else 0.0
    return {
        "lucro": lucro,
        "tipo": tipo,
        "aliquota": aliq * 100,
        "ir": ir,
        "lucro_liquido": round(lucro - ir, 2),
    }


def calcular_ir_dolar(lucro_reais: float) -> dict:
    if lucro_reais <= 0:
        return {"lucro": lucro_reais, "ir": 0, "aliquota": 0,
                "lucro_liquido": lucro_reais, "isento": True}
    for limite, aliq in FAIXAS_GANHO_CAPITAL:
        if lucro_reais <= limite:
            ir = round(lucro_reais * aliq, 2)
            return {
                "lucro": lucro_reais,
                "aliquota": aliq * 100,
                "ir": ir,
                "lucro_liquido": round(lucro_reais - ir, 2),
                "isento": False,
            }
    return {}


def comparar_investimentos(valor: float, prazo_dias: int, cdi_anual: float = 0.1065) -> list:
    """Compara CDB, LCI, Tesouro Selic e Poupança pelo rendimento líquido."""
    anos = prazo_dias / 365

    def bruto(pct_cdi):
        return valor * ((1 + cdi_anual * pct_cdi) ** anos - 1)

    resultados = []

    # CDB 100% CDI
    r = bruto(1.0)
    iof = calcular_iof(r, prazo_dias)
    r_pos_iof = r - iof
    ir = calcular_ir_renda_fixa(r_pos_iof, prazo_dias)
    resultados.append({
        "nome": "CDB 100% CDI",
        "tipo": "Renda Fixa",
        "rendimento_bruto": round(r, 2),
        "iof": iof,
        "ir": ir.get("ir", 0),
        "rendimento_liquido": round(r_pos_iof - ir.get("ir", 0), 2),
        "isento_ir": False,
    })

    # LCI/LCA 90% CDI (isenta IR e IOF)
    r = bruto(0.90)
    resultados.append({
        "nome": "LCI/LCA 90% CDI",
        "tipo": "Renda Fixa Isenta",
        "rendimento_bruto": round(r, 2),
        "iof": 0,
        "ir": 0,
        "rendimento_liquido": round(r, 2),
        "isento_ir": True,
    })

    # Tesouro Selic
    r = bruto(1.0)
    ir = calcular_ir_renda_fixa(r, prazo_dias)
    resultados.append({
        "nome": "Tesouro Selic",
        "tipo": "Título Público",
        "rendimento_bruto": round(r, 2),
        "iof": 0,
        "ir": ir.get("ir", 0),
        "rendimento_liquido": round(r - ir.get("ir", 0), 2),
        "isento_ir": False,
    })

    # Poupança ~70% Selic (isenta)
    r = bruto(0.70)
    resultados.append({
        "nome": "Poupança",
        "tipo": "Poupança",
        "rendimento_bruto": round(r, 2),
        "iof": 0,
        "ir": 0,
        "rendimento_liquido": round(r, 2),
        "isento_ir": True,
    })

    resultados.sort(key=lambda x: x["rendimento_liquido"], reverse=True)
    return resultados


# ── PREVISÃO FUTURA ──────────────────────────────────────────────────────────

def previsao_futura(saldo_mensal: float, meses: int = 6) -> list:
    """
    Projeção de acúmulo com base no saldo mensal atual.
    Retorna lista com valor acumulado mês a mês.
    """
    acumulado = 0.0
    previsao = []
    for i in range(1, meses + 1):
        acumulado += saldo_mensal
        previsao.append({
            "mes": i,
            "valor": round(acumulado, 2),
        })
    return previsao


def previsao_com_rendimento(saldo_mensal: float, meses: int = 6, cdi_anual: float = 0.1065) -> list:
    """
    Projeção realista: saldo mensal aplicado em renda fixa (CDI).
    Cada aporte rende até o fim do período.
    """
    cdi_mensal = (1 + cdi_anual) ** (1 / 12) - 1
    acumulado = 0.0
    previsao = []
    for i in range(1, meses + 1):
        acumulado = (acumulado + saldo_mensal) * (1 + cdi_mensal)
        previsao.append({
            "mes": i,
            "valor_sem_rendimento": round(saldo_mensal * i, 2),
            "valor_com_rendimento": round(acumulado, 2),
            "ganho_extra": round(acumulado - saldo_mensal * i, 2),
        })
    return previsao


# --- FUNÇÕES ADICIONAIS DE COMPATIBILIDADE ---------------------------------
def calcular_salario(bruto: float) -> dict:
    """Compatibilidade com a API antiga: retorna dicionário com bruto/liquido/etc."""
    # Por enquanto assume regime CLT e reutiliza resumo_clt
    return resumo_clt(bruto)


def calcular_irrf(salario_bruto: float) -> float:
    """Wrapper para manter a API antiga: retorna apenas o valor do IRRF (float)."""
    inss = calcular_inss(salario_bruto)
    irpf_info = calcular_irpf(salario_bruto - inss)
    return irpf_info.get("valor", 0.0)


def progresso_meta(goal) -> float:
    """Calcula progresso de uma `Goal` SQLAlchemy (compatível com uso em routes)

    Recebe o objeto `Goal` e retorna percentual (0-100) com uma casa decimal.
    """
    try:
        return round((goal.valor_atual / goal.valor_objetivo) * 100, 1) if goal.valor_objetivo else 0
    except Exception:
        return 0


# --- Backwards-compat / shims -------------------------------------------------
# Expor funções ETL presentes em `app.services.market_etl` para manter compatibilidade
try:
    from app.services.market_etl import (
        extrair_selic_bacen,
        extrair_preco_yfinance,
        executar_pipeline_etl,
    )
except Exception:
    # Se o módulo não estiver disponível em algum contexto, definimos shims leves.
    def extrair_selic_bacen():
        return None

    def extrair_preco_yfinance(ticker: str):
        return None

    def executar_pipeline_etl(app):
        return None
