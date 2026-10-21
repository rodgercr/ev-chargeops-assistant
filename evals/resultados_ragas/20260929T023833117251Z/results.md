# Comparação do RAG — Sprint 4

Execução real iniciada em 2026-09-29T02:38:33.117251+00:00 (UTC). Estado: **parcial**.
Casos previstos: 10; respostas registradas: 2.

## Desenho do experimento

- Baseline: documentos inteiros, busca por similaridade cosseno, top-3.
- Candidato: divisão recursiva de até 400 caracteres, sobreposição máxima de 80, top-3.
- Mesma base, embeddings, perguntas, perfis, prompts e modelo nas duas configurações.
- Gerador: llama3.2:3b; juiz: qwen3:4b; temperatura 0; seed 42.
- Embeddings: all-MiniLM-L6-v2; relevância com strictness=3.
- Prompts do chatbot e recuperação compartilhada; sem PostgreSQL, memória ou guardrails nesta medição isolada.
- Coleções reconstruídas em data/ragas_chroma, sem alterar os índices usados pelo aplicativo.
- As referências esperadas não são enviadas ao gerador. São utilizadas apenas pelo avaliador.

## Métricas RAGAS (comparação pareada)

| Métrica | Atual | Candidato | Diferença | Pares válidos |
|---|---:|---:|---:|---:|
| faithfulness | 1.000 | 1.000 | 0.000 | 1/10 |
| answer_relevancy | 0.135 | 0.665 | 0.530 | 1/10 |
| context_precision | N/D | N/D | N/D | 0/10 |
| context_recall | 1.000 | 1.000 | 0.000 | 1/10 |

As médias acima usam somente perguntas com nota válida nas duas versões. Falhas são null, nunca zero.

## Medições auxiliares

| Medida | Atual | Candidato |
|---|---:|---:|
| source_recall | 1.000 (1/10) | 1.000 (1/10) |
| retrieval_seconds | 0.018 (1/10) | 0.011 (1/10) |
| generation_seconds | 4.164 (1/10) | 0.433 (1/10) |
| context_chars | 2027.000 (1/10) | 918.000 (1/10) |

source_recall é cobertura de IDs dos documentos esperados (não uma métrica RAGAS).
Latência de geração inclui a chamada local e eventual carregamento do modelo; não inclui avaliação pelo juiz.
Tempos dependem de hardware, aquecimento e ordem de execução; não representam um benchmark rigoroso de velocidade.

## Interpretação e limites

- Faithfulness: quanto da resposta está sustentado pelos contextos recuperados.
- Answer relevancy: alinhamento entre resposta e pergunta; não mede correção factual.
- Context precision: relevância/ordenação dos contextos em relação à referência.
- Context recall: cobertura das afirmações da referência pelos contextos.
- Valores são avaliações automáticas, não porcentagens de aprovação nem garantia de segurança.
- Juiz local pequeno pode errar; revisar respostas e julgamentos antes da entrega.
- Dataset pequeno, autorado com IA a partir de cinco documentos acadêmicos; não é teste externo nem validação de manuais oficiais GoodWe.
- Casos de dado ausente devem admitir a limitação. Uma recusa correta pode receber baixa relevância; revisar esses casos separadamente.
- Prompts internos do RAGAS permanecem em inglês; a pergunta regenerada para relevância é solicitada em português.
- Uma execução por configuração, sem significância estatística. Seed não garante determinismo entre máquinas.
- O candidato não foi promovido automaticamente para o chatbot. Não presumir que dividir documentos melhora o resultado.

## Erros observados

- rag-01 / documentos_inteiros: {"context_precision": "OutputParserException: Invalid json output: The output string did not satisfy the constraints given in the prompt. Fix the output string and return it.\nFor troubleshooting, visit: https://docs.langchain.com/oss/python/langchain/errors/OUTPUT_PARSING_FAILURE "}
- rag-01 / trechos_400_80: {"context_precision": "OutputParserException: Invalid json output: The output string did not satisfy the constraints given in the prompt. Fix the output string and return it.\nFor troubleshooting, visit: https://docs.langchain.com/oss/python/langchain/errors/OUTPUT_PARSING_FAILURE "}

## Evidências e reprodução

O results.json desta pasta contém respostas, contextos ordenados, fontes, distâncias, tokens medidos pelo Ollama, julgamentos, versões, hashes e notas individuais.

Execute executar_ragas.cmd para uma nova comparação. Para retomar: executar_ragas.cmd --resume CAMINHO_DO_RESULTS_JSON.

Referência: [documentação RAGAS](https://docs.ragas.io/en/latest/).
