from app import create_app

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        # Rodar sem reloader para evitar processos duplicados durante desenvolvimento
        app.run(debug=True, use_reloader=False)