from flask import Flask
from app.extensions import db, migrate, login_manager


def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    # Extensões
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))

    # Blueprints
    from app.auth.routes import auth_bp
    from app.salary.routes import salary_bp
    from app.finance.routes import finance_bp
    from app.dashboard.routes import dashboard_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(salary_bp)
    app.register_blueprint(finance_bp)
    app.register_blueprint(dashboard_bp)

    # Job agendado — ETL de mercado (apenas fora de testes)
    _start_scheduler(app)

    return app


def _start_scheduler(app):
    """Inicia o APScheduler apenas uma vez, evitando duplicação em reload do dev server."""
    import os
    # Em desenvolvimento o Werkzeug sobe dois processos; o reloader não deve subir o scheduler
    if app.testing or app.debug:
        # Não inicia o scheduler durante testes ou no modo debug/development
        return

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from app.services.market_etl import executar_pipeline_etl

        scheduler = BackgroundScheduler(daemon=True)
        scheduler.add_job(
            func=executar_pipeline_etl,
            trigger="interval",
            hours=24,
            args=[app],
            id="job_market_etl",
            replace_existing=True,
        )
        scheduler.start()
    except Exception as e:
        # Se o APScheduler não estiver instalado ou ocorrer erro, apenas loga e segue
        try:
            app.logger.warning(f"Scheduler não iniciado: {e}")
        except Exception:
            print("Scheduler não iniciado:", e)
