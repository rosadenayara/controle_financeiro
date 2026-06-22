"""sync models: add missing columns to reflect `app.models` schema

Revision ID: b1a2c3d4e5f6
Revises: 7803b67ef5f1
Create Date: 2026-06-22 12:50:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b1a2c3d4e5f6'
down_revision = '7803b67ef5f1'
branch_labels = None
depends_on = None


def upgrade():
    # Use Postgres IF NOT EXISTS safely to avoid errors if columns already present
    op.execute("""
    ALTER TABLE users ADD COLUMN IF NOT EXISTS perfil_tributario VARCHAR(20) DEFAULT 'CLT';
    ALTER TABLE salaries ADD COLUMN IF NOT EXISTS inss DOUBLE PRECISION;
    ALTER TABLE salaries ADD COLUMN IF NOT EXISTS irrf DOUBLE PRECISION;
    ALTER TABLE salaries ADD COLUMN IF NOT EXISTS fgts DOUBLE PRECISION;
    ALTER TABLE salaries ADD COLUMN IF NOT EXISTS data_referencia DATE;
    ALTER TABLE salaries ADD COLUMN IF NOT EXISTS criado_em TIMESTAMP;

    ALTER TABLE incomes ADD COLUMN IF NOT EXISTS descricao VARCHAR(200);
    ALTER TABLE incomes ADD COLUMN IF NOT EXISTS data DATE;
    ALTER TABLE incomes ADD COLUMN IF NOT EXISTS criado_em TIMESTAMP;

    ALTER TABLE expenses ADD COLUMN IF NOT EXISTS descricao VARCHAR(200);
    ALTER TABLE expenses ADD COLUMN IF NOT EXISTS data DATE;
    ALTER TABLE expenses ADD COLUMN IF NOT EXISTS criado_em TIMESTAMP;

    ALTER TABLE goals ADD COLUMN IF NOT EXISTS data_limite DATE;
    ALTER TABLE goals ADD COLUMN IF NOT EXISTS concluida BOOLEAN DEFAULT FALSE;
    ALTER TABLE goals ADD COLUMN IF NOT EXISTS criado_em TIMESTAMP;

    ALTER TABLE market_data ADD COLUMN IF NOT EXISTS nome VARCHAR(100);
    ALTER TABLE market_data ADD COLUMN IF NOT EXISTS variacao_dia DOUBLE PRECISION;

    ALTER TABLE tax_profiles ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMP;
    """)


def downgrade():
    op.execute("""
    ALTER TABLE users DROP COLUMN IF EXISTS perfil_tributario;
    ALTER TABLE salaries DROP COLUMN IF EXISTS inss;
    ALTER TABLE salaries DROP COLUMN IF EXISTS irrf;
    ALTER TABLE salaries DROP COLUMN IF EXISTS fgts;
    ALTER TABLE salaries DROP COLUMN IF EXISTS data_referencia;
    ALTER TABLE salaries DROP COLUMN IF EXISTS criado_em;

    ALTER TABLE incomes DROP COLUMN IF EXISTS descricao;
    ALTER TABLE incomes DROP COLUMN IF EXISTS data;
    ALTER TABLE incomes DROP COLUMN IF EXISTS criado_em;

    ALTER TABLE expenses DROP COLUMN IF EXISTS descricao;
    ALTER TABLE expenses DROP COLUMN IF EXISTS data;
    ALTER TABLE expenses DROP COLUMN IF EXISTS criado_em;

    ALTER TABLE goals DROP COLUMN IF EXISTS data_limite;
    ALTER TABLE goals DROP COLUMN IF EXISTS concluida;
    ALTER TABLE goals DROP COLUMN IF EXISTS criado_em;

    ALTER TABLE market_data DROP COLUMN IF EXISTS nome;
    ALTER TABLE market_data DROP COLUMN IF EXISTS variacao_dia;

    ALTER TABLE tax_profiles DROP COLUMN IF EXISTS atualizado_em;
    """)
