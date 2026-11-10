import sys
import os
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.rag_engine import RAGEngine
from src.llm_service import LLMService

def executar_avaliacao():
    print("=== INICIANDO BATERIA DE TESTES E AVALIAÇÃO — SOLIA IA ===\n")
    rag = RAGEngine(data_path="data/base_doacoes.json")
    llm = LLMService()

    casos_teste = [
        {
            "id": "TC01",
            "tipo": "Match Direto (Alimentos)",
            "entrada": "Tenho 3 cestas básicas e leite em pó para doar na região da Vila Luzita.",
            "pedido_esperado": 101,
            "deve_gerar_alerta": False
        },
        {
            "id": "TC02",
            "tipo": "Match Semântico / Sinônimos (Vestuário)",
            "entrada": "Quero doar agasalhos de criança e mantas para o frio.",
            "pedido_esperado": 102,
            "deve_gerar_alerta": False
        },
        {
            "id": "TC03",
            "tipo": "Match de Urgência (Eletrodoméstico)",
            "entrada": "Estou trocando minha geladeira usada mas funcionando bem e quero doar.",
            "pedido_esperado": 103,
            "deve_gerar_alerta": False
        },
        {
            "id": "TC04",
            "tipo": "Situação de Risco / Triagem (Item Impróprio)",
            "entrada": "Tenho caixas de remédios controlados vencidos e pacotes de arroz vencido para doar.",
            "pedido_esperado": 101,
            "deve_gerar_alerta": True
        },
        {
            "id": "TC05",
            "tipo": "Situação de Falha / Fora de Escopo (Sem Match)",
            "entrada": "Quero doar peças de motor de avião e combustível industrial.",
            "pedido_esperado": None,
            "deve_gerar_alerta": True
        },
        {
            "id": "TC06",
            "tipo": "Regra de Negócio (Ignorar Pedido ENCERRADO #106)",
            "entrada": "Quero doar sacos de arroz 5kg e feijão para mutirão de outubro.",
            "pedido_esperado": 101,
            "deve_gerar_alerta": False
        }
    ]

    acertos_rag = 0
    acertos_triagem = 0
    tempos = []

    for caso in casos_teste:
        inicio = time.time()
        matches = rag.buscar_matches(caso["entrada"], top_k=3)
        resposta_ia = llm.gerar_recomendacao(caso["entrada"], matches)
        duracao = round(time.time() - inicio, 2)
        tempos.append(duracao)

        top_pedido = matches[0]["id_pedido"] if matches else None
        score_top = matches[0]["score_similaridade"] if matches else 0.0

        passou_rag = (top_pedido == caso["pedido_esperado"]) and all(m["id_pedido"] != 106 for m in matches)
        if passou_rag:
            acertos_rag += 1

        tem_alerta = bool(resposta_ia.get("alerta_triagem")) or resposta_ia.get("status_triagem") in ["ATENCAO", "SEM_MATCH"]
        passou_triagem = (tem_alerta == caso["deve_gerar_alerta"]) if caso["deve_gerar_alerta"] else True
        if passou_triagem:
            acertos_triagem += 1

        print(f"[{caso['id']}] {caso['tipo']}")
        print(f"  Entrada: {caso['entrada']}")
        print(f"  RAG Top-1: #{top_pedido} (Score: {score_top}) | Esperado: #{caso['pedido_esperado']} -> {'OK' if passou_rag else 'FALHA'}")
        print(f"  Status IA: {resposta_ia.get('status_triagem')} | Tempo: {duracao}s")
        print("-" * 70)

    total = len(casos_teste)
    print("\n=== RESUMO DAS MÉTRICAS DE AVALIAÇÃO ===")
    print(f"Total de Casos Testados: {total}")
    print(f"Precisão Top-1 do RAG (Retrieval Accuracy): {(acertos_rag/total)*100:.1f}% ({acertos_rag}/{total})")
    print(f"Acurácia de Triagem / Tratamento de Falhas: {(acertos_triagem/total)*100:.1f}% ({acertos_triagem}/{total})")
    print(f"Latência Média End-to-End (RAG + LLM): {sum(tempos)/total:.2f}s")

if __name__ == "__main__":
    executar_avaliacao()