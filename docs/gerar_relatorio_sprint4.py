"""Gera o relatório acadêmico da Sprint 4 em exatamente cinco páginas."""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "relatorio_sprint4.pdf"
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="Title2", parent=styles["Title"], textColor=colors.HexColor("#111827"), fontSize=22, leading=27, alignment=TA_CENTER))
styles.add(ParagraphStyle(name="H1x", parent=styles["Heading1"], textColor=colors.HexColor("#111827"), fontSize=16, leading=20, spaceAfter=10))
styles.add(ParagraphStyle(name="Bodyx", parent=styles["BodyText"], fontSize=9.2, leading=13, textColor=colors.HexColor("#263238"), spaceAfter=7))
styles.add(ParagraphStyle(name="Smallx", parent=styles["BodyText"], fontSize=7.6, leading=10, textColor=colors.HexColor("#374151")))


def p(text, style="Bodyx"):
    return Paragraph(text, styles[style])


def tabela(rows, widths, header=True):
    data = [[p(str(cell), "Smallx") for cell in row] for row in rows]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        commands += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E5E7EB")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827"))]
    t.setStyle(TableStyle(commands))
    return t


def rodape(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D1D5DB")); canvas.line(1.6*cm, 1.3*cm, 19.4*cm, 1.3*cm)
    canvas.setFont("Helvetica", 7.5); canvas.setFillColor(colors.HexColor("#6B7280"))
    canvas.drawString(1.6*cm, 0.85*cm, "FIAP x GoodWe Brasil · EV Challenge · Sprint 04")
    canvas.drawRightString(19.4*cm, 0.85*cm, f"Página {doc.page}")
    canvas.restoreState()


story = []
logo = ROOT / "assets" / "goodweai-logo.png"
if logo.exists():
    story += [Spacer(1, 0.7*cm), Image(str(logo), width=2.1*cm, height=2.1*cm), Spacer(1, 0.25*cm)]
story += [
    p("EV Challenge — Sprint 04", "Title2"),
    p("GoodWeAI · EV ChargeOps Assistant", "Title2"), Spacer(1, 0.6*cm),
    p("Relatório de evolução do projeto", "H1x"),
    p("Ciência da Computação — 2º semestre · Turma 1CCPK · 2026.2"),
    p("O projeto evoluiu do protótipo das Sprints 1/2 e da arquitetura conversacional LCEL da Sprint 3 para um RAG local medido: ChromaDB persistente, embeddings nomic, citações verificadas, duas versões de prompt, avaliação RAGAS e interface Streamlit."),
    tabela([["Entrega", "Evidência"], ["Interface web", "Streamlit: login, chat e painel administrativo"], ["RAG reproduzível", "data/knowledge_base + preparar_rag_sprint4.cmd"], ["Avaliação", "13 casos, 2 iterações e arquivo bruto versionado"], ["Relatórios", "relatorio_rag.md e relatorio_modelos.md"]], [5*cm, 11.5*cm]),
    Spacer(1, 0.4*cm), p("Execução totalmente local com PostgreSQL, ChromaDB e Ollama. Credenciais permanecem no arquivo .env ignorado pelo Git."),
    PageBreak(),
]

story += [p("1. Pipeline RAG e decisões técnicas", "H1x"),
    p("Fluxo: documentos versionados → validação do manifesto → chunking → embeddings nomic-embed-text → ChromaDB persistente → filtro por perfil → top-k → prompt LCEL → Llama 3.2 → validação das citações."),
    tabela([["Decisão", "Configuração", "Trade-off"], ["Chunking", "900 caracteres, overlap 150", "Simples e determinístico; com o corpus curto atual resultou em 1 trecho por documento."], ["Recuperação", "v1 k=2; v2 k=4", "v2 aumenta contexto e tokens, mas elevou recall e métricas."], ["Índice", "Nome derivado do hash", "Reprodutível e preserva índices anteriores; usa espaço adicional."], ["Embedding", "nomic-embed-text local", "Privacidade e operação offline após instalação; exige Ollama e 274 MB."], ["Perfis", "Filtro antes da geração", "Reduz exposição; depende de metadados corretos no manifesto."]], [3.2*cm, 4.4*cm, 9.6*cm]),
    Spacer(1, 0.25*cm), p("Base: cinco documentos acadêmicos herdados, FAQ, tabela tarifária explicitamente fictícia e uma síntese referenciada do manual GoodWe HCA. Não foi atribuída documentação ChargeGrid inexistente à GoodWe."),
    p("Guardrails: conteúdo recuperado é dado, não instrução; padrões de injection documental são descartados; resposta sem fonte recuperada é substituída por recusa; especificações ausentes não podem ser inventadas."),
    PageBreak()]

story += [p("2. Avaliação RAGAS e evolução do prompt", "H1x"),
    p("Execução local de 21/10/2026. O eval set foi fixado antes da medição, com 13 perguntas e referências. O Qwen 3:4b atuou como julgador RAGAS; isso mantém o ensaio local, mas é uma fonte possível de viés."),
    tabela([["Versão", "Mudança principal", "k", "Faithfulness", "Relevância", "Recall fonte", "Citação"], ["v1", "Grounding e fonte básica", "2", "0,705", "0,428", "0,846", "46,2%"], ["v2", "Cobertura, recusa e fonte por parágrafo", "4", "0,876", "0,654", "1,000", "92,3%"], ["Ganho", "v2 − v1", "+2", "+0,171", "+0,226", "+0,154", "+46,1 p.p."]], [1.4*cm, 5*cm, 0.8*cm, 2.1*cm, 2.1*cm, 2.1*cm, 2*cm]),
    Spacer(1, 0.3*cm), p("Cada média usa as 13 respostas válidas do Llama em cada versão. A v2 teve ganho nas duas métricas obrigatórias. Prompt e k mudaram simultaneamente; por isso o resultado comprova melhoria do pipeline, não causalidade isolada de uma única alteração."),
    p("Comparação de modelos: o Llama concluiu 26/26 tentativas (100%, latência válida média 1,31 s). O Qwen concluiu 1/26 (3,8%, 4,80 s); nas demais, atingiu max_tokens=512 durante raciocínio. As falhas foram preservadas, sem notas inventadas. Parâmetros comuns: temperature 0, top_p 0,9, num_ctx 8192, seed 42."),
    p("Evidência auditável: evals/sprint4/results.json contém configurações, hashes, trechos, respostas, tokens, tempos, notas e saídas do julgador."),
    PageBreak()]

story += [p("3. Comparativo antes/depois", "H1x"),
    tabela([["Critério", "Sprints 1/2 — versão original", "Sprint 4 — RAG avaliado"], ["Embeddings", "Sem avaliação nomic reproduzível", "nomic-embed-text local"], ["Índice", "Busca inicial sem artefato medido", "ChromaDB persistente por hash"], ["Scores", "Não medidos; N/D", "v1: 0,705/0,428; v2: 0,876/0,654"], ["Contexto", "Base inicial e recuperação sem recall registrado", "Recall da fonte: 0,846 → 1,000"], ["Citações", "Não exigidas/medidas", "46,2% → 92,3%; validação contra fontes recuperadas"], ["Segurança", "Guardrails conversacionais básicos", "Recusa sem contexto e injection documental"], ["Interface", "Protótipo web", "Streamlit com tema, perfis e administração"], ["Reprodutibilidade", "Sem snapshot completo de avaliação", "Corpus, prompts, dataset, hashes e resultado bruto"]], [3.4*cm, 6.7*cm, 7.1*cm]),
    Spacer(1, 0.3*cm), p("Problema 1 — respostas sem fonte. Solução: IDs estáveis no contexto e pós-validação; resposta sem citação válida vira recusa. Motivo: impedir que uma frase fluente pareça comprovada sem evidência."),
    p("Problema 2 — Qwen truncava respostas. Decisão: manter a falha no comparativo e selecionar Llama, que concluiu 100%. Motivo: aumentar o limite depois da execução mudaria a configuração e invalidaria a comparação fixada."),
    p("Problema 3 — documentos curtos geraram poucos chunks. Decisão: registrar a limitação e manter chunking parametrizado para crescimento do corpus, sem inflar artificialmente os documentos."),
    PageBreak()]

story += [p("4. Equipe, entrega e limitações", "H1x"),
    p("A tabela mantém a divisão de responsabilidades planejada na Sprint anterior. Ela não substitui a confirmação das contribuições efetivamente realizadas nem o histórico Git."),
    tabela([["Integrante / RM", "Responsabilidade principal prevista"], ["Rodger Costa Rios · 571438", "Coordenação, integração da arquitetura e LCEL"], ["Felipe Pereira Restivo · 570712", "Interface e experiência de uso no Streamlit"], ["Gabriel Rodrigues Zappelloni · 572060", "RAG, ChromaDB e base de conhecimento"], ["Kenichi Caio Yamamoto · 569815", "PostgreSQL, modelos e persistência de sessões"], ["Maykon de Lima Silva · 574022", "Guardrails, evals, modelos e documentação"]], [6.2*cm, 11*cm]),
    Spacer(1, 0.3*cm), p("Limitações: corpus acadêmico pequeno; uma síntese HCA, não manual ChargeGrid; tarifa de demonstração não é preço real; julgador e modelo comparado compartilham a família Qwen; execução depende dos modelos Ollama previamente instalados."),
    p("Checklist: PDF com 5 páginas; relatorios RAG/modelos; interface; corpus; prompts v1/v2; resultados brutos; arquivo TXT; .env ignorado. Antes do envio, o grupo deve revisar este documento, confirmar contribuições reais, verificar o repositório público e conferir o histórico quanto a segredos."),
    p("Uso de IA generativa: houve auxílio no desenvolvimento, revisão técnica e documentação. O grupo permanece responsável por compreender, validar e apresentar a solução."),
    p("Repositório: https://github.com/rodgercr/ev-chargeops-assistant/tree/sprint-3"),
]

doc = SimpleDocTemplate(str(OUT), pagesize=A4, rightMargin=1.6*cm, leftMargin=1.6*cm, topMargin=1.5*cm, bottomMargin=1.7*cm, title="GoodWeAI — Relatório Sprint 4", author="Turma 1CCPK")
doc.build(story, onFirstPage=rodape, onLaterPages=rodape)
print(OUT)
