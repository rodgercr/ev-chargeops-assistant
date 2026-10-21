# GoodWeAI — EV ChargeOps Assistant

> Chatbot com IA desenvolvido para o **EV Challenge 2026** em parceria com a **GoodWe** e a **FIAP**, focado na gestão operacional de eletropostos em condomínios residenciais.

---

## Entrega da Sprint 4

O relatório obrigatório está em [`docs/relatorio_sprint4.pdf`](docs/relatorio_sprint4.pdf). As evidências detalhadas estão em [`docs/relatorio_rag.md`](docs/relatorio_rag.md), [`docs/relatorio_modelos.md`](docs/relatorio_modelos.md) e `evals/sprint4/results.json`.

| Item avaliado | Implementação |
|---|---|
| Embeddings | `nomic-embed-text:latest`, executado localmente no Ollama |
| ChromaDB | Índice persistente, separado por hash do corpus e reconstruível |
| RAG versionado | Prompts v1/v2, chunking 900/150 e top-k 2/4 |
| Grounding | Citações validadas, recusa sem contexto e proteção contra injection documental |
| RAGAS | 13 casos; faithfulness 0,705 → 0,876 e relevância 0,428 → 0,654 |
| Comparação | Llama 3.2:3b e Qwen3:4b sob os mesmos parâmetros |
| Interface | Streamlit com chat, autenticação e painel administrativo |
| Persistência | PostgreSQL para dados relacionais e memória de conversa |

Toda a aplicação opera localmente com **PostgreSQL, ChromaDB e Ollama**. Nenhuma credencial deve ser enviada ao repositório.

### Execução local

1. Instale PostgreSQL e Ollama.
2. Copie `.env.example` para `.env` e preencha somente os valores locais.
3. Execute `instalar.cmd`.
4. Instale os modelos: `ollama pull llama3.2:3b` e `ollama pull nomic-embed-text`.
5. Prepare o banco com `setup_banco.py` e `setup_ev.py`.
6. Construa o índice com `preparar_rag_sprint4.cmd`.
7. Inicie com `executar.cmd`.

O Qwen é necessário somente para reproduzir a comparação/RAGAS: `ollama pull qwen3:4b`. A aplicação web fica disponível por padrão em `http://localhost:8501`.

Para reproduzir a avaliação completa, execute `executar_ragas.cmd`. O processo instala as dependências opcionais de `requirements-ragas.txt` e preserva o resultado detalhado em `evals/sprint4/results.json`. Como o arquivo possui fingerprint da configuração, use outro caminho de saída ao alterar modelos ou parâmetros.

---

## Integrantes

| Nome | RM |
|------|----|
| Rodger Costa Rios | 571438 |
| Felipe Pereira Restivo | 570712 |
| Gabriel Rodrigues Zappelloni | 572060 |
| Kenichi Caio Yamamoto | 569815 |
| Maykon de Lima Silva | 574022 |

**Turma:** 1CCPK

### Responsabilidades previstas — Sprint 4

A divisão abaixo mantém o planejamento registrado na sprint anterior. Ela não comprova a execução individual das atividades. As contribuições efetivamente realizadas devem ser confirmadas pelo grupo antes da entrega, conforme o [registro da equipe](docs/equipe_sprint4.md).

| Integrante | Responsabilidades previstas |
|---|---|
| Rodger Costa Rios | Coordenação do grupo, integração da arquitetura e implementação do fluxo LCEL |
| Felipe Pereira Restivo | Interface e experiência de uso no Streamlit |
| Gabriel Rodrigues Zappelloni | RAG, ChromaDB e organização da base de conhecimento |
| Kenichi Caio Yamamoto | PostgreSQL local, modelos de dados e persistência das sessões |
| Maykon de Lima Silva | Guardrails, evals, comparação de modelos e documentação |

---

## Problema Abordado

O EV Challenge 2026 apresenta dois problemas centrais relacionados à infraestrutura de carregamento de veículos elétricos:

- **ChargeGrid Intelligence**: ausência de mecanismos integrados nos eletropostos para orquestrar potência, registrar ciclos de carregamento e faturar automaticamente.
- **EV ChargeOps**: falta de ferramentas para gerenciar o uso compartilhado de eletropostos em condomínios residenciais, incluindo controle de acesso, consumo por unidade e comunicação com moradores e síndicos.

O GoodWeAI endereça o problema **EV ChargeOps**, oferecendo uma solução conversacional que permite ao síndico e aos moradores interagirem com os dados do sistema de forma natural, sem necessidade de navegar por painéis técnicos complexos.

---

## Proposta do Chatbot

O **GoodWe AI** é o assistente virtual do GoodWeAI, operando em dois modos distintos conforme o perfil do usuário autenticado:

### Agente Síndico / Admin
Atende síndicos e administradores com acesso completo aos dados operacionais do condomínio:
- Consulta de consumo por apartamento e por eletroposto
- Relatórios de sessões de carregamento (duração, kWh, custo)
- Situação financeira: faturas pendentes, inadimplência
- Status e histórico de incidentes por eletroposto
- Geração solar por unidade e saldo de energia

### Agente Morador
Atende moradores com escopo restrito ao atendimento geral:
- Dúvidas sobre políticas de uso dos eletropostos
- Informações sobre tarifas e formas de pagamento
- Canais de suporte e contato
- Regras do condomínio

A separação entre agentes garante que dados sensíveis de outros moradores não sejam expostos indevidamente.

---

## Tecnologias Utilizadas e Justificativa Técnica

| Tecnologia | Função | Justificativa |
|------------|--------|---------------|
| **Python 3.11** | Linguagem principal do backend | Ecossistema maduro para IA e APIs REST |
| **FastAPI** | Framework da API REST | Alta performance, tipagem nativa, documentação automática via Swagger |
| **LLaMA 3.2** | Modelo de linguagem (LLM) | Modelo open-source, executado localmente via Ollama, sem custo de API e sem envio de dados para terceiros |
| **Ollama** | Servidor local do LLM | Permite rodar o LLaMA 3.2 localmente no Windows/Mac/Linux com um único comando |
| **LangChain LCEL** | Orquestração do pipeline de IA | Compõe prompt, modelo e parser em uma cadeia declarativa, testável e reutilizável |
| **PostgreSQL** | Banco de dados relacional | Armazena usuários, sessões de carregamento, faturas, incidentes e geração solar |
| **ChromaDB** | Banco vetorial local | Armazena os embeddings usados pelo RAG sem misturar documentos com os dados transacionais |
| **SQLAlchemy** | ORM Python | Abstração do banco de dados com suporte a migrations e queries tipadas |
| **JWT (python-jose)** | Autenticação | Tokens stateless com perfis diferenciados por assinatura digital |
| **bcrypt** | Hash de senhas | Padrão da indústria para armazenamento seguro de credenciais |

### Evolução da Sprint 4 — LCEL integrado ao RAG

Partindo da base conversacional criada na Sprint 3, a Sprint 4 integra a `RunnableSequence` do LangChain ao contexto recuperado pelo RAG:

```python
chain = ChatPromptTemplate | ChatOllama | StrOutputParser()
```

As informações recuperadas do PostgreSQL local e do RAG com ChromaDB entram como variáveis do `ChatPromptTemplate`. O `ChatOllama` executa o modelo local e o `StrOutputParser` converte a mensagem final em texto para a interface Streamlit e para a API FastAPI.

### Evolução da Sprint 4 — memória por sessão

A chain LCEL é envolvida por `RunnableWithMessageHistory`. Cada conversa recebe um `session_id` independente e utiliza `ConversationTokenBufferMemory`, com limite configurável por `MEMORY_MAX_TOKENS`. Ao iniciar uma nova conversa, o Streamlit gera outro identificador e não mistura o histórico anterior. As mensagens também são registradas no PostgreSQL local com o mesmo `session_id`, permitindo restaurar a sessão sem compartilhar contexto entre usuários ou abas.

### Evolução da Sprint 4 — context engineering e grounding

Os prompts de síndico e morador foram evoluídos para organizar identidade, objetivo, prioridade das fontes, segurança, privacidade e formato da resposta. O contexto enviado ao modelo é separado em dados do PostgreSQL local, documentos recuperados pelo RAG, histórico da sessão e pergunta atual. Conteúdo recuperado é tratado como dado, não como instrução, reduzindo o risco de prompt injection indireto e de respostas inventadas. A qualidade da recuperação e das respostas foi medida com RAGAS, e os resultados comparativos estão documentados nesta entrega.

### Por que LLaMA local e não OpenAI/Gemini?

A escolha pelo LLaMA 3.2 rodando localmente via Ollama foi deliberada:
- **Privacidade**: dados sensíveis do condomínio (consumo, inadimplência, incidentes) não trafegam para servidores externos.
- **Custo zero de inferência**: sem cobrança por token em produção.
- **Independência**: o sistema funciona sem conexão com APIs de terceiros.

### Por que ChromaDB junto ao PostgreSQL local?

O PostgreSQL local guarda usuários, recargas, faturas e demais dados estruturados. O ChromaDB guarda os embeddings dos documentos consultados pelo RAG. Essa separação mantém toda a solução no computador, facilita a demonstração sem credenciais externas e deixa clara a função de cada banco.

### RAG reproduzível

A fonte da Sprint 4 fica em `data/knowledge_base/`: o manifesto define IDs, arquivos e permissões, e os Markdown formam o corpus acadêmico. `preparar_rag_sprint4.cmd` valida o corpus, gera embeddings com `nomic-embed-text` e grava um índice persistente identificado pelo hash do conteúdo. O índice gerado não é enviado ao GitHub e pode ser reconstruído sem alterar o corpus.

Depois que os modelos Ollama estiverem instalados, a indexação e a aplicação funcionam localmente. A síntese HCA referencia o manual oficial; tarifas e políticas demonstrativas são marcadas como fictícias.

---

## Arquitetura do Sistema

```
┌─────────────────────────────────────────────────┐
│            STREAMLIT + FASTAPI OPCIONAL          │
│ Login · Cadastro · Chat · Painéis por perfil     │
└────────────────────┬────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────┐
│ Guardrails → Contexto → LCEL → Memória           │
└──────────┬──────────────────┬───────────────────┘
           │                  │
┌──────────▼──────┐  ┌────────▼──────────────────┐
│ PostgreSQL      │  │ ChromaDB / RAG             │
│ local           │  │ base em knowledge_base/    │
└──────────┬──────┘  └────────┬──────────────────┘
           │                  │
           └─────────┬────────┘
                     │
          ┌──────────▼──────────┐
          │ LLaMA 3.2 via Ollama│
          └─────────────────────┘
```

---

## Fluxo de Funcionamento

O fluxo completo do pipeline GoodWeAI:

1. **Autenticação** — valida o usuário e identifica seu perfil.
2. **Guardrails** — bloqueiam injeções, riscos e solicitações fora do escopo.
3. **Contexto relacional** — consulta no PostgreSQL local apenas dados autorizados para o perfil.
4. **RAG** — busca trechos relevantes na coleção `sindico` ou `atendimento`.
5. **Memória** — recupera o histórico isolado pelo `session_id`.
6. **LCEL** — combina prompt, contexto, histórico, ChatOllama e parser.
7. **Geração** — o LLaMA 3.2 produz a resposta localmente.
8. **Persistência** — pergunta e resposta são registradas no histórico da sessão.

---

## Modelo de Teste — Perguntas e Respostas Esperadas

### Agente Síndico

| # | Pergunta | Resposta Esperada |
|---|----------|-------------------|
| 1 | Qual usuário mais consumiu energia este mês? | O assistente consulta a tabela `sessoes_carregamento`, agrega por `usuario_id` e retorna o nome, apartamento, total em kWh e custo acumulado do período. |
| 2 | O eletroposto EP-04 está funcionando? | Consulta a tabela `eletropostos` pelo código EP-04 e retorna o status atual (ex: "em manutenção"), localização e data de instalação. |
| 3 | Quais faturas estão pendentes? | Consulta `faturas` com status "pendente", lista os moradores, valores e datas de vencimento. |
| 4 | Houve algum incidente esta semana? | Consulta `incidentes` filtrando pelos últimos 7 dias, retorna tipo, eletroposto envolvido e status de resolução. |
| 5 | Qual foi o total de energia carregada no condomínio em maio? | Agrega `energia_kwh` de todas as sessões do mês, retorna total em kWh e custo total do condomínio. |

### Agente Morador

| # | Pergunta | Resposta Esperada |
|---|----------|-------------------|
| 1 | Como faço para reservar um eletroposto? | Retorna as regras de uso definidas nas políticas do condomínio armazenadas no ChromaDB. |
| 2 | Qual é a tarifa de carregamento? | Informa o valor em R$/kWh conforme configuração vigente. |
| 3 | Minha fatura veio errada, o que faço? | Orienta contato com o síndico ou canal de suporte, conforme documentos de política. |
| 4 | Qual é o horário de funcionamento dos eletropostos? | Retorna as regras de horário definidas nas políticas do condomínio. |
| 5 | Como funciona o crédito de energia solar? | Explica o mecanismo de geração solar e saldo conforme documentação cadastrada. |

---

## System Prompts

### Agente Síndico

```
Você é o GoodWe AI, um EV ChargeOps Assistant no modo SÍNDICO, assistente virtual
especializado em gestão administrativa de eletropostos em condomínios residenciais,
desenvolvido no contexto do EV Challenge 2026 em parceria com a GoodWe e a FIAP.

Você está atendendo um SÍNDICO ou ADMINISTRADOR DO CONDOMÍNIO, que possui acesso
completo ao sistema GoodWeAI.

Responda sempre em português do Brasil, com linguagem técnica e administrativa.
Seja direto, objetivo e preciso. Nunca invente dados — use apenas as informações
fornecidas no contexto. Quando não souber, oriente a contatar o suporte GoodWe.
```

### Agente Morador

```
Você é o GoodWe AI, um EV ChargeOps Assistant no modo MORADOR, assistente virtual
especializado em atendimento a moradores de condomínios com eletropostos GoodWe,
desenvolvido no contexto do EV Challenge 2026 em parceria com a GoodWe e a FIAP.

Você está atendendo um MORADOR DO CONDOMÍNIO, com acesso restrito às informações
gerais do sistema e às políticas do condomínio.

Responda sempre em português do Brasil, com linguagem clara, simpática e acessível.
Seja objetivo e cordial. Nunca forneça dados de outros moradores.
Nunca invente informações — use apenas o conteúdo disponível no contexto.
Para questões operacionais ou financeiras específicas, oriente o morador a
contatar o síndico ou o suporte GoodWe.
```

---

## Estrutura do Repositório

```text
ev-chargeops-assistant/
├── streamlit_app.py               # Interface principal: login, chat e painéis
├── executar.cmd                   # Inicia a interface Streamlit no Windows
├── executar_evals.cmd             # Executa os evals integrados e guardrails
├── executar_ragas.cmd             # Reproduz a avaliação RAGAS da Sprint 4
├── instalar.cmd                   # Cria o ambiente e instala dependências
├── preparar_rag_sprint4.cmd       # Reconstrói o ChromaDB nomic da Sprint 4
├── preparar_rag_sprint4.py        # Valida e indexa a base documental atual
├── main.py                        # API FastAPI opcional
├── setup_banco.py                 # Cria tabelas base e dados iniciais
├── setup_ev.py                    # Cria tabelas EV e dados de exemplo
├── atualizar_prompts_sprint3.py   # Publica os prompts (nome legado da Sprint 3)
├── requirements.txt               # Dependências Python
├── .env.example                   # Modelo seguro das variáveis de ambiente
│
├── prompts/                       # Prompts atualizados de síndico e morador
├── knowledge_base/                # Fonte versionada e reproduzível do RAG
│   ├── manifest.json              # IDs, arquivos, coleções e hashes
│   └── *.md                       # Documentos acadêmicos de demonstração
│
├── models/
│   ├── consulta_recarga.py        # Structured output com Pydantic v2
│   ├── database.py                # Usuários, perfis, prompts e histórico
│   ├── ev_models.py               # Eletropostos, sessões, faturas e incidentes
│   ├── schemas.py                 # Validação das entradas e saídas da API
│   └── connection.py              # Conexão local via SQLAlchemy
│
├── routers/                       # Endpoints FastAPI opcionais
├── services/
│   ├── guardrails/                # Escopo, moderação e segurança
│   ├── auth_service.py            # Cadastro, hash de senha e tokens
│   ├── llm_service.py             # LCEL, memória por sessão e LLaMA
│   ├── rag_service.py             # Busca semântica via ChromaDB
│   └── db_context_service.py      # Contexto autorizado do PostgreSQL
│
├── evals/
│   ├── eval_set.json              # Conjunto reproduzível de casos integrados
│   ├── rag_dataset_sprint4.json   # Dataset de avaliação do RAG da Sprint 4
│   ├── run_evals.py               # Executor dos testes integrados
│   ├── run_sprint4.py             # Comparação reproduzível das configurações RAG
│   └── sprint4/results.json       # Resultado principal da Sprint 4
│
├── docs/
│   ├── relatorio_modelos.md       # Comparação LLaMA 3.2 × Qwen3
│   ├── relatorio_rag.md           # Evidências técnicas do pipeline RAG
│   └── relatorio_sprint4.pdf      # Relatório final da Sprint 4
│
└── tests/                         # 23 testes automatizados
```

---

## Como Executar

**Pré-requisitos:** Python 3.11, PostgreSQL local e Ollama com LLaMA 3.2.

### Windows — maneira recomendada

1. Execute `instalar.cmd` uma vez.
2. Crie no PostgreSQL local um banco vazio chamado `cargaai`.
3. Preencha no `.env` a senha do seu usuário PostgreSQL local.
4. Execute `python setup_banco.py` e `python setup_ev.py` com o ambiente ativado.
5. Execute `python atualizar_prompts_sprint3.py` (o nome foi mantido por compatibilidade com a Sprint 3).
6. Execute `preparar_rag_sprint4.cmd` para gerar o ChromaDB local.
7. Confirme que o Ollama está aberto e que o modelo configurado está instalado.
8. Execute `executar.cmd`.
9. Acesse `http://localhost:8501` se o navegador não abrir automaticamente.

### Preparar o PostgreSQL local

Durante a instalação do PostgreSQL, guarde a senha definida para o usuário `postgres`. No pgAdmin, selecione **Databases → Create → Database** e crie o banco `cargaai`. Depois, configure o `.env`:

```env
DATABASE_URL=postgresql://postgres:SUA_SENHA@localhost:5432/cargaai
```

Não envie o `.env` ao GitHub. O `setup_banco.py` cria ou atualiza as tabelas sem apagar dados existentes, e o `setup_ev.py` cria as tabelas operacionais e os dados de demonstração.

### Execução manual

```bash
# 1. Criar e ativar ambiente virtual
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # Linux/Mac

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Configurar variáveis de ambiente
# Editar .env com DATABASE_URL e demais configurações

# 4. Criar ou atualizar tabelas e inserir os dados iniciais
python setup_banco.py
python setup_ev.py
python atualizar_prompts_sprint3.py  # nome legado mantido por compatibilidade

# 5. Reconstruir as coleções do RAG
python preparar_rag_sprint4.py

# 6. Iniciar a interface
streamlit run streamlit_app.py --server.fileWatcherType none
```

A interface fica em `http://localhost:8501`. A API FastAPI continua disponível opcionalmente com `uvicorn main:app --reload` em `http://localhost:8000/docs`.

### Criar uma conta

Na tela inicial do Streamlit, escolha a aba **Criar conta**, informe nome, usuário e senha e depois entre normalmente. Todo cadastro público recebe automaticamente o perfil `morador`; contas de síndico e administrador continuam restritas à administração do sistema.

---

## Contexto do Desafio

Desenvolvido para o **EV Challenge 2026**, iniciativa da **GoodWe** em parceria com a **FIAP**, com foco na solução do problema **EV ChargeOps**: gestão inteligente de eletropostos compartilhados em condomínios residenciais, incluindo faturamento, monitoramento de consumo e comunicação entre síndico e moradores.

---

## Painel administrativo de carregadores

Entre com uma conta **admin** e, no menu lateral, abra **Gerenciar carregadores**.
O painel permite cadastrar postos, editar localização, potência, tarifa e status,
e consultar o histórico por carregador com filtros de período e status.
Tarifas e custos históricos são preservados.

Se o app já estava aberto antes da atualização, reinicie com `executar.cmd`.
Veja o [guia do painel administrativo](docs/painel_admin.md).

## Guardrails, evals e RAGAS da Sprint 4

> Para avaliar a qualidade da recuperação documental na Sprint 4, consulte também
> [RAGAS e comparação do RAG](docs/ragas.md). Os testes abaixo validam os
> guardrails, a segurança e as funcionalidades integradas desta entrega.
>
> Execução real da Sprint 4: [resultados e análise](docs/comparacao_rag.md).
> Foram avaliadas 20 respostas; a divisão experimental em trechos não demonstrou
> melhoria geral. A configuração de recuperação usada pelo app foi preservada.

Antes de consultar o RAG ou chamar o Ollama, a mensagem passa por guardrails determinísticos. Eles bloqueiam prompt injection, jailbreak, instruções elétricas perigosas, aconselhamento jurídico/financeiro, especificações não confirmadas e assuntos fora do escopo. Perguntas legítimas sobre faturas, consumo, eletropostos e recarga continuam permitidas; continuações curtas também são aceitas quando a sessão já possui contexto.

Para executar somente os testes de segurança, sem usar o Ollama:

```cmd
executar_evals.cmd --somente-guardrails
```

Para executar os dez casos com o modelo configurado no `.env`:

```cmd
executar_evals.cmd
```

Para escolher outro modelo já instalado no Ollama:

```cmd
executar_evals.cmd --model qwen3:4b
```

O conjunto reproduzível está em `evals/eval_set.json`. A comparação anterior entre `llama3.2:3b` e `qwen3:4b` foi migrada para `docs/relatorio_modelos.md`, e os JSONs originais permanecem em `evals/resultados_historicos/`.
