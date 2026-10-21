# Painel web de carregadores

O painel faz parte do Streamlit existente. Não é necessário iniciar outro site,
instalar dependências adicionais nem recriar o banco.

## Acessar

1. Se o aplicativo já estava aberto durante a atualização, pare-o no terminal
   com Ctrl+C e execute novamente `executar.cmd`. O iniciador desativa a
   atualização automática de arquivos, então atualizar apenas o navegador pode
   não carregar o novo código.
2. Entre com uma conta ativa de perfil **admin**.
3. Abra o menu lateral e escolha **Gerenciar carregadores**.

O cadastro público continua criando somente moradores. Esta página não permite
que o usuário promova a própria conta para administrador.

## Funcionalidades

- **Visão geral:** código, localização, potência, tarifa e status dos carregadores,
  busca por código/localização e contadores da rede.
- **Novo carregador:** cadastra o equipamento diretamente no PostgreSQL local.
- **Editar carregador:** altera código, localização, potência, tarifa e status.
  A gravação exige marcar a confirmação e clicar em Salvar alterações.
- **Histórico de recargas:** consulta por carregador, período de início e status;
  mostra usuário, início/fim, duração, energia, tarifa aplicada, custo e status.
  Paginação de 25 registros; os totais consideram todo o filtro, não só a página.

## Regras importantes

- Código obrigatório e único, normalizado em letras maiúsculas; até 50 caracteres.
- Localização obrigatória; até 200 caracteres.
- Potência maior que zero, em kW; tarifa maior ou igual a zero, em R$/kWh.
- Status: online, offline, manutenção ou falha.
- A tarifa é a configuração usada nos próximos registros de recarga. Não há
  recálculo de tarifas, custos, sessões ou faturas já salvos.
- Alterar a potência modifica o cadastro no banco, não controla fisicamente um
  carregador. Não há integração de comando remoto de equipamento nesta página.
- O total de custo é o valor registrado nas sessões filtradas, não receita recebida.
- A data final do filtro inclui o dia inteiro; os horários são os gravados no banco.
- Recarregar dados descarta as alterações ainda não salvas do formulário.
- Se outra sessão editar o carregador enquanto o formulário estiver aberto,
  salvar é bloqueado até recarregar, evitando sobrescrever mudanças silenciosamente.
- Não foi adicionada exclusão de carregadores, para preservar relações com recargas,
  incidentes e faturas.

## Segurança e testes

O serviço reconsulta o usuário ativo e seu perfil no banco em cada operação.
Não confia apenas no perfil armazenado na tela. A página é restrita ao admin;
as permissões históricas da API para síndicos não foram ampliadas nem removidas.
Erros de banco aparecem na interface sem SQL, senha ou detalhes de conexão.
Cada escrita é transacional, com rollback em falhas.

Os testes de cadastro, alteração, permissões, histórico, concorrência e formulários
rodam em SQLite isolado; não cadastram carregadores de teste no PostgreSQL real.
Foi corrigido também o registro legado de recargas para respeitar tarifa zero,
sem substituí-la pela tarifa padrão.

```cmd
.venv\Scripts\python.exe -m pytest tests/test_admin_eletropostos.py tests/test_admin_carregadores_ui.py -q
```
