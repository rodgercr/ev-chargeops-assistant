# Sprint 4 — RAGAS e comparação do RAG

Resultado medido: [comparação e conclusão](comparacao_rag.md).

O benchmark mede duas configurações sobre os mesmos cinco documentos versionados:

| Configuração | Unidade de busca | Busca |
|---|---|---|
| documentos_inteiros | Um documento por vetor (baseline do aplicativo) | Cosseno, top-3 |
| trechos_400_80 | Trechos de até 400 caracteres, sobreposição máxima de 80 | Cosseno, top-3 |

O candidato é experimental: **não substitui automaticamente o RAG do chatbot**.
A comparação isola o RAG documental. Não testa login, banco relacional, memória,
guardrails ou o aplicativo de ponta a ponta. Os prompts e a função de recuperação
são compartilhados com o aplicativo, mas não usamos os dados pessoais do banco.

## Executar no Windows

Na pasta do projeto, em um terminal CMD:

```cmd
.venv\Scripts\python.exe -m pip install -r requirements-ragas.txt
ollama pull llama3.2:3b
ollama pull qwen3:4b
executar_ragas.cmd
```

Mantenha o Ollama aberto. Se os modelos já estiverem instalados, não é preciso
baixá-los novamente. O .cmd instala as dependências opcionais se o RAGAS não
estiver disponível. O download inicial de dependências/embeddings exige internet;
a inferência e os julgamentos usam somente o Ollama local, sem chave de API.

O gerador padrão é llama3.2:3b e o juiz padrão é qwen3:4b. Usar modelos distintos
reduz a autoavaliação direta, mas não elimina vieses ou erros do juiz.

```cmd
executar_ragas.cmd --limit 1
executar_ragas.cmd --resume evals\resultados_ragas\PASTA_DA_EXECUCAO\results.json
executar_ragas.cmd --model llama3.2:3b --judge qwen3:4b --timeout 240
```

O teste com --limit é marcado como **parcial**. Para completar, retome sem esse
parâmetro. A retomada exige os mesmos modelos, parâmetros, versões, código, prompts
e base. Ela não repete resultados já registrados, inclusive falhas. Para reavaliar
falhas, inicie uma nova execução. Não edite as notas manualmente.

Cada execução cria uma pasta nova em evals/resultados_ragas, com results.json e
results.md. Os arquivos são atualizados a cada resposta e métrica. Saída 0 indica
conclusão sem falhas; 2 indica parcial/falhas; 1 indica erro de preparação.

## O que é medido

- **Faithfulness:** sustentação da resposta pelos trechos recuperados.
- **Answer relevancy:** alinhamento entre pergunta e resposta; strictness=3.
- **Context precision:** relevância e ordem dos contextos em relação à referência.
- **Context recall:** cobertura das afirmações da referência nos contextos.
- Medidas auxiliares: cobertura dos IDs esperados, tamanho do contexto, latências
  e tokens reais informados pelo Ollama. Não confundir cobertura de IDs com recall RAGAS.

São dez perguntas, incluindo dois casos de dados ausentes e um caso multifonte.
As respostas esperadas foram autoradas a partir dos documentos: o grupo deve
revisá-las. Elas nunca são fornecidas ao gerador.

O adaptador usa os prompts, modelos Pydantic e fórmulas do RAGAS, com saída JSON
estruturada nativa do Ollama. Explicações e perguntas regeneradas são solicitadas
em português. Falhas/truncamentos geram null com erro registrado, nunca nota zero
inventada. A tabela principal compara apenas pares válidos e mostra a cobertura.

## Reprodutibilidade e limites

- Temperatura 0 e seed 42; contexto 8192; resposta até 512 tokens; juiz até 2048.
- Ordem das configurações alternada por pergunta; geração antes da avaliação.
- Registros contêm hashes da base/código/prompts, versões e digest dos modelos.
- Índices isolados em data/ragas_chroma, ignorados pelo Git; a base do app é preservada.
- Telemetria do RAGAS e tracing LangChain desativados pelo executor.
- RAGAS 0.4.3 e langchain-community 0.4.1 fixados: a versão 0.4.2 de community
  removeu um módulo que essa versão do RAGAS ainda importa.
- Os adaptadores de compatibilidade do RAGAS emitem avisos de depreciação; não
  atualizar a versão principal sem testar a integração.
- Embeddings são os mesmos do aplicativo (EMBEDDING_MODEL do .env). O modelo padrão
  all-MiniLM-L6-v2 tem limitações em português; trocar embeddings deve ser outro experimento.
- Dez casos sobre cinco documentos não comprovam qualidade geral, segurança ou
  significância estatística. Notas do juiz local exigem revisão humana.
- Recusas corretas em perguntas sem resposta podem receber relevância baixa.
  Verifique esses casos individualmente.

Testes rápidos (sem Ollama):

```cmd
.venv\Scripts\python.exe -m pytest -q
```

Documentação de referência: [RAGAS](https://docs.ragas.io/en/latest/).
