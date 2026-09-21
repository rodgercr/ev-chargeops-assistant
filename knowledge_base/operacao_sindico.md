# Rotina operacional do síndico

O painel administrativo consolida eletropostos, sessões de carregamento, faturas e incidentes.
Ao analisar uma ocorrência, o síndico deve identificar o código do eletroposto, a data do
registro, o tipo do incidente e o status atual disponível no banco.

Dados operacionais do PostgreSQL local têm prioridade sobre este documento. O RAG fornece
orientações gerais; status, valores, moradores e medições devem vir das tabelas relacionais.

Quando faltar informação, o assistente deve indicar qual dado não foi encontrado em vez de
estimar ou preencher a resposta com números fictícios.
