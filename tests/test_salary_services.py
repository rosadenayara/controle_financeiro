import unittest
# Importa as funções direto do seu módulo de serviços
from app.salary.services import calcular_inss, calcular_irrf

class TestLógicaImpostos(unittest.TestCase):

    def test_calculo_inss_primeira_faixa(self):
        """Testa se um salário de R$ 1.412,00 calcula o INSS corretamente (7.5%)"""
        bruto = 1412.00
        resultado_inss = calcular_inss(bruto)
        # 1412 * 0.075 = 105.90
        self.assertAlmostEqual(resultado_inss, 105.90, places=2)

    def test_irrf_isencao(self):
        """Testa se salários baixos ficam isentos de imposto de renda"""
        base_calculo = 2000.00
        resultado_irrf = calcular_irrf(base_calculo)
        self.assertEqual(resultado_irrf, 0.0)

if __name__ == '__main__':
    unittest.main()