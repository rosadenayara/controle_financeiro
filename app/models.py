from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

# Usar a instância compartilhada em `app.extensions` evita múltiplas instâncias
# de SQLAlchemy durante importações e testes.
from app.extensions import db


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    perfil_tributario = db.Column(db.String(20), default='CLT')  # CLT, PJ, MEI, CNPJ

    salarios = db.relationship('Salary', backref='user', lazy=True, cascade='all, delete-orphan')
    incomes = db.relationship('Income', backref='user', lazy=True, cascade='all, delete-orphan')
    expenses = db.relationship('Expense', backref='user', lazy=True, cascade='all, delete-orphan')
    goals = db.relationship('Goal', backref='user', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.email}>'


class Salary(db.Model):
    __tablename__ = 'salaries'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    regime = db.Column(db.String(10), nullable=False, default='CLT')  # CLT, PJ, MEI
    bruto = db.Column(db.Float, nullable=False)   # salário bruto (CLT) ou faturamento (PJ/MEI)
    liquido = db.Column(db.Float, nullable=False)
    inss = db.Column(db.Float)
    irrf = db.Column(db.Float)
    fgts = db.Column(db.Float)
    pro_labore = db.Column(db.Float)              # PJ: valor do pró-labore
    tipo_atividade = db.Column(db.String(20))     # MEI: comercio | servicos | ambos
    data_referencia = db.Column(db.Date, default=datetime.utcnow)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Salary {self.regime} bruto={self.bruto} liquido={self.liquido}>'


class Income(db.Model):
    __tablename__ = 'incomes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    categoria = db.Column(db.String(50))
    descricao = db.Column(db.String(200))
    data = db.Column(db.Date, default=datetime.utcnow)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Income {self.categoria}: {self.valor}>'


class Expense(db.Model):
    __tablename__ = 'expenses'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    categoria = db.Column(db.String(50))
    descricao = db.Column(db.String(200))
    data = db.Column(db.Date, default=datetime.utcnow)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Expense {self.categoria}: {self.valor}>'


class Goal(db.Model):
    __tablename__ = 'goals'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    valor_objetivo = db.Column(db.Float, nullable=False)
    valor_atual = db.Column(db.Float, default=0)
    data_limite = db.Column(db.Date, nullable=True)
    concluida = db.Column(db.Boolean, default=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def progresso(self):
        if self.valor_objetivo == 0:
            return 0
        return round((self.valor_atual / self.valor_objetivo) * 100, 1)

    def __repr__(self):
        return f'<Goal {self.nome}: {self.progresso}%>'

    @progresso.setter
    def progresso(self, pct):
        """Permitir atribuir progresso em porcentagem (0-100).

        Atribuir `goal.progresso = 50` atualiza `valor_atual` para 50% do `valor_objetivo`.
        """
        try:
            pct = float(pct)
        except (TypeError, ValueError):
            return

        if not self.valor_objetivo or self.valor_objetivo == 0:
            # Se não houver objetivo definido, zera valor_atual
            self.valor_atual = 0.0
            return

        # Limita entre 0 e 100
        pct = max(0.0, min(100.0, pct))
        self.valor_atual = round((pct / 100.0) * self.valor_objetivo, 2)


# --- MÓDULO DE MERCADO (Engenharia de Dados) ---

class MarketData(db.Model):
    __tablename__ = 'market_data'

    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(20), nullable=False, index=True)  # Ex: 'PETR4.SA', 'SELIC', 'IPCA'
    tipo = db.Column(db.String(20), nullable=False)                 # Ex: 'ACAO', 'INDICADOR', 'FUNDO'
    nome = db.Column(db.String(100))                                # Nome legível: 'Petrobras PN'
    valor = db.Column(db.Float, nullable=False)
    variacao_dia = db.Column(db.Float)                              # % de variação no dia
    data_referencia = db.Column(db.Date, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<MarketData {self.ticker}: {self.valor} em {self.data_referencia}>'


# --- CARTEIRA DE INVESTIMENTOS ---

class PortfolioItem(db.Model):
    """Posição individual na carteira do usuário."""
    __tablename__ = 'portfolio_items'

    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    tipo            = db.Column(db.String(20), nullable=False)   # cdb | lci | tesouro_selic | tesouro_ipca | poupanca | acoes | fii
    nome            = db.Column(db.String(100))                  # apelido livre
    valor_investido = db.Column(db.Float, nullable=False)
    data_entrada    = db.Column(db.Date, nullable=False)
    # Renda fixa
    pct_cdi         = db.Column(db.Float)   # ex: 1.10 = 110% CDI
    spread_ipca     = db.Column(db.Float)   # spread anual p/ Tesouro IPCA+ (ex: 0.06)
    # Renda variável
    ticker          = db.Column(db.String(20))   # ex: PETR4.SA
    preco_entrada   = db.Column(db.Float)        # preço por unidade na compra
    criado_em       = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<PortfolioItem {self.tipo} {self.nome} R${self.valor_investido}>'


# --- MÓDULO DE IMPOSTOS ---

class TaxProfile(db.Model):
    """Perfil tributário detalhado do usuário — CPF ou CNPJ, regime, etc."""
    __tablename__ = 'tax_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    tipo_pessoa = db.Column(db.String(10), default='PF')           # PF ou PJ
    regime = db.Column(db.String(30))                               # CLT, MEI, Simples, Lucro Presumido
    pro_labore = db.Column(db.Float)                                # Apenas PJ
    distribuicao_lucros = db.Column(db.Float)                       # Apenas PJ
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('tax_profile', uselist=False))

    def __repr__(self):
        return f'<TaxProfile {self.tipo_pessoa} - {self.regime}>'
