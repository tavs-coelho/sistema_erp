from datetime import date, timedelta

from sqlalchemy.orm import Session

from .models import (
    AbonoFalta,
    Asset,
    AssetMovement,
    BudgetAllocation,
    Commitment,
    ConfiguracaoDepreciacao,
    ConfiguracaoIntegracaoPonto,
    ContaBancaria,
    Contract,
    Contribuinte,
    Department,
    Employee,
    EscalaServidor,
    FiscalYear,
    FundingSource,
    ImovelCadastral,
    IntegracaoPontoFolhaLog,
    LancamentoBancario,
    LancamentoDepreciacao,
    LancamentoTributario,
    Municipality,
    NotaFiscalServico,
    OperacaoITBI,
    PayrollEvent,
    Payment,
    Payslip,
    ProcurementProcess,
    Liquidation,
    RecalcularPayslipLog,
    RegistroPonto,
    RevenueEntry,
    RoleEnum,
    User,
    Vendor,
)
from .security import hash_password


def seed_data(db: Session):
    if db.query(User).first():
        _seed_nfse_itbi(db)
        _seed_ponto(db)
        _seed_depreciacao(db)
        _seed_integracao_ponto_folha(db)
        return

    db.add(Municipality(name="Município de Vila Esperança"))

    departments = [
        Department(name="Saúde"),
        Department(name="Educação"),
        Department(name="Administração"),
        Department(name="Obras"),
        Department(name="Assistência Social"),
    ]
    db.add_all(departments)
    db.flush()

    fy = FiscalYear(year=2026, active=True)
    db.add(fy)
    db.flush()

    employees = []
    for i in range(1, 21):
        employees.append(
            Employee(
                name=f"Servidor {i}",
                cpf=f"000.000.000-{i:02d}",
                job_title=["Analista", "Técnico", "Assistente"][i % 3],
                employment_type="Efetivo" if i % 2 == 0 else "Comissionado",
                base_salary=2500 + i * 120,
                department_id=departments[i % 5].id,
            )
        )
    db.add_all(employees)
    db.flush()

    roles = [
        RoleEnum.admin,
        RoleEnum.accountant,
        RoleEnum.hr,
        RoleEnum.procurement,
        RoleEnum.patrimony,
        RoleEnum.employee,
        RoleEnum.read_only,
    ]
    users = []
    for role in roles:
        for idx in range(1, 4):
            users.append(
                User(
                    username=f"{role.value}{idx}",
                    full_name=f"{role.value.title()} {idx}",
                    email=f"{role.value}{idx}@demo.local",
                    role=role,
                    hashed_password=hash_password("demo123"),
                    must_change_password=(idx == 1),
                    employee_id=employees[idx - 1].id if role == RoleEnum.employee else None,
                )
            )
    db.add_all(users)

    vendors = [Vendor(name=f"Fornecedor {i}", document=f"12.345.678/000{i:02d}") for i in range(1, 16)]
    db.add_all(vendors)
    db.flush()

    db.add_all(
        [
            BudgetAllocation(code=f"BA-{i:03d}", description=f"Dotação {i}", amount=50000 + i * 3000, fiscal_year_id=fy.id)
            for i in range(1, 6)
        ]
    )
    db.add_all([FundingSource(code=f"FS-{i:02d}", name=f"Fonte {i}") for i in range(1, 4)])

    commitments = []
    for i in range(1, 13):
        commitments.append(
            Commitment(
                number=f"EMP-2026-{i:03d}",
                description=f"Empenho de serviço {i}",
                amount=3000 + i * 700,
                fiscal_year_id=fy.id,
                department_id=departments[i % 5].id,
                vendor_id=vendors[i % 15].id,
                status="pago" if i <= 10 else "empenhado",
            )
        )
    db.add_all(commitments)
    db.flush()

    db.add_all(
        [
            Payment(
                commitment_id=commitments[i - 1].id,
                amount=commitments[i - 1].amount,
                payment_date=date.today() - timedelta(days=i * 3),
            )
            for i in range(1, 11)
        ]
    )

    processes = [ProcurementProcess(number=f"PROC-2026-{i:03d}", object_description=f"Processo licitatório {i}", status="homologado") for i in range(1, 9)]
    db.add_all(processes)
    db.flush()

    db.add_all(
        [
            Contract(
                number=f"CT-2026-{i:03d}",
                process_id=processes[i - 1].id,
                vendor_id=vendors[i % 15].id,
                start_date=date(2026, 1, 1) + timedelta(days=i * 5),
                end_date=date(2026, 12, 31) - timedelta(days=i * 10),
                amount=12000 + i * 2500,
                status="vigente" if i < 7 else "encerrado",
            )
            for i in range(1, 9)
        ]
    )

    db.add_all(
        [
            Asset(
                tag=f"PAT-{i:04d}",
                description=f"Bem patrimonial {i}",
                classification=["Mobiliário", "Informática", "Veículo"][i % 3],
                location=f"Sala {i%10 + 1}",
                department_id=departments[i % 5].id,
                responsible_employee_id=employees[i % 20].id,
                value=1000 + i * 250,
                status="ativo",
            )
            for i in range(1, 31)
        ]
    )

    # Cenário demo coerente de ponta a ponta (fácil de localizar na UI)
    demo_department = Department(name="Secretaria Demo Integrada")
    db.add(demo_department)
    db.flush()

    demo_vendor = Vendor(name="Fornecedor Demo Integrado", document="99.888.777/0001-66")
    db.add(demo_vendor)
    db.flush()

    db.add(
        BudgetAllocation(
            code="BA-DEMO-001",
            description="Dotação Demo Integrada",
            amount=120000,
            fiscal_year_id=fy.id,
        )
    )

    demo_commitment = Commitment(
        number="EMP-DEMO-001",
        description="Empenho Demo Integrado para demonstração",
        amount=15000,
        fiscal_year_id=fy.id,
        department_id=demo_department.id,
        vendor_id=demo_vendor.id,
        status="pago",
    )
    db.add(demo_commitment)
    db.flush()
    db.add(Liquidation(commitment_id=demo_commitment.id, amount=demo_commitment.amount))
    db.add(Payment(commitment_id=demo_commitment.id, amount=demo_commitment.amount, payment_date=date(2026, 4, 15)))

    demo_employee = employees[0]
    demo_payroll_event = PayrollEvent(
        employee_id=demo_employee.id,
        month="2026-04",
        kind="provento",
        description="Evento Demo Integrado",
        value=450,
    )
    db.add(demo_payroll_event)
    gross = demo_employee.base_salary + demo_payroll_event.value
    deductions = gross * 0.11
    db.add(Payslip(employee_id=demo_employee.id, month="2026-04", gross_amount=gross, deductions=deductions, net_amount=gross - deductions))

    demo_asset = Asset(
        tag="PAT-DEMO-001",
        description="Bem Demo Integrado (Notebook)",
        classification="Informática",
        location="Sala Demo 01",
        department_id=demo_department.id,
        responsible_employee_id=demo_employee.id,
        value=4200,
        status="ativo",
    )
    db.add(demo_asset)
    db.flush()
    db.add(
        AssetMovement(
            asset_id=demo_asset.id,
            from_department_id=demo_department.id,
            to_department_id=departments[0].id,
            movement_type="transferencia",
        )
    )
    demo_asset.department_id = departments[0].id
    demo_asset.location = "Sala Demo 02"
    demo_asset.responsible_employee_id = employees[1].id

    # ── Conciliação Bancária — dados demo ──────────────────────────────────────
    conta_movimento = ContaBancaria(
        banco="Banco do Brasil",
        agencia="0001-9",
        numero_conta="12345-6",
        descricao="Conta Movimento Geral",
        tipo="corrente",
        saldo_inicial=50000.0,
        data_saldo_inicial=date(date.today().year, 1, 1),
    )
    db.add(conta_movimento)
    conta_vinculada = ContaBancaria(
        banco="Caixa Econômica Federal",
        agencia="0050",
        numero_conta="99887-1",
        descricao="Conta Vinculada — Saúde",
        tipo="corrente",
        saldo_inicial=20000.0,
        data_saldo_inicial=date(date.today().year, 1, 1),
    )
    db.add(conta_vinculada)
    db.flush()

    # Lançamentos que têm correspondência direta com Payments (débito)
    # Reutilizar pagamentos do seed: commitments[0..9] têm payments
    # payments foram adicionados antes do flush final — requery
    payments_demo = db.query(Payment).limit(5).all()
    for i, pay in enumerate(payments_demo):
        # Lançamento bancário com valor exato e mesma data → será conciliado automaticamente
        db.add(LancamentoBancario(
            conta_id=conta_movimento.id,
            data_lancamento=pay.payment_date,
            tipo="debito",
            valor=pay.amount,
            descricao=f"Pagamento referente ao empenho (seed #{i+1})",
            documento_ref=f"TED{i+1:04d}",
            status="pendente",
        ))

    # Lançamentos de crédito com correspondência em RevenueEntry (se houver)
    rev_entries = db.query(RevenueEntry).limit(3).all()
    for i, rev in enumerate(rev_entries):
        db.add(LancamentoBancario(
            conta_id=conta_movimento.id,
            data_lancamento=rev.entry_date,
            tipo="credito",
            valor=rev.amount,
            descricao=f"Arrecadação {rev.description[:40]}",
            documento_ref=f"REC{i+1:04d}",
            status="pendente",
        ))

    # Lançamentos sem correspondência (tarifas, etc.) → permanecerão pendentes
    db.add(LancamentoBancario(
        conta_id=conta_movimento.id,
        data_lancamento=date(date.today().year, 1, 10),
        tipo="debito",
        valor=45.90,
        descricao="Tarifa de manutenção de conta",
        documento_ref="TAR0001",
        status="pendente",
    ))
    db.add(LancamentoBancario(
        conta_id=conta_movimento.id,
        data_lancamento=date(date.today().year, 2, 10),
        tipo="debito",
        valor=45.90,
        descricao="Tarifa de manutenção de conta",
        documento_ref="TAR0002",
        status="pendente",
    ))
    # Lançamento divergente demo: valor bate mas data difere em 7 dias
    if payments_demo:
        pay_div = payments_demo[0]
        db.add(LancamentoBancario(
            conta_id=conta_vinculada.id,
            data_lancamento=pay_div.payment_date + timedelta(days=7),
            tipo="debito",
            valor=pay_div.amount,
            descricao="Pagamento com atraso de compensação bancária (demo divergência)",
            documento_ref="DIVTST001",
            status="pendente",
        ))

    db.commit()
    _seed_nfse_itbi(db)
    _seed_ponto(db)
    _seed_depreciacao(db)
    _seed_integracao_ponto_folha(db)


def _seed_nfse_itbi(db: Session):
    """Seed de dados demo para NFS-e e ITBI."""
    if db.query(NotaFiscalServico).first():
        return

    year = date.today().year

    # Contribuintes demo
    prestador = Contribuinte(
        cpf_cnpj="11.222.333/0001-44",
        nome="Empresa de TI Ltda",
        tipo="PJ",
        email="ti@empresademo.local",
        municipio="Vila Esperança",
        uf="SP",
        cep="01310-000",
        logradouro="Av. Paulista",
        numero="1000",
        bairro="Bela Vista",
    )
    tomador = Contribuinte(
        cpf_cnpj="55.666.777/0001-88",
        nome="Órgão Público Demo",
        tipo="PJ",
        email="compras@orgaodemo.local",
        municipio="Vila Esperança",
        uf="SP",
        cep="01310-100",
        logradouro="Rua Boa Vista",
        numero="200",
        bairro="Centro",
    )
    pf_vendedor = Contribuinte(
        cpf_cnpj="766.543.210-99",
        nome="Maria Vendedora Demo",
        tipo="PF",
        municipio="Vila Esperança",
        uf="SP",
        cep="01000-000",
        logradouro="Rua Demo",
        numero="5",
        bairro="Jardim Demo",
    )
    pf_comprador = Contribuinte(
        cpf_cnpj="544.321.098-77",
        nome="João Comprador Demo",
        tipo="PF",
        municipio="Vila Esperança",
        uf="SP",
        cep="01000-100",
        logradouro="Rua Demo",
        numero="7",
        bairro="Jardim Demo",
    )
    db.add_all([prestador, tomador, pf_vendedor, pf_comprador])
    db.flush()

    # Imóvel para ITBI
    imovel_itbi = ImovelCadastral(
        inscricao="DEMO-ITBI-001",
        contribuinte_id=pf_vendedor.id,
        logradouro="Rua das Palmeiras",
        numero="300",
        bairro="Jardim Novo",
        area_terreno=250.0,
        area_construida=120.0,
        valor_venal=280000.0,
        uso="residencial",
    )
    db.add(imovel_itbi)
    db.flush()

    # NFS-e #1: serviço de consultoria — ISS 2 %
    valor_servico_1 = 5000.0
    aliquota_1 = 2.0
    iss_1 = round(valor_servico_1 * aliquota_1 / 100, 2)
    lanc_nfse_1 = LancamentoTributario(
        contribuinte_id=prestador.id,
        imovel_id=None,
        tributo="ISS",
        competencia=f"{year}-03",
        exercicio=year,
        valor_principal=iss_1,
        valor_total=iss_1,
        vencimento=date(year, 3, 20),
        observacoes="ISS gerado automaticamente pela NFS-e (competência " + f"{year}-03)",
    )
    db.add(lanc_nfse_1)
    db.flush()
    nfse_1 = NotaFiscalServico(
        numero=f"NFS/{year}-0001",
        prestador_id=prestador.id,
        tomador_id=tomador.id,
        descricao_servico="Consultoria em tecnologia da informação e suporte de sistemas",
        codigo_servico="1.01",
        competencia=f"{year}-03",
        data_emissao=date(year, 3, 15),
        valor_servico=valor_servico_1,
        valor_deducoes=0.0,
        aliquota_iss=aliquota_1,
        valor_iss=iss_1,
        retencao_fonte=False,
        status="emitida",
        lancamento_id=lanc_nfse_1.id,
        observacoes="NFS-e demo — consultoria",
    )
    db.add(nfse_1)

    # NFS-e #2: serviço de manutenção — ISS 3 %, com retenção na fonte
    valor_servico_2 = 3200.0
    aliquota_2 = 3.0
    iss_2 = round(valor_servico_2 * aliquota_2 / 100, 2)
    lanc_nfse_2 = LancamentoTributario(
        contribuinte_id=prestador.id,
        imovel_id=None,
        tributo="ISS",
        competencia=f"{year}-04",
        exercicio=year,
        valor_principal=iss_2,
        valor_total=iss_2,
        vencimento=date(year, 4, 20),
        observacoes="ISS gerado automaticamente pela NFS-e (competência " + f"{year}-04)",
    )
    db.add(lanc_nfse_2)
    db.flush()
    nfse_2 = NotaFiscalServico(
        numero=f"NFS/{year}-0002",
        prestador_id=prestador.id,
        tomador_id=tomador.id,
        descricao_servico="Manutenção preventiva de equipamentos de informática",
        codigo_servico="14.01",
        competencia=f"{year}-04",
        data_emissao=date(year, 4, 10),
        valor_servico=valor_servico_2,
        valor_deducoes=0.0,
        aliquota_iss=aliquota_2,
        valor_iss=iss_2,
        retencao_fonte=True,
        status="emitida",
        lancamento_id=lanc_nfse_2.id,
        observacoes="NFS-e demo — manutenção, ISS retido na fonte",
    )
    db.add(nfse_2)

    # ITBI #1: compra e venda — alíquota 2 %, valor declarado < valor venal (usa venal como base)
    valor_declarado = 250000.0
    valor_venal_ref = 280000.0  # imovel_itbi.valor_venal
    base_calc = max(valor_declarado, valor_venal_ref)
    aliquota_itbi = 2.0
    valor_devido = round(base_calc * aliquota_itbi / 100, 2)
    lanc_itbi = LancamentoTributario(
        contribuinte_id=pf_comprador.id,
        imovel_id=imovel_itbi.id,
        tributo="ITBI",
        competencia=f"{year}-04",
        exercicio=year,
        valor_principal=valor_devido,
        valor_total=valor_devido,
        vencimento=date(year, 4, 30),
        observacoes="ITBI gerado automaticamente para operação compra_venda",
    )
    db.add(lanc_itbi)
    db.flush()
    itbi_1 = OperacaoITBI(
        numero=f"ITBI/{year}-0001",
        transmitente_id=pf_vendedor.id,
        adquirente_id=pf_comprador.id,
        imovel_id=imovel_itbi.id,
        natureza_operacao="compra_venda",
        data_operacao=date(year, 4, 5),
        valor_declarado=valor_declarado,
        valor_venal_referencia=valor_venal_ref,
        base_calculo=base_calc,
        aliquota_itbi=aliquota_itbi,
        valor_devido=valor_devido,
        status="aberto",
        lancamento_id=lanc_itbi.id,
        observacoes="ITBI demo — compra e venda residencial",
    )
    db.add(itbi_1)

    db.commit()


def _seed_ponto(db: Session):
    """Seed de dados demo para ponto e frequência."""
    if db.query(EscalaServidor).first():
        return

    # Usa funcionários já existentes no seed
    employees = db.query(Employee).all()
    if not employees:
        return

    year = date.today().year
    month = date.today().month
    # Usar mês anterior para ter histórico completo
    if month == 1:
        ano_ref, mes_ref = year - 1, 12
    else:
        ano_ref, mes_ref = year, month - 1

    emp1 = employees[0]
    emp2 = employees[1] if len(employees) > 1 else None

    # Escala padrão para emp1
    escala1 = EscalaServidor(
        employee_id=emp1.id,
        horas_dia=8.0,
        dias_semana="12345",
        hora_entrada="08:00",
        hora_saida="17:00",
        hora_inicio_intervalo="12:00",
        hora_fim_intervalo="13:00",
    )
    db.add(escala1)

    if emp2:
        # Escala 6h para emp2
        escala2 = EscalaServidor(
            employee_id=emp2.id,
            horas_dia=6.0,
            dias_semana="12345",
            hora_entrada="07:00",
            hora_saida="13:00",
            hora_inicio_intervalo="10:00",
            hora_fim_intervalo="10:15",
        )
        db.add(escala2)

    db.flush()

    import calendar as _cal
    _, days_in_ref_month = _cal.monthrange(ano_ref, mes_ref)

    # Registros para emp1: dias úteis do mês de referência
    for day in range(1, days_in_ref_month + 1):
        d = date(ano_ref, mes_ref, day)
        if d.weekday() >= 5:  # sábado / domingo
            continue

        if day == 5:
            # Falta no dia 5 — sem registro
            continue
        if day == 10:
            # Atraso de 25 min no dia 10
            hora_entrada = "08:25"
        else:
            hora_entrada = "08:00"

        if day == 15:
            # Hora extra: sai às 19h
            hora_saida = "19:00"
        else:
            hora_saida = "17:00"

        for tipo, hora in [
            ("entrada", hora_entrada),
            ("inicio_intervalo", "12:00"),
            ("fim_intervalo", "13:00"),
            ("saida", hora_saida),
        ]:
            db.add(RegistroPonto(
                employee_id=emp1.id,
                data=d,
                tipo_registro=tipo,
                hora_registro=hora,
                origem="demo",
                observacoes="seed demo",
            ))

    # Abono para a falta do dia 5
    data_falta = date(ano_ref, mes_ref, 5)
    if data_falta.weekday() < 5:  # só se for dia útil
        db.add(AbonoFalta(
            employee_id=emp1.id,
            data=data_falta,
            tipo="falta",
            motivo="Consulta médica — atestado apresentado",
            status="aprovado",
        ))

    db.commit()


def _seed_depreciacao(db: Session):
    """Seed de dados demo para depreciação patrimonial."""
    if db.query(ConfiguracaoDepreciacao).first():
        return

    assets = db.query(Asset).filter(Asset.status == "ativo").all()
    if not assets:
        return

    # Classes NBCASP e parâmetros de referência
    _classes = {
        "veiculo":    {"vida_util_meses": 60,  "residual_pct": 0.10},
        "maquina":    {"vida_util_meses": 120, "residual_pct": 0.10},
        "movel":      {"vida_util_meses": 120, "residual_pct": 0.10},
        "equipamento": {"vida_util_meses": 60, "residual_pct": 0.05},
        "imovel":     {"vida_util_meses": 300, "residual_pct": 0.20},
    }

    today = date.today()
    # Simular aquisição 24 meses atrás para ter histórico
    from dateutil.relativedelta import relativedelta as _rd
    data_aquisicao_24m = today - _rd(months=24)

    cfgs_adicionadas = 0
    for i, asset in enumerate(assets[:6]):   # máx 6 bens para demo
        # Escolhe parâmetros pelo índice para variar
        classe_key = list(_classes.keys())[i % len(_classes)]
        params = _classes[classe_key]
        valor_aquisicao = asset.value if asset.value and asset.value > 0 else 10000.0
        valor_residual = round(valor_aquisicao * params["residual_pct"], 2)
        metodo = "saldo_decrescente" if i % 2 == 1 else "linear"

        cfg = ConfiguracaoDepreciacao(
            asset_id=asset.id,
            data_aquisicao=data_aquisicao_24m.date() if hasattr(data_aquisicao_24m, "date") else data_aquisicao_24m,
            valor_aquisicao=valor_aquisicao,
            vida_util_meses=params["vida_util_meses"],
            valor_residual=valor_residual,
            metodo=metodo,
            ativo=True,
        )
        db.add(cfg)
        cfgs_adicionadas += 1

    db.flush()

    # Gerar lançamentos para os últimos 12 meses (histórico)
    from app.routers.depreciacao import _processar_bem as _proc
    all_cfgs = db.query(ConfiguracaoDepreciacao).all()

    for delta_m in range(12, 0, -1):
        p_date = today - _rd(months=delta_m)
        periodo = f"{p_date.year}-{p_date.month:02d}"
        for cfg in all_cfgs:
            try:
                _proc(db, cfg, periodo, None)
            except Exception:
                pass

    db.commit()


def _seed_integracao_ponto_folha(db: Session):
    """Seed de dados demo para integração ponto → folha."""
    if db.query(ConfiguracaoIntegracaoPonto).first():
        return

    employees = db.query(Employee).all()
    if not employees:
        return

    # Configura integração para todos os servidores ativos (até 4 para demo)
    for i, emp in enumerate(employees[:4]):
        # Varia a configuração entre servidores para demonstrar
        cfg = ConfiguracaoIntegracaoPonto(
            employee_id=emp.id,
            desconto_falta_diaria=None,      # proporcional ao salário
            percentual_hora_extra=50.0 if i % 2 == 0 else 100.0,
            desconto_atraso=True,
            ativo=True,
        )
        db.add(cfg)

    db.commit()
