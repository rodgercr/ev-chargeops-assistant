# Relatório do RAG — Sprint 4

## Escopo e reprodutibilidade

A avaliação foi executada localmente em 21/10/2026. O corpus fixado contém oito documentos Markdown versionados em `data/knowledge_base/`; o índice ChromaDB é persistente, reconstruível e usa `nomic-embed-text:latest`. O arquivo bruto, com respostas, trechos recuperados, tempos, tokens, notas e auditoria do julgador, está em `evals/sprint4/results.json`.

O chunking usa 900 caracteres e overlap de 150. Como os documentos atuais são curtos, cada arquivo produziu um trecho; portanto, o experimento mede principalmente recuperação e prompting. Esse é um limite conhecido, e não foi ocultado como se houvesse fragmentação extensa.

## Configuração

| Item | Valor |
|---|---|
| Gerador principal | `llama3.2:3b` |
| Comparação | `qwen3:4b` |
| Julgador RAGAS | `qwen3:4b` local |
| Embeddings | `nomic-embed-text:latest` |
| Temperature / top_p | 0 / 0,9 |
| Janela / máximo de saída | 8192 / 512 tokens |
| Eval set | 13 perguntas fixadas antes da execução |
| Métricas exigidas | faithfulness e answer_relevancy |

O mesmo modelo Qwen foi usado como julgador; isso reduz custo e mantém tudo local, mas pode introduzir viés. As referências do eval set foram autoradas pelo grupo e devem receber revisão humana antes de uma utilização além da disciplina.

## Iterações do prompt

| Versão | Mudança | k | Faithfulness | Answer relevancy | Recall da fonte | Respostas com citação |
|---|---|---:|---:|---:|---:|---:|
| v1 | Grounding, citação e documentos tratados como dados | 2 | 0,705 | 0,428 | 0,846 | 46,2% |
| v2 | Cobertura por parte da pergunta, proibição explícita de invenções, citação por parágrafo e recusa definida | 4 | 0,876 | 0,654 | 1,000 | 92,3% |
| Ganho | v2 − v1 | +2 | **+0,171** | **+0,226** | **+0,154** | **+46,1 p.p.** |

As médias acima usam os 13 casos válidos por versão do Llama. A v2 cumpriu a exigência de ganho nas duas métricas RAGAS obrigatórias. O aumento de `k` e a mudança do prompt ocorreram juntos; logo, o experimento demonstra ganho do pipeline v2, mas não isola causalmente qual das duas alterações foi responsável por cada parcela.

## Grounding e segurança

- cada trecho recebe um identificador estável e é apresentado como `[Fonte: id]`;
- resposta sem citação, ou com fonte não recuperada, é substituída por recusa segura;
- perguntas sem contexto autorizado recebem recusa;
- padrões de prompt injection dentro de documentos são removidos antes de compor o contexto;
- o filtro de perfil é aplicado na consulta ao índice antes da geração;
- especificações ausentes da base não devem ser completadas pelo conhecimento interno do modelo.

## Limitações

O corpus inclui uma síntese acadêmica referenciada do manual GoodWe HCA, e não uma cópia integral nem um manual específico do ChargeGrid. A tarifa de R$ 1,20/kWh é explicitamente fictícia. O resultado bruto terminou como `concluido_com_falhas` porque o Qwen atingiu o limite de saída em 25 de 26 tentativas; as 26 respostas do Llama e suas 52 notas RAGAS foram concluídas.
