# PR 20 — Notificações, atendimento interno e FAQ

## Fluxo operacional
1. Abra **Núcleo → Central**.
2. Consulte notificações pessoais e marque como lidas.
3. Abra um chamado, preenchendo assunto, descrição e prioridade; acompanhe sua situação.
4. Responda na conversa do chamado. Usuários veem somente os próprios chamados; administradores da entidade veem chamados da equipe e podem alterar o estado.
5. Quando o administrador cria tarefa atribuída a outro usuário, o responsável recebe notificação privada de tarefa.
6. Use a busca no FAQ, contendo orientações de login, MFA, unidades, cadastros, documentos, protocolo, tarefas, suporte, backups e limites regulatórios.

## Segurança
Chamados, mensagens e notificações são separados por `tenant_id`; leitura e marcação exigem identidade do destinatário; uma resposta é exibida somente após autorização no chamado. Auditoria de ações de suporte **não** inclui o texto da reclamação.

## Limitações
Não envia e-mail/SMS/WhatsApp, não implementa SLA contratual, encaminhamento à central externa, pesquisa de satisfação, anexos em chamado ou monitoramento 24h por agentes. FAQ é conteúdo de ajuda do produto, não substitui contrato ou normas. A resposta da equipe ainda depende de usuários administradores autenticados.

Teste: `pytest tests/test_nucleo_central.py -q`. Cobertura por requisito do TR permanece pendente.
