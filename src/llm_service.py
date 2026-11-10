import os
import json
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

class LLMService:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY não encontrada no arquivo .env")
        self.client = genai.Client(api_key=api_key)
        self.models = ["gemini-3.8-flash", "gemini-3.8-flash-lite", "gemini-3.5-flash"]

    def _fallback_local(self, consulta_doador: str, matches_rag: list) -> dict:
        """Plano B offline caso a API externa sofra pico de demanda (HTTP 503)."""
        palavras_risco = ["vencid", "estragad", "quebrad", "remédio", "remedio", "medicamento"]
        tem_risco = any(p in consulta_doador.lower() for p in palavras_risco)

        recomendacoes = []
        for m in matches_rag:
            inst = m["instituicao"]
            recomendacoes.append({
                "id_pedido": m["id_pedido"],
                "instituicao": inst["nome"],
                "endereco": inst["endereco"],
                "motivo_compatibilidade": f"Compatível com a categoria '{m['categoria']}' (Similaridade semântica: {m['score_similaridade']*100:.1f}%).",
                "mensagem_pronta": f"Olá, equipe do {inst['nome']}! Vi o pedido #{m['id_pedido']} na plataforma SOLIA e gostaria de agendar uma doação. Como podemos combinar a entrega?"
            })

        return {
            "status_triagem": "ATENCAO" if tem_risco else "APROVADO",
            "analise_geral": f"Encontramos {len(matches_rag)} pedido(s) ativo(s) compatível(is) com a sua doação. A principal opção é {matches_rag[0]['instituicao']['nome']} (modo de contingência ativo devido à instabilidade temporária na API externa).",
            "recomendacoes": recomendacoes,
            "alerta_triagem": "Atenção: itens vencidos, danificados ou medicamentos controlados não são aceitos para doação direta." if tem_risco else None
        }

    def gerar_recomendacao(self, consulta_doador: str, matches_rag: list) -> dict:
        if not matches_rag:
            return {
                "status_triagem": "SEM_MATCH",
                "analise_geral": "Não encontramos pedidos de ajuda ativos compatíveis com os itens descritos no momento.",
                "recomendacoes": [],
                "alerta_triagem": "Verifique se os itens estão dentro das categorias aceitas (Alimentos, Vestuário, Móveis, Higiene ou Educação) ou tente descrever com mais detalhes."
            }

        contexto_rag = json.dumps(matches_rag, ensure_ascii=False, indent=2)

        prompt = f"""
Você é o Assistente Inteligente da plataforma CitizenTech 'SOLIA', que conecta doadores a instituições e pedidos de ajuda verificados.

ENTRADA DO DOADOR:
"{consulta_doador}"

CONTEXTO RECUPERADO DA BASE DE DADOS (VIA RAG - APENAS PEDIDOS ATIVOS):
{contexto_rag}

INSTRUÇÕES OBRIGATÓRIAS:
1. Baseie-se EXCLUSIVAMENTE nos dados fornecidos no contexto acima. Nunca invente instituições, endereços ou pedidos.
2. Analise a compatibilidade entre o que o doador quer entregar e os pedidos recuperados.
3. Verifique se há algum risco na doação (ex: alimentos vencidos, itens quebrados/sem conserto, medicamentos sem prescrição) e preencha o campo 'alerta_triagem' caso necessário (se estiver tudo certo, retorne null).
4. Para cada instituição/pedido recomendado, escreva uma mensagem curta e cordial pronta para o doador enviar no agendamento da entrega.

Retorne APENAS um JSON válido seguindo exatamente esta estrutura:
{{
  "status_triagem": "APROVADO" ou "ATENCAO",
  "analise_geral": "Resumo claro explicando qual é a melhor opção de doação e por quê.",
  "recomendacoes": [
    {{
      "id_pedido": 101,
      "instituicao": "Nome da Instituição",
      "endereco": "Endereço completo",
      "motivo_compatibilidade": "Explicação objetiva do match",
      "mensagem_pronta": "Olá! Gostaria de doar..."
    }}
  ],
  "alerta_triagem": "Aviso de boas práticas ou null"
}}
"""

        for model_id in self.models:
            try:
                response = self.client.models.generate_content(
                    model=model_id,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.2,
                    ),
                )
                return json.loads(response.text)
            except Exception:
                time.sleep(0.8)

        # Se todos os modelos da nuvem retornarem 503, aciona a contingência local sem quebrar a aplicação
        return self._fallback_local(consulta_doador, matches_rag)