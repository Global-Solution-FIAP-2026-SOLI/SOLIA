from flask import Flask, render_template, request, jsonify
from src.rag_engine import RAGEngine
from src.llm_service import LLMService

app = Flask(__name__)

rag_engine = RAGEngine(data_path="data/base_doacoes.json")
llm_service = LLMService()

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/api/recomendar", methods=["POST"])
def recomendar():
    dados = request.get_json()
    consulta = dados.get("consulta", "").strip()

    if not consulta:
        return jsonify({"erro": "Por favor, descreva o que você deseja doar."}), 400

    try:
        matches_rag = rag_engine.buscar_matches(consulta, top_k=3)

        resposta_ia = llm_service.gerar_recomendacao(consulta, matches_rag)

        return jsonify({
            "matches_rag": matches_rag,
            "resultado_ia": resposta_ia
        })
    except Exception as e:
        return jsonify({"erro": f"Erro ao processar solicitação: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)