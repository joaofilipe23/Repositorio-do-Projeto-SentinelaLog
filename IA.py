import os
import json
import urllib.request
import urllib.error

def perguntar_ia(pergunta):
    chave = os.environ.get("GROQ_API_KEY")
    if not chave:
        return "Chave da API não encontrada."
    url = "https://api.groq.com/openai/v1/chat/completions"
    dados = {
        "model": "openai/gpt-oss-20b",
        "reasoning_effort": "low",
        "messages": [
            {"role": "user", "content": "REGRA: responda em português do Brasil, em UM parágrafo de no máximo 2 frases, sem tabela, sem lista, sem asterisco, sem título. Pergunta: " + pergunta}
        ]
    }
    pedido = urllib.request.Request(url, data=json.dumps(dados).encode("utf-8"), method="POST")
    pedido.add_header("Content-Type", "application/json")
    pedido.add_header("Authorization", "Bearer " + chave)
    pedido.add_header("User-Agent", "sentinelalog")
    try:
        resposta = urllib.request.urlopen(pedido, timeout=30)
        resultado = json.loads(resposta.read().decode("utf-8"))
        return resultado["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as erro:
        return "Erro da API: " + str(erro.code)
    except Exception:
        return "Não consegui falar com a IA."

def explicar_relatorio(relatorio):
    pergunta = "Explique em linguagem simples, em poucas linhas, os riscos deste relatório de segurança de um laboratório de informática escolar:\n\n" + relatorio
    return perguntar_ia(pergunta)