from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
from app.extensions import db, login_manager 
from app.services.market_etl import executar_pipeline_etl

def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    # Inicialização das extensões
    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))

    # Importação e Registro dos Blueprints
    from app.auth.routes import auth_bp
    from app.salary.routes import salary_bp
    from app.finance.routes import finance_bp
    from app.dashboard.routes import dashboard_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(salary_bp)
    app.register_blueprint(finance_bp)
    app.register_blueprint(dashboard_bp)

    # CONFIGURAÇÃO DO JOB AGENDADO (ETL)
    if not app.testing:
        scheduler = BackgroundScheduler()
        scheduler.add_job(
            func=executar_pipeline_etl, 
            trigger="interval", 
            hours=24, 
            args=[app],
            id="job_market_etl"
        )
        scheduler.start()

    return app