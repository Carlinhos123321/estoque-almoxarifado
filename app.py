from flask import Flask, jsonify, request

app = Flask(__name__)

estoque = {}

@app.route("/estoque", methods=["GET"])
def listar():
    return jsonify(estoque), 200

@app.route("/estoque", methods=["POST"])
def adicionar():
    data = request.json
    nome = data.get("nome").lower()
    quantidade = data.get("quantidade", 0)

    if nome in estoque:
        estoque[nome] += quantidade
    else:
        estoque[nome] = quantidade

    return jsonify({
        "mensagem": "Item atualizado!",
        "estoque": estoque[nome]
    }), 201

@app.route("/")
def home():
    return "API FUNCIONANDO"

if __name__ == "__main__":
    app.run(debug=True)