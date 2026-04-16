from flask import Flask

app = Flask(__name__)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    return "<h1>O Vercel está VIVO!</h1><p>Se estás a ver isto, o problema era a ligação à Base de Dados e não o teu código.</p>"

if __name__ == "__main__":
    app.run()