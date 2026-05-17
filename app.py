from flask import Flask, jsonify, request

app = Flask(__name__, static_folder="static")

estoque = {}

@app.route("/")
def home():
    return app.send_static_file("index.html")

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

if __name__ == "__main__":
    app.run(debug=True)