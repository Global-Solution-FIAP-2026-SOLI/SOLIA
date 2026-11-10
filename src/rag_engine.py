import json
import numpy as np
from sentence_transformers import SentenceTransformer


class RAGEngine:
    def __init__(self, data_path="data/base_doacoes.json"):
        self.data_path = data_path
        self.model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        self.pedidos_ativos = []
        self.embeddings = None
        self._carregar_e_indexar()

    def _carregar_e_indexar(self):
        with open(self.data_path, "r", encoding="utf-8") as f:
            todos_pedidos = json.load(f)

        self.pedidos_ativos = [p for p in todos_pedidos if p.get("status") == "ABERTO"]

        documentos = []
        for p in self.pedidos_ativos:
            itens_str = ", ".join([f"{i['quantidade']}x {i['nome']}" for i in p["itens"]])
            texto_indexavel = (
                f"Categoria: {p['categoria']}. "
                f"Necessidade: {p['descricao']} "
                f"Itens solicitados: {itens_str}. "
                f"Instituição: {p['instituicao']['nome']} localizada em {p['instituicao']['endereco']}."
            )
            documentos.append(texto_indexavel)

        self.embeddings = self.model.encode(documentos, normalize_embeddings=True)

    def buscar_matches(self, consulta_doador: str, top_k: int = 3, limiar_minimo: float = 0.25):
        vetor_consulta = self.model.encode([consulta_doador], normalize_embeddings=True)[0]

        similaridades = np.dot(self.embeddings, vetor_consulta)

        indices_ordenados = np.argsort(similaridades)[::-1][:top_k]

        resultados = []
        for idx in indices_ordenados:
            score = float(similaridades[idx])
            if score >= limiar_minimo:
                pedido = self.pedidos_ativos[idx].copy()
                pedido["score_similaridade"] = round(score, 4)
                resultados.append(pedido)

        return resultados