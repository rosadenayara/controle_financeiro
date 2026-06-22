"""Compatibilidade: reexporta funções de cálculo de `app.taxes.calculos`.

Os testes e alguns módulos antigos importam `app.salary.services`. Para evitar
duplicação, este módulo apenas exporta os utilitários relevantes.
"""
from app.taxes.calculos import calcular_inss, calcular_irrf

__all__ = ["calcular_inss", "calcular_irrf"]
