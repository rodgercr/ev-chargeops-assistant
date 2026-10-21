# Comparação do RAG — Sprint 4

Execução real iniciada em 2026-09-29T02:41:49.895306+00:00 (UTC). Estado: **concluido**.
Casos previstos: 10; respostas registradas: 20.

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
| faithfulness | 0.720 | 0.654 | -0.065 | 10/10 |
| answer_relevancy | 0.490 | 0.553 | 0.062 | 10/10 |
| context_precision | 0.883 | 0.833 | -0.050 | 10/10 |
| context_recall | 0.900 | 0.883 | -0.017 | 10/10 |

As médias acima usam somente perguntas com nota válida nas duas versões. Falhas são null, nunca zero.

## Medições auxiliares

| Medida | Atual | Candidato |
|---|---:|---:|
| source_recall | 0.900 (10/10) | 1.000 (10/10) |
| retrieval_seconds | 0.009 (10/10) | 0.010 (10/10) |
| generation_seconds | 1.047 (10/10) | 1.103 (10/10) |
| context_chars | 2028.800 (10/10) | 844.700 (10/10) |

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

Nenhum erro registrado até este ponto da execução.

## Evidências e reprodução

O results.json desta pasta contém respostas, contextos ordenados, fontes, distâncias, tokens medidos pelo Ollama, julgamentos, versões, hashes e notas individuais.

Execute executar_ragas.cmd para uma nova comparação. Para retomar: executar_ragas.cmd --resume CAMINHO_DO_RESULTS_JSON.

Referência: [documentação RAGAS](https://docs.ragas.io/en/latest/).
