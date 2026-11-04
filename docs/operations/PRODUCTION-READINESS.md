# Plataforma — Homologação de segurança e operação (PR #14)

Esta entrega incorpora health/readiness no FastAPI, correlação de requisições por X-Request-ID, cabeçalhos contra sniffing, embedding e vazamento de referência, e Cache-Control no-store para respostas sensíveis. Um comando de preflight valida política de autenticação do navegador, origem HTTPS, segredo de sessão e chave MFA.

## Comandos
Na raiz do backend, com variáveis de ambiente de homologação seguras: python -m scripts.production_preflight

Verificar: GET /health/live (processo), GET /health/ready (consulta SELECT 1; devolve 503 se o banco estiver indisponível).

## Segurança
O preflight é uma validação estática: NÃO provisiona TLS, DNS, proxy, firewall ou banco. A infraestrutura de produção necessita operador, segredos externos ao Git, HTTPS válido, domínios/entidades, backups restaurados e monitoramento. Não usar credenciais e portas expostas do Compose demonstrativo em produção.

O middleware X-Request-ID aceita apenas ID ASCII alfanumérico curto ou gera novo UUID. Os cabeçalhos do API são aplicados em todas as respostas; revisar separadamente CSP da UI e política de cookies por domínio antes de exposição pública.

## Critério de aceite
CI de hardening aprovada; validação HTTP de probes, testes do backend completo e teste de proxy em ambiente TLS de homologação. Nenhum requisito de licitação deve ser marcado como demonstrável só por existir healthcheck.
