import json
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional


def now_gmt3():
    return datetime.now(timezone(timedelta(hours=-3)))
from database import db
from models import Produto, Movimentacao, Categoria

class EstoqueDB:
    """Classe para gerenciar o estoque usando banco de dados SQLite"""

    def __init__(self):
        self._migrar_dados_json()

    def _migrar_dados_json(self):
        """Migra dados do JSON para o banco se existir"""
        arquivo_json = "dados_estoque.json"
        if os.path.exists(arquivo_json) and not self._banco_tem_dados():
            try:
                print("Migrando dados do JSON para banco de dados...")
                with open(arquivo_json, 'r', encoding='utf-8') as f:
                    dados = json.load(f)

                for id_prod, prod_dict in dados.items():
                    produto = Produto(
                        id_produto=id_prod,
                        nome=prod_dict["nome"],
                        categoria=prod_dict["categoria"],
                        preco=prod_dict["preco"],
                        quantidade=prod_dict["quantidade"],
                        minimo=prod_dict["minimo"],
                        localizacao=prod_dict.get("localizacao", "")
                    )
                    db.session.add(produto)

                db.session.commit()
                print(f"Migracao concluida: {len(dados)} produtos transferidos")

                # Backup do arquivo JSON
                backup_file = f"{arquivo_json}.backup"
                os.rename(arquivo_json, backup_file)
                print(f"✓ Backup criado: {backup_file}")

            except Exception as e:
                print(f"✗ Erro na migração: {e}")
                db.session.rollback()

    def _banco_tem_dados(self):
        """Verifica se o banco já tem dados"""
        try:
            return Produto.query.count() > 0
        except:
            return False

    def adicionar_produto(self, id_produto: str, nome: str, categoria: str,
                         preco: float, quantidade: int, minimo: int,
                         localizacao: str = "") -> bool:
        """Adiciona um novo produto ao estoque"""
        try:
            if Produto.query.get(id_produto):
                print(f"✗ Produto com ID '{id_produto}' já existe!")
                return False

            if preco <= 0 or quantidade < 0:
                print("✗ Preço e quantidade devem ser positivos!")
                return False

            produto = Produto(id_produto, nome, categoria, preco, quantidade, minimo, localizacao)
            db.session.add(produto)
            db.session.commit()

            print(f"✓ Produto '{nome}' adicionado com sucesso!")
            return True

        except Exception as e:
            db.session.rollback()
            print(f"✗ Erro ao adicionar produto: {e}")
            return False

    def remover_produto(self, id_produto: str) -> bool:
        """Remove um produto do estoque"""
        try:
            produto = Produto.query.get(id_produto)
            if not produto:
                print(f"✗ Produto com ID '{id_produto}' não encontrado!")
                return False

            nome = produto.nome
            db.session.delete(produto)
            db.session.commit()

            print(f"✓ Produto '{nome}' removido com sucesso!")
            return True

        except Exception as e:
            db.session.rollback()
            print(f"✗ Erro ao remover produto: {e}")
            return False

    def buscar_produto(self, id_produto: str) -> Optional[Produto]:
        """Busca um produto pelo ID"""
        return Produto.query.get(id_produto)

    def listar_produtos(self) -> List[Produto]:
        """Retorna lista de todos os produtos"""
        return Produto.query.all()

    def atualizar_quantidade(self, id_produto: str, nova_quantidade: int) -> bool:
        """Atualiza a quantidade de um produto"""
        try:
            produto = Produto.query.get(id_produto)
            if not produto:
                print(f"✗ Produto com ID '{id_produto}' não encontrado!")
                return False

            if nova_quantidade < 0:
                print("✗ Quantidade não pode ser negativa!")
                return False

            produto.quantidade = nova_quantidade
            db.session.commit()

            print(f"✓ Quantidade atualizada para {nova_quantidade} unidades!")
            return True

        except Exception as e:
            db.session.rollback()
            print(f"✗ Erro ao atualizar quantidade: {e}")
            return False

    def entrada_estoque(self, id_produto: str, quantidade: int, motivo: str = "", usuario: str = "") -> bool:
        """Registra entrada de produtos no estoque"""
        try:
            produto = Produto.query.get(id_produto)
            if not produto:
                print(f"✗ Produto com ID '{id_produto}' não encontrado!")
                return False

            if quantidade <= 0:
                print("✗ Quantidade deve ser maior que zero!")
                return False

            produto.quantidade += quantidade

            # Registrar movimentação
            movimentacao = Movimentacao(id_produto, 'ENTRADA', quantidade, motivo, usuario)
            db.session.add(movimentacao)

            db.session.commit()
            print(f"✓ {quantidade} unidades adicionadas ao estoque!")
            return True

        except Exception as e:
            db.session.rollback()
            print(f"✗ Erro na entrada de estoque: {e}")
            return False

    def saida_estoque(self, id_produto: str, quantidade: int, motivo: str = "", usuario: str = "") -> bool:
        """Registra saída de produtos do estoque"""
        try:
            produto = Produto.query.get(id_produto)
            if not produto:
                print(f"✗ Produto com ID '{id_produto}' não encontrado!")
                return False

            if quantidade <= 0:
                print("✗ Quantidade deve ser maior que zero!")
                return False

            if produto.quantidade < quantidade:
                print(f"✗ Estoque insuficiente! Disponível: {produto.quantidade}")
                return False

            produto.quantidade -= quantidade

            # Registrar movimentação
            movimentacao = Movimentacao(id_produto, 'SAIDA', quantidade, motivo, usuario)
            db.session.add(movimentacao)

            db.session.commit()
            print(f"✓ {quantidade} unidades removidas do estoque!")
            return True

        except Exception as e:
            db.session.rollback()
            print(f"✗ Erro na saída de estoque: {e}")
            return False

    def atualizar_produto(self, id_produto: str, **dados) -> bool:
        """Atualiza dados de um produto"""
        try:
            produto = Produto.query.get(id_produto)
            if not produto:
                print(f"✗ Produto com ID '{id_produto}' não encontrado!")
                return False

            # Atualizar campos permitidos com conversão de tipos
            if 'nome' in dados:
                produto.nome = str(dados['nome'])
            if 'categoria' in dados:
                produto.categoria = str(dados['categoria'])
            if 'preco' in dados:
                produto.preco = float(dados['preco'])
            if 'quantidade' in dados:
                produto.quantidade = int(dados['quantidade'])
            if 'minimo' in dados:
                produto.minimo = int(dados['minimo'])
            if 'localizacao' in dados:
                produto.localizacao = str(dados['localizacao'])

            produto.data_atualizacao = now_gmt3()
            db.session.commit()
            print(f"✓ Produto '{id_produto}' atualizado com sucesso!")
            return True

        except Exception as e:
            db.session.rollback()
            print(f"✗ Erro ao atualizar produto: {e}")
            return False

    def relatorio_estoque_baixo(self) -> List[Produto]:
        """Retorna produtos com estoque abaixo do mínimo"""
        return Produto.query.filter(Produto.quantidade < Produto.minimo).all()

    def relatorio_valor_total(self) -> Dict:
        """Retorna estatísticas do valor total do estoque"""
        try:
            produtos = Produto.query.all()
            valor_total = sum(p.quantidade * p.preco for p in produtos)
            total_produtos = len(produtos)
            total_unidades = sum(p.quantidade for p in produtos)

            return {
                'valor_total': valor_total,
                'total_produtos': total_produtos,
                'total_unidades': total_unidades
            }
        except Exception as e:
            print(f"✗ Erro no relatório: {e}")
            return {'valor_total': 0, 'total_produtos': 0, 'total_unidades': 0}

    def relatorio_por_categoria(self) -> Dict:
        """Retorna relatório agrupado por categoria"""
        try:
            from sqlalchemy import func
            resultado = db.session.query(
                Produto.categoria,
                func.count(Produto.id_produto).label('total_produtos'),
                func.sum(Produto.quantidade).label('total_unidades'),
                func.sum(Produto.quantidade * Produto.preco).label('valor_total')
            ).group_by(Produto.categoria).all()

            return {row.categoria: {
                'total_produtos': row.total_produtos,
                'total_unidades': row.total_unidades,
                'valor_total': row.valor_total
            } for row in resultado}

        except Exception as e:
            print(f"✗ Erro no relatório por categoria: {e}")
            return {}

    def get_movimentacoes(self, id_produto: str = None, limit: int = 50) -> List[Movimentacao]:
        """Retorna histórico de movimentações"""
        try:
            query = Movimentacao.query.order_by(Movimentacao.data_movimentacao.desc())
            if id_produto:
                query = query.filter_by(id_produto=id_produto)
            return query.limit(limit).all()
        except Exception as e:
            print(f"✗ Erro ao buscar movimentações: {e}")
            return []