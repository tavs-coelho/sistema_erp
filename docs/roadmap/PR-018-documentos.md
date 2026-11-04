# PR 18 — Gestão eletrônica de documentos e versionamento

**Fluxo:** Núcleo → Documentos → Novo registro (código, título, classificação, protocolo opcional), cadastrar; selecione o documento e envie arquivo PDF/JPG/PNG/TXT até 8 MB; consulte histórico de versões e baixe a versão desejada. Cada envio gera checksum SHA-256 e auditoria sem armazenar conteúdo do documento nos logs.

**Proteção:** documentos e versões por entidade; acesso `restrito` apenas ao criador ou administrador; escrita por perfis administrativos autorizados, somente pelo criador ou administrador. Validação de assinatura PDF/imagem, tamanho, nomes sanitizados e chave aleatória de armazenamento; download sempre exige autorização.

**Teste:** `pytest tests/test_nucleo_documentos.py -q` com upload e download reais contra diretório temporário, duas entidades e perfis.

**Pendências:** antivírus/antimalware, assinatura eletrônica e validade jurídica, política de classificação mais granular por secretaria, indexação/OCR, retenção e descarte LGPD, storage externo, backup consistente dos anexos e auditoria de consulta. Não declarar GED homologado para produção ou requisitos do edital satisfeitos.
