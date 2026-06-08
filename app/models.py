from .extensions import db
from flask_login import UserMixin
from datetime import datetime
from app import db
from datetime import datetime

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(200))

# Salário mensal do usuário, incluindo bruto e líquido
class Salary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    bruto = db.Column(db.Float)
    liquido = db.Column(db.Float)

# Dinheiro extra que o usuário recebe, como bônus ou renda extra
class Income(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    valor = db.Column(db.Float)
    categoria = db.Column(db.String(50))

# Despesas do usuário, como aluguel, contas, alimentação, etc.
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    valor = db.Column(db.Float)
    categoria = db.Column(db.String(50))
    descricao = db.Column(db.String(200))
    data = db.Column(db.Date, default=datetime.utcnow)

# Metas financeiras do usuário, como economizar para uma viagem, comprar um carro, etc.
class Goal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    nome = db.Column(db.String(100))
    valor_objetivo = db.Column(db.Float)
    valor_atual = db.Column(db.Float, default=0)

# Dados de mercado, como cotações de ações, taxas de juros, índices econômicos, etc.
class MarketData(db.Model):
    _tablename_ = 'market_data'
    
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(20), nullable=False, index=True) # Ex: 'PETR4.SA', 'SELIC', 'IPCA'
    tipo = db.Column(db.String(20), nullable=False) # Ex: 'ACAO', 'INDICADOR'
    valor = db.Column(db.Float, nullable=False)
    data_referencia = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def _repr_(self):
        return f"<MarketData {self.ticker}: {self.valor} em {self.data_referencia}>"
    
