# Relatório de comparação de modelos

## Origem dos resultados

Esta comparação foi executada na etapa anterior da evolução da Sprint 3, usando o mesmo conjunto de dez casos presente em `evals/eval_set.json`. Os arquivos detalhados originais foram preservados em `evals/resultados_historicos/`. Eles são mantidos como evidência da decisão de modelo e não foram recalculados nem alterados durante a migração para a arquitetura atual.

## Configuração comum

Os modelos foram avaliados no mesmo computador, com os mesmos prompts, casos e parâmetros. A execução utilizou memória local isolada e não gravou dados no PostgreSQL.

| Modelo | Temperature | Top-p | Máx. saída | Raciocínio | Testes aprovados | Taxa de sucesso | Latência média | Tokens de saída |
|---|---:|---:|---:|---|---:|---:|---:|---:|
| `llama3.2:3b` | 0.2 | 0.9 | 512 | desativado | 10/10 | 100% | 0,904 s | 709 |
| `qwen3:4b` | 0.2 | 0.9 | 512 | desativado | 8/10 | 80% | 2,537 s | 1.250 |

## Resultado

O `llama3.2:3b` aprovou todos os casos. O `qwen3:4b` falhou nos casos `chat-01` (caminho feliz) e `structured-01` (saída estruturada). Nesse ambiente, o Llama também apresentou latência média aproximadamente 2,81 vezes menor.

## Recomendação

O modelo recomendado para o chatbot é o `llama3.2:3b`, por combinar a maior taxa de sucesso com a menor latência média entre os modelos avaliados.

## Cobertura

O conjunto cobre:

- conversa dentro do escopo;
- memória em três turnos;
- saída estruturada com Pydantic v2;
- prompt injection e jailbreak;
- solicitação fora do escopo;
- segurança elétrica;
- aconselhamento jurídico e financeiro;
- especificação de produto não confirmada.

## Limitações

As métricas refletem o hardware e a execução local usados naquele momento. Tempos podem variar conforme CPU/GPU, carga do sistema e estado do Ollama. O executor atual, `evals/run_evals.py`, permite gerar uma nova medição da arquitetura integrada antes da apresentação final.
