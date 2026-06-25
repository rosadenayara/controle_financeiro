from app import create_app
from app.extensions import db

app = create_app()

# Adicione estas duas linhas para criar o banco de dados no Render automaticamente
with app.app_context():
    db.create_all()

if __name__ == "_main_":
    app.run(debug=True, use_reloader=False)