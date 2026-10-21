# Relatório de modelos — Sprint 4

## Comparação controlada

Os modelos `llama3.2:3b` e `qwen3:4b` receberam as mesmas 13 perguntas, nas versões v1 e v2 do pipeline RAG, com `temperature=0`, `top_p=0,9`, `max_tokens=512`, `num_ctx=8192` e seed 42. O embedding, corpus e hardware foram mantidos.

| Modelo | Tentativas | Concluídas | Taxa de conclusão | Latência média válida | Resultado |
|---|---:|---:|---:|---:|---|
| `llama3.2:3b` | 26 | 26 | 100% | 1,31 s | Aprovado para o chatbot |
| `qwen3:4b` | 26 | 1 | 3,8% | 4,80 s | Reprovado nessa configuração |

O Qwen consumiu o limite de 512 tokens antes de emitir a resposta final em 25 casos. Essa falha é parte do resultado: não foram atribuídas notas RAGAS às respostas incompletas. Um ensaio isolado com limite maior terminou, porém produziu raciocínio excessivamente longo; por isso ele não substituiu o experimento fixado nem foi misturado às médias.

## Resultado do modelo selecionado

| Pipeline | Faithfulness | Answer relevancy | Entrada total | Saída total |
|---|---:|---:|---:|---:|
| Llama v1 | 0,705 | 0,428 | 6.987 tokens | 1.290 tokens |
| Llama v2 | 0,876 | 0,654 | 15.130 tokens | 1.259 tokens |

O `llama3.2:3b` foi mantido: concluiu todos os casos, apresentou ganho nas métricas e teve latência menor. A v2 usa mais tokens de entrada porque recupera quatro trechos em vez de dois, mas entregou respostas ligeiramente menores e mais bem fundamentadas.

## Limitações

O comparativo avalia essas versões e parâmetros no computador local; não representa um ranking universal. O julgador também é Qwen local, o que pode introduzir viés. Para reavaliar o Qwen de forma produtiva, recomenda-se criar uma nova execução identificada, com maior limite de saída e controle explícito do modo de raciocínio, sem sobrescrever a evidência atual.
