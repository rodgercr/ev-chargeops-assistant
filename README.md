# GoodWeAI — Agente Síndico

> Assistente virtual inteligente para gestão administrativa de eletropostos em condomínios residenciais, desenvolvido no contexto do **EV Challenge 2026** em parceria com a **GoodWe** e a **FIAP**.

---

## Integrantes

| Nome | RM |
|------|----|
| Felipe Pereira Restivo | RM: 570712 |
| Gabriel Rodrigues Zappelloni | RM: 572060 |
| Kenichi Caio Yamamoto | RM: 569815 |
| Maykon de Lima Silva | RM: 574022 |
| Rodger Costa Rios | RM: 571438 |

---

## Problema Abordado

O EV Challenge 2026 apresenta o problema **EV ChargeOps**: a ausência de ferramentas integradas para gerenciar o uso compartilhado de eletropostos em condomínios residenciais, incluindo controle de consumo por unidade, faturamento automático e comunicação com o síndico.

O Agente Síndico do GoodWeAI resolve esse problema oferecendo uma interface conversacional que permite ao síndico consultar dados operacionais do condomínio de forma natural, sem necessidade de navegar por painéis técnicos complexos.

---

## Persona Atendida

**Síndico / Administrador do condomínio** — usuário com acesso completo ao sistema, responsável pela gestão dos eletropostos, moradores e financeiro do condomínio.

O agente responde perguntas como:
- "Qual apartamento mais consumiu energia este mês?"
- "Quais faturas estão pendentes?"
- "O eletroposto EP-04 está funcionando?"
- "Houve algum incidente esta semana?"
- "Qual foi o total de energia carregada no condomínio em maio?"

---

## Tecnologias Utilizadas e Justificativa Técnica

| Tecnologia | Função | Justificativa |
|------------|--------|---------------|
| **Python 3.11** | Linguagem principal do backend | Ecossistema maduro para IA e APIs REST |
| **FastAPI** | Framework da API REST | Alta performance, tipagem nativa, documentação automática via Swagger |
| **LLaMA 3.2** | Modelo de linguagem (LLM) | Modelo open-source, executado localmente via Ollama, sem custo de API e sem envio de dados para terceiros |
| **Ollama** | Servidor local do LLM | Permite rodar o LLaMA 3.2 localmente sem dependência de APIs externas |
| **LangChain** | Orquestração do pipeline de IA | Gerencia o fluxo entre prompt, contexto e modelo |
| **PostgreSQL** | Banco de dados relacional | Armazena usuários, sessões de carregamento, faturas, incidentes e geração solar |
| **pgvector** | Extensão vetorial do PostgreSQL | Permite busca semântica por similaridade diretamente no PostgreSQL |
| **SQLAlchemy** | ORM Python | Abstração do banco de dados com queries tipadas |
| **JWT (python-jose)** | Autenticação | Tokens stateless com perfis diferenciados por assinatura digital |

### Por que LLaMA local?

- **Privacidade**: dados sensíveis do condomínio (consumo, inadimplência, incidentes) não trafegam para servidores externos.
- **Custo zero de inferência**: sem cobrança por token em produção.
- **Independência**: o sistema funciona sem conexão com APIs de terceiros.

### Por que pgvector?

Consolida a busca semântica dentro do mesmo PostgreSQL já utilizado pelo sistema, eliminando um banco de dados extra, simplificando o backup e permitindo queries combinando dados relacionais e vetoriais.

---

## Fluxo de Funcionamento — Agente Síndico

![Fluxograma Agente Síndico](./docs/fluxograma_sindico.png)

1. **Autenticação** — síndico acessa o bot e o sistema valida o perfil via JWT
2. **Carregamento do System Prompt** — prompt versionado do perfil síndico é carregado do PostgreSQL
3. **Middleware de autorização** — valida permissões e escopo do perfil
4. **Orquestração LangChain** — gerencia o pipeline de execução
5. **Dois caminhos paralelos:**
   - **Sistema RAG** — filtro por metadados → busca semântica com pgvector → reranking de relevância
   - **db_context_service** — busca dados reais no PostgreSQL: sessões, faturas, incidentes e geração solar de todos os moradores
6. **Montagem do prompt** — system prompt + dados do banco + contexto semântico + pergunta
7. **Decisão de qualidade** — se RAG não encontrou conteúdo relevante, aciona fallback para suporte
8. **Geração com LLaMA 3.2** — via Ollama, inferência local
9. **Validação da resposta** — se falhar, aciona retry com timeout
10. **Pós-processamento** — formatação e sanitização
11. **Logging e observabilidade** — salva no `historico_conversas` do PostgreSQL
12. **Resposta exibida ao síndico**

---

## Modelo de Teste — Perguntas e Respostas Esperadas

| # | Pergunta | Resposta Esperada |
|---|----------|-------------------|
| 1 | Qual usuário mais consumiu energia este mês? | Consulta `sessoes_carregamento` agrupando por `usuario_id`, retorna nome, apartamento, total em kWh e custo acumulado do período. |
| 2 | O eletroposto EP-04 está funcionando? | Consulta a tabela `eletropostos` pelo código EP-04 e retorna o status atual, localização e potência. |
| 3 | Quais faturas estão pendentes? | Consulta `faturas` com status "pendente", lista moradores, valores e datas de vencimento. |
| 4 | Houve algum incidente esta semana? | Consulta `incidentes` filtrando pelos últimos 7 dias, retorna tipo, eletroposto envolvido e status de resolução. |
| 5 | Qual foi o total de energia carregada no condomínio em maio? | Agrega `energia_kwh` de todas as sessões do mês, retorna total em kWh e custo total do condomínio. |

---

## System Prompt — Agente Síndico

```
Você é o GoodWe AI, um EV ChargeOps Assistant no modo SÍNDICO, assistente virtual
especializado em gestão administrativa de eletropostos em condomínios residenciais,
desenvolvido no contexto do EV Challenge 2026 em parceria com a GoodWe e a FIAP.

Você está atendendo um SÍNDICO ou ADMINISTRADOR DO CONDOMÍNIO, que possui acesso
completo ao sistema GoodWeAI.

## IDENTIDADE E POSTURA

- Seu nome é GoodWe AI. Não se apresente como "IA" ou "chatbot" — você é um assistente
  operacional do sistema GoodWeAI.
- Trate o síndico com respeito e linguagem técnica-administrativa, mas sem ser
  excessivamente formal.
- Seja direto, objetivo e preciso. O síndico toma decisões com base no que você informa
  — nunca invente dados ou funcionalidades.
- Quando não souber uma informação com certeza, diga: "Não tenho esse dado disponível
  no momento. Recomendo verificar diretamente no painel ou acionar o suporte GoodWe."
- Mantenha coerência com o histórico da conversa.

## DADOS QUE VOCÊ PODE CONSULTAR

- Cadastro de todos os moradores e apartamentos
- Histórico completo de sessões de carregamento (duração, kWh, custo, eletroposto)
- Faturas: pendentes, pagas e inadimplência por unidade
- Status operacional de cada eletroposto: online, offline, em manutenção, com falha
- Relatório de incidentes: data, tipo, status e resolução
- Geração solar por unidade e saldo de energia

## REGRAS DE COMPORTAMENTO

1. SEMPRE responda em português do Brasil.
2. NUNCA invente dados, valores ou funcionalidades que não existam no sistema.
3. NUNCA realize ações diretas — você orienta, o síndico executa.
4. Em casos de emergência (incêndio, curto-circuito), instrua a desligar o disjuntor
   e acionar o suporte de emergência GoodWe: 0800-XXX-XXXX.
5. Para problemas de hardware, redirecione ao suporte técnico oficial.
6. Dados financeiros sensíveis (CPF, dados bancários) não devem ser compartilhados.

## LIMITAÇÕES TÉCNICAS

- Você não possui acesso em tempo real aos equipamentos.
- Você não realiza ações diretas no sistema — apenas orienta.
- Para problemas críticos de hardware, redirecione ao suporte técnico oficial da GoodWe.
```

---

## Contexto do Desafio

Desenvolvido para o **EV Challenge 2026**, iniciativa da **GoodWe** em parceria com a **FIAP**, com foco na solução do problema **EV ChargeOps**: gestão inteligente de eletropostos compartilhados em condomínios residenciais.
