import unittest
from app import create_app, db
from app.models import MarketData
from app.taxes.calculos import extrair_selic_bacen, extrair_preco_yfinance, executar_pipeline_etl

class TestMarketETL(unittest.TestCase):

    def setUp(self):
        """Configura o ambiente de testes antes de cada método"""
        self.app = create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        """Limpa o contexto do app após a execução de cada teste"""
        self.app_context.pop()

    def test_01_extracao_selic_bacen(self):
        """Verifica se a API do Banco Central está respondendo com um número válido"""
        taxa = extrair_selic_bacen()
        self.assertIsNotNone(taxa, "A resposta da API do BACEN não deveria ser nula")
        self.assertIsInstance(taxa, float, "A taxa Selic deve ser um número do tipo float")
        self.assertTrue(taxa >= 0, "A taxa Selic não deve ser negativa")

    def test_02_extracao_yfinance(self):
        """Verifica se o yfinance consegue buscar a cotação do BOVA11"""
        preco = extrair_preco_yfinance("BOVA11.SA")
        self.assertIsNotNone(preco, "A resposta do yfinance não deveria ser nula")
        self.assertIsInstance(preco, float, "O preço do ativo deve ser do tipo float")
        self.assertTrue(preco > 0, "O preço de mercado precisa ser maior que zero")

    def test_03_execucao_pipeline_carga(self):
        """Testa se o pipeline ETL consegue rodar e inserir registros no banco de dados"""
        # Conta quantos registros existem antes de rodar o pipeline
        total_antes = MarketData.query.count()
        
        # Executa o pipeline completo que grava no banco
        executar_pipeline_etl(self.app)
        
        # Conta quantos registros existem após a execução
        total_depois = MarketData.query.count()
        
        # Verifica se novos dados foram adicionados ao PostgreSQL
        self.assertTrue(total_depois > total_antes, "O pipeline deveria ter adicionado novos registros à tabela")

if __name__ == '__main__':
    unittest.main()