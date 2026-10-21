# Comparação real do RAG — Sprint 4

## Resultado

**A divisão em trechos de 400 caracteres não demonstrou melhoria geral neste
experimento. O aplicativo mantém a recuperação por documentos inteiros.**
O candidato melhora relevância e cobertura das fontes, mas perde nas médias de
fidelidade, precisão de contexto e cobertura das afirmações da referência.
Isso é um resultado experimental, não uma reprovação da técnica de chunking.

Execução em 28/09/2026, das 23:41 às 23:49 (horário de São Paulo;
29/09 em UTC), com retomada do primeiro caso após o teste inicial.
Dez perguntas, duas configurações, 20 respostas e 80 notas válidas.
Não houve falhas na execução final.

| Métrica RAGAS | RAG atual | Trechos 400/80 | Diferença candidato − atual |
|---|---:|---:|---:|
| Faithfulness — sustentação da resposta | 0,720 | 0,654 | −0,065 |
| Answer relevancy — relevância da resposta | 0,490 | 0,553 | +0,062 |
| Context precision — relevância/ordenação do contexto | 0,883 | 0,833 | −0,050 |
| Context recall — cobertura da referência | 0,900 | 0,883 | −0,017 |

Médias pareadas, com os mesmos dez casos válidos nas duas versões. As diferenças
são calculadas antes do arredondamento. **Notas não são porcentagens de aprovação.**

## O que foi comparado

- Mesmos cinco documentos acadêmicos da knowledge_base, separados por perfil.
- Baseline: um documento por vetor; candidato: quebra recursiva de até 400
  caracteres, sobreposição máxima de 80. Busca cosseno top-3 em ambos.
- Gerador llama3.2:3b; juiz qwen3:4b; embeddings all-MiniLM-L6-v2.
- Temperatura 0, seed 42, contexto 8192, até 512 tokens por resposta e 2048 por
  chamada do juiz. Answer relevancy usa três perguntas regeneradas.
- Mesmos prompts de morador/síndico e função de recuperação do projeto. A
  temperatura foi controlada para o experimento; não é uma reprodução exata
  de todas as configurações do chat em produção.
- Referências esperadas só são enviadas ao juiz, nunca ao gerador.
- Os prompts vêm dos arquivos versionados, não do PostgreSQL. O teste isola o RAG:
  não avalia memória, guardrails, autenticação ou dados operacionais.
- Coleções isoladas em data/ragas_chroma; nenhum índice do app foi substituído.

## Medidas auxiliares

| Medida | Atual | Trechos |
|---|---:|---:|
| Cobertura média dos IDs de fontes esperadas | 0,900 | 1,000 |
| Caracteres médios recuperados | 2.028,8 | 844,7 |
| Tokens de entrada do gerador, total | 14.288 | 11.253 |
| Tokens de saída do gerador, total | 851 | 922 |
| Tempo médio de recuperação | 0,009 s | 0,010 s |
| Tempo médio de geração | 1,047 s | 1,103 s |

Tokens informados pelo Ollama, não estimados. Os totais acima não incluem o juiz;
suas chamadas e tokens estão separados no JSON. As latências incluem as condições
locais e eventual carregamento do modelo; não justificam conclusões gerais de
velocidade. Encontrar o ID correto não garante recuperar todas as frases necessárias.

## Revisão qualitativa dos registros

- **rag-01, uso:** o candidato explicou a verificação antes da recarga, mas omitiu
  retirar o veículo e liberar a vaga. O baseline respondeu às duas partes.
- **rag-02, faturas:** o baseline expandiu kWh incorretamente como
  “kilo-ohm-hora”. O candidato usou “quilowatt-hora”. É um erro real de geração;
  as notas automáticas não substituem essa revisão.
- **rag-03, cobrança:** o baseline recusou responder apesar de recuperar o
  documento de faturas. O candidato orientou comparar a fatura e procurar o síndico,
  embora tenha adicionado detalhes não expressos na referência.
- **rag-04, segurança:** o baseline não recuperou seguranca-recarga entre os três
  resultados. O candidato recuperou o documento e apresentou orientações gerais.
  Este teste não passou pelo guardrail da aplicação e não comprova segurança
  do fluxo completo.
- **rag-09 e rag-10, dados ausentes:** ambos admitiram não encontrar a informação.
  A relevância automática foi zero mesmo sendo uma recusa apropriada.

No caso rag-04 do baseline, o juiz considerou o primeiro documento genericamente
útil e a context precision ficou próxima de 1, apesar de context recall igual a 0.
É uma demonstração de que precisão isolada não basta e de que o juiz local pode
ser permissivo.

Separando exploratoriamente os oito casos com informação disponível, faithfulness
foi 0,712 → 0,755 e answer relevancy 0,613 → 0,691. Essa análise secundária não
substitui a tabela principal: mostra a influência dos casos de abstenção e reforça
a necessidade de uma base maior e revisão humana, sem selecionar apenas as notas
favoráveis ao candidato.

## Decisão e próximos experimentos

Manter o baseline por enquanto. Antes de promover outra configuração:

1. Revisar as referências e julgamentos com o grupo, principalmente recusas.
2. Ampliar as perguntas e usar documentos oficiais autorizados e mais variados.
3. Testar trechos maiores ou recuperação do parágrafo/documento pai, para evitar
   perda de informações complementares.
4. Comparar embeddings adequados ao português em experimento separado.
5. Repetir avaliações e validar os casos críticos manualmente.

Não há significância estatística demonstrada: são apenas dez perguntas autoradas
com auxílio de IA, cinco documentos demonstrativos e um juiz local pequeno.
Também não houve teste externo independente. Não apresentar estas notas como
certificação, garantia de segurança ou evidência de prontidão completa da Sprint 4.

## Evidências

- [Resultados completos e auditáveis](../evals/resultados_ragas/20260929T024149895306Z/results.json)
- [Relatório automático da execução](../evals/resultados_ragas/20260929T024149895306Z/results.md)
- [Perguntas e referências versionadas](../evals/rag_dataset.json)
- [Guia de reprodução por CMD](ragas.md)

SHA-256 do JSON final:
`7932d84496c4c08d1b31c7b38272c2a9aeca0045b35ac862004d737c437e4404`.

O piloto anterior, na pasta 20260929T023833117251Z, foi parcial e teve falhas de
JSON do juiz. Foi preservado como diagnóstico e **não entra nas médias acima**.
A execução final usa os mesmos esquemas Pydantic e fórmulas RAGAS com saída
estruturada nativa do Ollama. Foram executados 36 testes automatizados do projeto,
todos aprovados; eles validam o código, não a qualidade semântica das respostas.
