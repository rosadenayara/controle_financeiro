"""
app/services/market_etl.py
Pipeline ETL de dados de mercado — BACEN SGS + yfinance → PostgreSQL
"""
import logging
from datetime import datetime

import requests
import yfinance as yf

logger = logging.getLogger(__name__)

# ── Indicadores do BACEN (API SGS) ───────────────────────────────────────────
# código SGS → (ticker interno, tipo, nome legível)
INDICADORES_BACEN = {
    11:  ("SELIC", "INDICADOR", "Taxa Selic (% a.a.)"),
    12:  ("CDI",   "INDICADOR", "CDI (% a.a.)"),
    433: ("IPCA",  "INDICADOR", "IPCA - Variação Mensal (%)"),
}

# ── Ativos coletados via yfinance ─────────────────────────────────────────────
ATIVOS_YFINANCE = [
    ("BOVA11.SA", "FUNDO",  "ETF IBOVESPA"),
    ("PETR4.SA",  "ACAO",   "Petrobras PN"),
    ("VALE3.SA",  "ACAO",   "Vale"),
    ("ITUB4.SA",  "ACAO",   "Itaú Unibanco PN"),
    ("IVVB11.SA", "FUNDO",  "ETF S&P 500 (BRL)"),
    ("BRL=X",     "CAMBIO", "Dólar / Real"),
]

_BACEN_SGS = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados/ultimos/1?formato=json"


# ── Extração ──────────────────────────────────────────────────────────────────

def _extrair_indicador_bacen(codigo: int):
    """Chama a API SGS do BACEN. Retorna (valor, data_ref) ou (None, None)."""
    url = _BACEN_SGS.format(codigo=codigo)
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        dados = resp.json()
        if dados:
            ultimo = dados[-1]
            valor = float(str(ultimo["valor"]).replace(",", "."))
            data_ref = datetime.strptime(ultimo["data"], "%d/%m/%Y").date()
            return valor, data_ref
    except Exception as e:
        logger.warning("BACEN série %s: %s", codigo, e)
    return None, None


def _extrair_ativo_yfinance(ticker: str):
    """Busca cotação do yfinance. Retorna (preco, variacao_pct, data_ref) ou (None, None, None)."""
    try:
        hist = yf.Ticker(ticker).history(period="5d")
        if hist.empty:
            return None, None, None
        preco = float(hist["Close"].iloc[-1])
        variacao = None
        if len(hist) >= 2:
            anterior = float(hist["Close"].iloc[-2])
            if anterior:
                variacao = round((preco - anterior) / anterior * 100, 4)
        data_ref = hist.index[-1].date()
        return preco, variacao, data_ref
    except Exception as e:
        logger.warning("yfinance %s: %s", ticker, e)
    return None, None, None


# ── Carga (upsert) ────────────────────────────────────────────────────────────

def _upsert(ticker, tipo, nome, valor, data_ref, variacao=None):
    """Insere ou atualiza o registro (ticker + data_ref) no banco."""
    from app.extensions import db
    from app.models import MarketData

    registro = MarketData.query.filter_by(ticker=ticker, data_referencia=data_ref).first()
    if registro:
        registro.valor = valor
        registro.variacao_dia = variacao
        registro.atualizado_em = datetime.utcnow()
    else:
        db.session.add(MarketData(
            ticker=ticker,
            tipo=tipo,
            nome=nome,
            valor=valor,
            variacao_dia=variacao,
            data_referencia=data_ref,
        ))


# ── Job principal ─────────────────────────────────────────────────────────────

def executar_pipeline_etl(app):
    """Coleta todos os indicadores e ativos e persiste no banco (com upsert)."""
    with app.app_context():
        from app.extensions import db
        logger.info("▶ Pipeline ETL iniciado")
        erros = []

        for codigo, (ticker, tipo, nome) in INDICADORES_BACEN.items():
            valor, data_ref = _extrair_indicador_bacen(codigo)
            if valor is not None:
                _upsert(ticker, tipo, nome, valor, data_ref)
                logger.info("✔ %-8s  %.4f  (%s)", ticker, valor, data_ref)
            else:
                erros.append(ticker)
                logger.warning("✘ %s não coletado", ticker)

        for ticker, tipo, nome in ATIVOS_YFINANCE:
            preco, variacao, data_ref = _extrair_ativo_yfinance(ticker)
            if preco is not None:
                _upsert(ticker, tipo, nome, preco, data_ref, variacao)
                logger.info("✔ %-12s  R$ %.2f  var: %s%%", ticker, preco, variacao)
            else:
                erros.append(ticker)
                logger.warning("✘ %s não coletado", ticker)

        db.session.commit()
        logger.info("◼ ETL concluído — erros: %s", erros or "nenhum")
        return {"ok": True, "erros": erros}


# ── Funções públicas (compatibilidade com calculos.py) ────────────────────────

def extrair_selic_bacen() -> float | None:
    valor, _ = _extrair_indicador_bacen(11)
    return valor


def extrair_preco_yfinance(ticker: str) -> float | None:
    preco, _, _ = _extrair_ativo_yfinance(ticker)
    return preco
