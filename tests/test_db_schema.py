import pytest
from sqlalchemy import create_engine, inspect, text
from config import Config


@pytest.fixture(scope="module")
def engine():
    return create_engine(Config.SQLALCHEMY_DATABASE_URI)


def test_tables_exist(engine):
    insp = inspect(engine)
    expected = {
        'users', 'salaries', 'incomes', 'expenses', 'goals', 'market_data', 'tax_profiles', 'alembic_version'
    }
    existing = set(insp.get_table_names())
    missing = expected - existing
    assert not missing, f"Tabelas faltando: {missing}"


def test_tables_empty(engine):
    with engine.connect() as conn:
        # `market_data` é populada pelo pipeline ETL usado em outros testes,
        # portanto não esperamos que esteja vazia. Verificamos as demais.
        for t in ['users', 'salaries', 'incomes', 'expenses', 'goals', 'tax_profiles']:
            res = conn.execute(text(f'SELECT count(*) FROM {t}'))
            assert res.scalar() == 0, f"Tabela {t} não está vazia"
