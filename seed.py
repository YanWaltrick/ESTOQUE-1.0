from werkzeug.security import generate_password_hash

from app import app, db
from models import Chamada, Historico, Movimentacao, Produto, User


def upsert_user(username, password, role="user"):
    user = User.query.filter_by(username=username).first()
    if user:
        user.role = role
        if not user.password.startswith("pbkdf2:sha256:"):
            user.password = generate_password_hash(password, method="pbkdf2:sha256")
        return user, False

    user = User(
        username=username,
        password=generate_password_hash(password, method="pbkdf2:sha256"),
        role=role,
    )
    db.session.add(user)
    return user, True


def upsert_product(data):
    product = db.session.get(Produto, data["id_produto"])
    if product:
        product.nome = data["nome"]
        product.categoria = data["categoria"]
        product.preco = data["preco"]
        product.quantidade = data["quantidade"]
        product.minimo = data["minimo"]
        product.localizacao = data["localizacao"]
        return product, False

    product = Produto(**data)
    db.session.add(product)
    return product, True


def ensure_movimentacao(id_produto, tipo, quantidade, motivo, usuario):
    movimentacao = Movimentacao.query.filter_by(
        id_produto=id_produto,
        tipo=tipo,
        quantidade=quantidade,
        motivo=motivo,
        usuario=usuario,
    ).first()
    if movimentacao:
        return False

    db.session.add(Movimentacao(id_produto, tipo, quantidade, motivo, usuario))
    return True


def ensure_chamada(id_usuario, mensagem, status="nova", lida=False):
    chamada = Chamada.query.filter_by(id_usuario=id_usuario, mensagem=mensagem).first()
    if chamada:
        chamada.status = status
        chamada.lida = lida
        return False

    chamada = Chamada(id_usuario=id_usuario, mensagem=mensagem)
    chamada.status = status
    chamada.lida = lida
    db.session.add(chamada)
    return True


def ensure_historico(tipo_evento, descricao, usuario_responsavel, detalhes=None):
    evento = Historico.query.filter_by(
        tipo_evento=tipo_evento,
        descricao=descricao,
        usuario_responsavel=usuario_responsavel,
    ).first()
    if evento:
        if detalhes:
            evento.detalhes = detalhes
        return False

    db.session.add(Historico(tipo_evento, descricao, usuario_responsavel, detalhes))
    return True


def run_seed():
    resumo = {
        "usuarios_criados": 0,
        "produtos_criados": 0,
        "movimentacoes_criadas": 0,
        "chamadas_criadas": 0,
        "historico_criado": 0,
    }

    with app.app_context():
        db.create_all()

        users = [
            {"username": "admin", "password": "admin", "role": "admin"},
            {"username": "operador", "password": "123456", "role": "user"},
            {"username": "estoquista", "password": "123456", "role": "user"},
            {"username": "compras", "password": "123456", "role": "user"},
            {"username": "suporte", "password": "123456", "role": "user"},
        ]

        for user_data in users:
            _, created = upsert_user(**user_data)
            if created:
                resumo["usuarios_criados"] += 1

        db.session.flush()

        products = [
            {
                "id_produto": "P-1001",
                "nome": "Notebook Dell Inspiron 15",
                "categoria": "Informatica",
                "preco": 3499.90,
                "quantidade": 8,
                "minimo": 3,
                "localizacao": "A1-P1",
            },
            {
                "id_produto": "P-1002",
                "nome": "Mouse Logitech M170",
                "categoria": "Perifericos",
                "preco": 89.90,
                "quantidade": 25,
                "minimo": 10,
                "localizacao": "A1-P2",
            },
            {
                "id_produto": "P-1003",
                "nome": "Teclado Mecanico Redragon",
                "categoria": "Perifericos",
                "preco": 249.90,
                "quantidade": 6,
                "minimo": 5,
                "localizacao": "A1-P3",
            },
            {
                "id_produto": "P-1004",
                "nome": "Monitor LG 24 Polegadas",
                "categoria": "Monitores",
                "preco": 799.90,
                "quantidade": 4,
                "minimo": 2,
                "localizacao": "B2-P1",
            },
            {
                "id_produto": "P-1005",
                "nome": "Cabo HDMI 2m",
                "categoria": "Acessorios",
                "preco": 39.90,
                "quantidade": 40,
                "minimo": 15,
                "localizacao": "B2-P4",
            },
            {
                "id_produto": "P-1006",
                "nome": "SSD Kingston 480GB",
                "categoria": "Armazenamento",
                "preco": 289.90,
                "quantidade": 14,
                "minimo": 6,
                "localizacao": "A2-P1",
            },
            {
                "id_produto": "P-1007",
                "nome": "HD Externo Seagate 1TB",
                "categoria": "Armazenamento",
                "preco": 419.90,
                "quantidade": 7,
                "minimo": 4,
                "localizacao": "A2-P2",
            },
            {
                "id_produto": "P-1008",
                "nome": "Memoria RAM 16GB DDR4",
                "categoria": "Componentes",
                "preco": 259.90,
                "quantidade": 11,
                "minimo": 8,
                "localizacao": "A2-P3",
            },
            {
                "id_produto": "P-1009",
                "nome": "Placa de Video RTX 4060",
                "categoria": "Componentes",
                "preco": 2399.90,
                "quantidade": 2,
                "minimo": 2,
                "localizacao": "A2-P4",
            },
            {
                "id_produto": "P-1010",
                "nome": "Roteador TP-Link AX1800",
                "categoria": "Redes",
                "preco": 379.90,
                "quantidade": 5,
                "minimo": 3,
                "localizacao": "C1-P1",
            },
            {
                "id_produto": "P-1011",
                "nome": "Switch Gigabit 8 Portas",
                "categoria": "Redes",
                "preco": 229.90,
                "quantidade": 3,
                "minimo": 4,
                "localizacao": "C1-P2",
            },
            {
                "id_produto": "P-1012",
                "nome": "Impressora HP Laser 107w",
                "categoria": "Impressao",
                "preco": 1199.90,
                "quantidade": 2,
                "minimo": 1,
                "localizacao": "C1-P3",
            },
            {
                "id_produto": "P-1013",
                "nome": "Toner HP 107A",
                "categoria": "Impressao",
                "preco": 219.90,
                "quantidade": 1,
                "minimo": 5,
                "localizacao": "C1-P4",
            },
            {
                "id_produto": "P-1014",
                "nome": "Webcam Logitech C920",
                "categoria": "Video",
                "preco": 449.90,
                "quantidade": 9,
                "minimo": 4,
                "localizacao": "B1-P1",
            },
            {
                "id_produto": "P-1015",
                "nome": "Headset HyperX Cloud Stinger",
                "categoria": "Audio",
                "preco": 199.90,
                "quantidade": 12,
                "minimo": 6,
                "localizacao": "B1-P2",
            },
            {
                "id_produto": "P-1016",
                "nome": "Filtro de Linha 6 Tomadas",
                "categoria": "Energia",
                "preco": 54.90,
                "quantidade": 18,
                "minimo": 10,
                "localizacao": "B1-P3",
            },
            {
                "id_produto": "P-1017",
                "nome": "Nobreak SMS 1200VA",
                "categoria": "Energia",
                "preco": 689.90,
                "quantidade": 1,
                "minimo": 2,
                "localizacao": "B1-P4",
            },
            {
                "id_produto": "P-1018",
                "nome": "Leitor de Codigo de Barras Elgin",
                "categoria": "Automacao",
                "preco": 329.90,
                "quantidade": 0,
                "minimo": 2,
                "localizacao": "C2-P1",
            },
        ]

        for product_data in products:
            _, created = upsert_product(product_data)
            if created:
                resumo["produtos_criados"] += 1

        db.session.flush()

        movimentacoes = [
            ("P-1001", "ENTRADA", 8, "Carga inicial para homologacao", "admin"),
            ("P-1002", "ENTRADA", 25, "Carga inicial para homologacao", "admin"),
            ("P-1003", "ENTRADA", 6, "Carga inicial para homologacao", "admin"),
            ("P-1004", "ENTRADA", 4, "Carga inicial para homologacao", "admin"),
            ("P-1005", "ENTRADA", 40, "Carga inicial para homologacao", "admin"),
            ("P-1006", "ENTRADA", 14, "Carga inicial para homologacao", "admin"),
            ("P-1007", "ENTRADA", 7, "Carga inicial para homologacao", "admin"),
            ("P-1008", "ENTRADA", 11, "Carga inicial para homologacao", "admin"),
            ("P-1009", "ENTRADA", 2, "Carga inicial para homologacao", "admin"),
            ("P-1010", "ENTRADA", 5, "Carga inicial para homologacao", "admin"),
            ("P-1011", "ENTRADA", 3, "Carga inicial para homologacao", "admin"),
            ("P-1012", "ENTRADA", 2, "Carga inicial para homologacao", "admin"),
            ("P-1013", "ENTRADA", 1, "Carga inicial para homologacao", "admin"),
            ("P-1014", "ENTRADA", 9, "Carga inicial para homologacao", "admin"),
            ("P-1015", "ENTRADA", 12, "Carga inicial para homologacao", "admin"),
            ("P-1016", "ENTRADA", 18, "Carga inicial para homologacao", "admin"),
            ("P-1017", "ENTRADA", 1, "Carga inicial para homologacao", "admin"),
            ("P-1003", "SAIDA", 1, "Teste de retirada interna", "operador"),
            ("P-1008", "SAIDA", 2, "Separacao para manutencao", "estoquista"),
            ("P-1013", "SAIDA", 1, "Ultimo toner alocado para impressora fiscal", "operador"),
            ("P-1017", "SAIDA", 1, "Equipamento reservado para infraestrutura", "compras"),
        ]

        for args in movimentacoes:
            if ensure_movimentacao(*args):
                resumo["movimentacoes_criadas"] += 1

        operador = User.query.filter_by(username="operador").first()
        estoquista = User.query.filter_by(username="estoquista").first()
        compras = User.query.filter_by(username="compras").first()
        suporte = User.query.filter_by(username="suporte").first()

        chamadas = [
            (
                operador,
                'Solicito ajuste de estoque para o produto "Teclado Mecanico Redragon".',
                "nova",
                False,
            ),
            (
                estoquista,
                'Produto "Toner HP 107A" abaixo do minimo e precisa de reposicao urgente.',
                "lida",
                True,
            ),
            (
                compras,
                'Favor analisar cotacao para reposicao do "Nobreak SMS 1200VA".',
                "analise",
                True,
            ),
            (
                suporte,
                'Leitor de codigo de barras sem saldo disponivel para testes de expedicao.',
                "execucao",
                True,
            ),
            (
                operador,
                'Reposicao de "Mouse Logitech M170" concluida e validada no setor comercial.',
                "concluida",
                True,
            ),
        ]

        for usuario, mensagem, status, lida in chamadas:
            if usuario and ensure_chamada(usuario.id, mensagem, status=status, lida=lida):
                resumo["chamadas_criadas"] += 1

        if ensure_historico(
            "seed_execucao",
            "Carga de dados de teste executada",
            "seed.py",
            detalhes="Usuarios, 18 produtos, movimentacoes e chamadas com status variados foram garantidos.",
        ):
            resumo["historico_criado"] += 1

        db.session.commit()

        total_usuarios = User.query.count()
        total_produtos = Produto.query.count()
        total_movimentacoes = Movimentacao.query.count()
        total_chamadas = Chamada.query.count()
        total_historico = Historico.query.count()
        produtos_abaixo_minimo = Produto.query.filter(Produto.quantidade < Produto.minimo).count()
        produtos_sem_estoque = Produto.query.filter(Produto.quantidade == 0).count()

    print("Seed concluido com sucesso.")
    print(
        "Criados agora: "
        f"{resumo['usuarios_criados']} usuarios, "
        f"{resumo['produtos_criados']} produtos, "
        f"{resumo['movimentacoes_criadas']} movimentacoes, "
        f"{resumo['chamadas_criadas']} chamadas, "
        f"{resumo['historico_criado']} eventos de historico."
    )
    print(
        "Totais atuais: "
        f"{total_usuarios} usuarios, "
        f"{total_produtos} produtos, "
        f"{total_movimentacoes} movimentacoes, "
        f"{total_chamadas} chamadas, "
        f"{total_historico} eventos de historico."
    )
    print(
        "Cenarios de estoque: "
        f"{produtos_abaixo_minimo} produtos abaixo do minimo e "
        f"{produtos_sem_estoque} produtos sem estoque."
    )
    print("Credenciais de teste: admin/admin, operador/123456, estoquista/123456")


if __name__ == "__main__":
    run_seed()
