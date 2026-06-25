"""
app/taxes/calculos.py
Cálculos tributários brasileiros — tabelas 2025
Substitui e expande o services.py original.
"""

# ── TABELAS OFICIAIS 2025 ────────────────────────────────────────────────────

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
    # RBT12 estimado — o correto seria somar os últimos 12 meses reais
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


MEI_DAS = {
    "comercio":  76.90,
    "servicos":  80.90,
    "ambos":     81.90,
}
MEI_LIMITE_ANUAL = 144_900.00


def resumo_mei(faturamento_mensal: float, tipo_atividade: str = "comercio") -> dict:
    das = MEI_DAS.get(tipo_atividade, MEI_DAS["comercio"])
    limite_mensal = MEI_LIMITE_ANUAL / 12
    excede = faturamento_mensal > limite_mensal
    return {
        "regime": "MEI",
        "faturamento": faturamento_mensal,
        "tipo_atividade": tipo_atividade,
        "das_mensal": das,
        "liquido_estimado": round(faturamento_mensal - das, 2),
        "limite_mensal": round(limite_mensal, 2),
        "limite_anual": MEI_LIMITE_ANUAL,
        "excede_limite": excede,
        "alerta": "Faturamento acima do teto MEI (R$ 144.900/ano). Considere migrar para Simples Nacional." if excede else None,
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


def calcular_ir_acoes(lucro: float, tipo: str = "swing", valor_venda_mensal: float = None) -> dict:
    aliquotas = {"swing": 0.15, "day": 0.20, "fii": 0.20}
    aliq = aliquotas.get(tipo, 0.15)

    # PF: isenção para swing trade com vendas totais no mês até R$ 20.000
    isento = (
        tipo == "swing"
        and valor_venda_mensal is not None
        and valor_venda_mensal <= 20_000.00
        and lucro > 0
    )

    ir = 0.0 if (lucro <= 0 or isento) else round(lucro * aliq, 2)
    return {
        "lucro": lucro,
        "tipo": tipo,
        "aliquota": aliq * 100,
        "isento": isento,
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


def _item_investimento(tipo: str, valor: float, anos: float, prazo_dias: int,
                        cdi_anual: float, ipca_anual: float, **kw) -> dict:
    """Calcula rendimento de um único tipo de investimento."""

    def _rf(r_bruto):
        iof = calcular_iof(r_bruto, prazo_dias)
        base = r_bruto - iof
        ir  = calcular_ir_renda_fixa(base, prazo_dias)
        return r_bruto, iof, ir.get("ir", 0), round(base - ir.get("ir", 0), 2)

    if tipo == "cdb":
        pct = kw.get("pct_cdi", 1.0)
        r = valor * ((1 + cdi_anual * pct) ** anos - 1)
        r, iof, ir, liq = _rf(r)
        return {"nome": f"CDB {pct*100:.0f}% CDI", "tipo": "Renda Fixa",
                "rendimento_bruto": round(r,2), "iof": iof, "ir": ir,
                "rendimento_liquido": liq, "isento_ir": False, "estimativa": False}

    if tipo == "lci":
        pct = kw.get("pct_cdi", 0.90)
        r = round(valor * ((1 + cdi_anual * pct) ** anos - 1), 2)
        return {"nome": f"LCI/LCA {pct*100:.0f}% CDI", "tipo": "Renda Fixa Isenta",
                "rendimento_bruto": r, "iof": 0, "ir": 0,
                "rendimento_liquido": r, "isento_ir": True, "estimativa": False}

    if tipo == "tesouro_selic":
        r = valor * ((1 + cdi_anual) ** anos - 1)
        r, iof, ir, liq = _rf(r)
        return {"nome": "Tesouro Selic", "tipo": "Título Público",
                "rendimento_bruto": round(r,2), "iof": iof, "ir": ir,
                "rendimento_liquido": liq, "isento_ir": False, "estimativa": False}

    if tipo == "tesouro_ipca":
        spread = kw.get("spread", 0.06)
        ipca   = kw.get("ipca_anual", ipca_anual)
        ret    = (1 + ipca) * (1 + spread) - 1
        r = valor * ((1 + ret) ** anos - 1)
        r, iof, ir, liq = _rf(r)
        return {"nome": f"Tesouro IPCA+ {spread*100:.1f}%", "tipo": "Título Público",
                "rendimento_bruto": round(r,2), "iof": iof, "ir": ir,
                "rendimento_liquido": liq, "isento_ir": False, "estimativa": True}

    if tipo == "poupanca":
        r = round(valor * ((1 + cdi_anual * 0.70) ** anos - 1), 2)
        return {"nome": "Poupança", "tipo": "Poupança",
                "rendimento_bruto": r, "iof": 0, "ir": 0,
                "rendimento_liquido": r, "isento_ir": True, "estimativa": False}

    if tipo == "bolsa":
        ret = kw.get("retorno_anual", 0.12)
        r   = round(valor * ((1 + ret) ** anos - 1), 2)
        ir  = round(r * 0.15, 2) if r > 0 else 0.0
        return {"nome": "Bolsa (IBOVESPA)", "tipo": "Renda Variável",
                "rendimento_bruto": r, "iof": 0, "ir": ir,
                "rendimento_liquido": round(r - ir, 2), "isento_ir": False, "estimativa": True}

    if tipo == "fii":
        ret = kw.get("retorno_anual", 0.08)
        r   = round(valor * ((1 + ret) ** anos - 1), 2)
        # Rendimentos de FII distribuídos são isentos para PF; ganho de capital 20%
        # Aqui tratamos como rendimento distribuído (isento)
        return {"nome": "FII (rendimento)", "tipo": "Renda Variável",
                "rendimento_bruto": r, "iof": 0, "ir": 0,
                "rendimento_liquido": r, "isento_ir": True, "estimativa": True}

    return None


def comparar_investimentos(
    valor: float,
    prazo_dias: int,
    cdi_anual: float = 0.1065,
    retorno_bolsa_anual: float = None,   # mantido para compatibilidade
    investimentos: list = None,           # lista flexível: [{tipo, **params}]
    ipca_anual: float = 0.06,
) -> list:
    """Compara investimentos pelo rendimento líquido.

    Modo flexível: passe `investimentos` como lista de dicts com chave `tipo`.
    Modo legado (sem `investimentos`): retorna conjunto padrão + bolsa opcional.
    """
    anos = prazo_dias / 365
    kw_base = dict(valor=valor, anos=anos, prazo_dias=prazo_dias, cdi_anual=cdi_anual)

    if investimentos is not None:
        resultados = []
        for inv in [dict(i) for i in investimentos]:
            tipo = inv.pop("tipo")
            # ipca_anual do item tem prioridade sobre o parâmetro base
            item_ipca = inv.pop("ipca_anual", ipca_anual)
            resultados.append(
                _item_investimento(tipo, ipca_anual=item_ipca, **kw_base, **inv)
            )
    else:
        # Conjunto padrão (legado)
        resultados = [
            _item_investimento("cdb",           ipca_anual=ipca_anual, **kw_base, pct_cdi=1.0),
            _item_investimento("lci",           ipca_anual=ipca_anual, **kw_base, pct_cdi=0.90),
            _item_investimento("tesouro_selic", ipca_anual=ipca_anual, **kw_base),
            _item_investimento("poupanca",      ipca_anual=ipca_anual, **kw_base),
        ]
        if retorno_bolsa_anual is not None:
            resultados.append(
                _item_investimento("bolsa", ipca_anual=ipca_anual, **kw_base,
                                   retorno_anual=retorno_bolsa_anual)
            )

    resultados = [r for r in resultados if r is not None]
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


def simular_aportes(aporte_mensal: float, cdi_anual: float = 0.1065,
                    ipca_anual: float = 0.0600) -> list:
    """
    Projeção de patrimônio com aportes mensais em diferentes investimentos.
    Retorna lista de dicts com rendimento líquido para 1, 2, 5 e 10 anos.
    """
    prazos_anos = [1, 2, 5, 10]

    def fv(taxa_anual: float, anos: int) -> float:
        taxa_m = (1 + taxa_anual) ** (1 / 12) - 1
        n = anos * 12
        if taxa_m < 1e-10:
            return aporte_mensal * n
        return aporte_mensal * ((1 + taxa_m) ** n - 1) / taxa_m

    def aliq_ir(anos: int) -> float:
        dias = anos * 365
        if dias <= 180:  return 0.225
        if dias <= 360:  return 0.200
        if dias <= 720:  return 0.175
        return 0.150

    opcoes = [
        {"tipo": "CDB 100% CDI",          "taxa": cdi_anual,                          "isento": False},
        {"tipo": "LCI/LCA 92% CDI",       "taxa": cdi_anual * 0.92,                   "isento": True},
        {"tipo": "Tesouro Selic",          "taxa": cdi_anual,                          "isento": False},
        {"tipo": "Tesouro IPCA+ 6% a.a.", "taxa": (1 + ipca_anual) * (1.06) - 1,     "isento": False},
        {"tipo": "Poupança",              "taxa": min(cdi_anual * 0.70, 0.0617),      "isento": True},
        {"tipo": "Bolsa (12% a.a. est.)", "taxa": 0.12, "isento": False, "ir_fixo": 0.15},
        {"tipo": "FII (8% a.a. est.)",    "taxa": 0.08,                               "isento": True},
    ]

    resultado = []
    for op in opcoes:
        prazos = []
        for anos in prazos_anos:
            total = aporte_mensal * 12 * anos
            bruto = fv(op["taxa"], anos)
            rendimento = max(0.0, bruto - total)

            if op.get("isento"):
                ir = 0.0
            elif "ir_fixo" in op:
                ir = rendimento * op["ir_fixo"]
            else:
                ir = rendimento * aliq_ir(anos)

            liquido = bruto - ir
            prazos.append({
                "anos":          anos,
                "aportado":      round(total, 2),
                "bruto":         round(bruto, 2),
                "ir":            round(ir, 2),
                "liquido":       round(liquido, 2),
                "ganho_liquido": round(liquido - total, 2),
            })
        resultado.append({"tipo": op["tipo"], "isento": op.get("isento", False), "prazos": prazos})
    return resultado


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
