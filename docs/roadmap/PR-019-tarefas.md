# PR 19 — Tarefas e tramitação de processos

Criação de tarefa vinculada a protocolo municipal ativo, atribuição a usuário da mesma entidade, prioridade e prazo, acompanhamento pessoal e atualização de situação com transições controladas (`aberta → em_andamento/concluida/cancelada`; `em_andamento → concluida/cancelada`). Conclusão e cancelamento são estados terminais. O responsável ou administrador executa a transição; outras pessoas não visualizam tarefas alheias. Auditoria de criação e mudanças.

**Uso:** Núcleo → Tarefas; selecione protocolo e responsável, cadastre; acesse a lista, filtre por situação, inicie e conclua. Teste `pytest tests/test_nucleo_tarefas.py -q`.

**Limites:** não há SLA configurável, escalonamento automático, calendário municipal de feriados, assinaturas digitais ou fila assíncrona. O acesso global por papel não está plenamente substituído por políticas de lotação por unidade. A etapa 20 adicionará notificações de atribuição.

POC: cobertura por requisito ainda não aferida.
