from flask import Flask
from prometheus_flask_exporter import PrometheusMetrics

# Création minimale de l'application
app = Flask(__name__)
metrics = PrometheusMetrics(app)

@app.route('/')
def index():
    return "Le serveur de test fonctionne !"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)