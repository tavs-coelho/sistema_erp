# Plano de Migração e Conversão de Dados

**Versão:** 1.0 | **Data:** 2026-04 | **Produto:** Sistema ERP Municipal

---

## 1. Objetivo

Definir as etapas, formatos, validações e responsabilidades para migrar/converter dados do sistema legado da prefeitura para o Sistema ERP Municipal.

---

## 2. Estratégia Geral

A migração adota a abordagem **ETL incremental** (Extract → Transform → Load) com fase de validação antes de cada carga definitiva:

```
Sistema Legado  →  Extração (CSV/SQL)  →  Transformação  →  Validação  →  Carga no ERP
```

Não há migração automatizada "cega": cada conjunto de dados passa por revisão de totais e amostras antes do load definitivo.

---

## 3. Escopo de Migração por Módulo

### 3.1 Dados obrigatórios para go-live

| Domínio | Tabela destino | Fonte típica | Prioridade |
|---|---|---|---|
| Contribuintes | `contribuintes` | Cadastro tributário legado (planilha ou SQL) | Alta |
| Imóveis (IPTU) | `imoveis_cadastrais` | CADIMO ou planilha de valores venais | Alta |
| Lançamentos tributários em aberto | `lancamentos_tributarios` | Relatório de débitos do exercício corrente | Alta |
| Dívida ativa ativa | `divida_ativa` | Relatório CDA vigente | Alta |
| Fornecedores | `vendors` | Cadastro de fornecedores (CNPJ, nome) | Alta |
| Exercício fiscal e dotações (LOA) | `fiscal_years`, `loa_items` | LOA aprovada (lei orçamentária) | Alta |
| Empenhos do exercício | `commitments` | SIAFI/SIGPBM ou planilha contábil | Alta |
| Contratos vigentes | `contracts` | Planilha de contratos ou sistema de contratos | Alta |
| Funcionários e cargos | `employees` | RH legado | Média |
| Convênios vigentes | `convenios` | SICONV ou planilha da secretaria de convênios | Média |

### 3.2 Dados opcionais (histórico)

| Domínio | Observação |
|---|---|
| Lançamentos tributários de exercícios anteriores | Importar apenas se necessário para auditoria |
| Histórico de pagamentos contábeis | Importar resumos anuais; não registros individuais |
| Patrimônio (bens móveis/imóveis) | Planilha de inventário patrimonial |

---

## 4. Formato de Arquivo para Extração

### 4.1 Contribuintes (CSV)

```
cpf_cnpj;nome;tipo;logradouro;numero;complemento;bairro;municipio;uf;cep;email;telefone
123.456.789-00;José da Silva;PF;Rua das Flores;100;;Centro;Municipio X;SP;01000-000;;
```

### 4.2 Imóveis Cadastrais (CSV)

```
inscricao;cpf_cnpj_contribuinte;logradouro;numero;complemento;bairro;area_terreno;area_construida;valor_venal;uso
01.001.0001.001;123.456.789-00;Rua das Flores;100;;Centro;250;120;180000;residencial
```

### 4.3 Lançamentos Tributários em Aberto (CSV)

```
cpf_cnpj;inscricao_imovel;tributo;competencia;exercicio;valor_principal;valor_juros;valor_multa;vencimento
123.456.789-00;01.001.0001.001;IPTU;2026-01;2026;1200.00;0;0;2026-03-31
```

### 4.4 Dívida Ativa (CSV)

```
numero_inscricao;cpf_cnpj;tributo;exercicio;valor_original;valor_atualizado;data_inscricao;status
DA-2024-001;123.456.789-00;IPTU;2024;900.00;990.00;2024-04-01;ativa
```

---

## 5. Processo de Transformação

### 5.1 Regras de limpeza

- Remover acentuação de campos-chave indexados (ex: bairro, logradouro) — apenas para indexação; preservar o texto original no campo de exibição.
- Normalizar CPF/CNPJ para formato `NNN.NNN.NNN-NN` (PF) e `NN.NNN.NNN/NNNN-NN` (PJ).
- Converter datas para ISO 8601 `YYYY-MM-DD`.
- Converter valores monetários para float com ponto decimal.
- Mapear status legados para os valores aceitos pelo ERP (ver tabela abaixo).

### 5.2 Mapeamento de status — Tributário

| Status legado | Status ERP |
|---|---|
| ABERTO / PENDENTE | `aberto` |
| PAGO / QUITADO | `pago` |
| INSCRITO / CDA | `inscrito_divida` |
| CANCELADO | `cancelado` |

### 5.3 Mapeamento de status — Contratos

| Status legado | Status ERP |
|---|---|
| ATIVO / EM VIGÊNCIA | `vigente` |
| ENCERRADO / FINALIZADO | `encerrado` |
| RESCINDIDO | `rescindido` |

---

## 6. Script de Carga (ETL)

Um script Python de migração será fornecido em `scripts/migrate_legacy.py`. Estrutura básica:

```python
# scripts/migrate_legacy.py
import csv
from app.db import SessionLocal
from app.models import Contribuinte, ImovelCadastral, LancamentoTributario, DividaAtiva

def load_contribuintes(path: str, db):
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter=";"):
            if not db.query(Contribuinte).filter_by(cpf_cnpj=row["cpf_cnpj"]).first():
                db.add(Contribuinte(**row))
    db.commit()

# ... repetir para demais entidades
```

---

## 7. Validação Pós-Migração

Após cada carga, executar as conferências abaixo antes de prosseguir.

### 7.1 Totais de controle

| Verificação | Como conferir |
|---|---|
| Total de contribuintes ativos | Comparar contagem ERP vs. relatório legado |
| Total de imóveis cadastrados | Comparar contagem ERP vs. CADIMO |
| Soma do valor venal total | Comparar soma `valor_venal` no ERP vs. planilha fiscal |
| Total de lançamentos em aberto | Comparar contagem e soma de valores |
| Total de dívida ativa (valor atualizado) | Comparar soma vs. CDA vigente |
| Total de contratos vigentes | Comparar lista ERP vs. planilha de contratos |

### 7.2 Amostragem

- Selecionar 30 contribuintes aleatoriamente e confirmar dados na tela do ERP.
- Selecionar 20 lançamentos e confirmar valores, vencimento e status.
- Selecionar 10 inscrições de dívida ativa e confirmar dados vs. CDA original.

---

## 8. Cronograma de Migração

| Semana | Atividade |
|---|---|
| S1 | Extração e validação dos arquivos CSV do sistema legado |
| S1–S2 | Transformação (limpeza, mapeamento, normalização) |
| S2 | Carga em ambiente de homologação; conferência de totais |
| S2–S3 | Validação por usuários-chave (amostragem) |
| S3 | Ajustes e reprocessamento de divergências |
| S4 | Carga definitiva em produção (go-live) |

---

## 9. Responsabilidades

| Responsável | Papel |
|---|---|
| DBA da prefeitura | Extração do sistema legado |
| Técnico ERP | Transformação e script de carga |
| Fiscal tributário | Validação de contribuintes e imóveis |
| Contador | Validação de empenhos, contratos e dotações |
| Coordenador de implantação | Aprovação final e assinatura do termo |
