from flask import Flask
from app.extensions import db, migrate, login_manager


def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

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
    from app.taxes.routes import taxes_bp
    from app.investimentos.routes import inv_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(salary_bp)
    app.register_blueprint(finance_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(taxes_bp)
    app.register_blueprint(inv_bp)

    _start_scheduler(app)
    return app


def _start_scheduler(app):
    """Sobe o APScheduler apenas no processo principal do Werkzeug."""
    import os
    if app.testing:
        return
    # Em debug o Werkzeug sobe dois processos; só inicializa no processo filho
    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
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
        app.logger.info("✅ Scheduler iniciado.")
    except Exception as e:
        app.logger.warning(f"Scheduler não iniciado: {e}")
