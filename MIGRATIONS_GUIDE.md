# Flask-Migrate - Versionamento de Banco de Dados

## O que é Flask-Migrate?

Flask-Migrate é uma ferramenta profissional para gerenciar evolução do schema do banco de dados usando Alembic (que é a biblioteca de migrações do SQLAlchemy).

**Beneficios:**
- Histórico completo de mudanças no banco de dados
- Fácil recuperação com `db upgrade` e `db downgrade`
- Controle de versão do schema
- Não perde dados quando o banco é deletado
- Funciona com MySQL, PostgreSQL, SQLite, etc.

## Estrutura de Migrações

```
migrations/
├── alembic.ini       # Configuração do Alembic
├── env.py            # Ambiente de execução das migrações
├── script.py.mako    # Template para novas migrações
├── versions/         # Pasta com todas as migrações
│   ├── 001_initial_migration.py
│   ├── 002_add_columns.py
│   └── ...
└── __init__.py
```

## Primeiros Passos

### 1. Inicializar as Migrações

Na primeira vez que você usar Flask-Migrate, execute:

```bash
python setup_migrations.py
```

Isso irá:
- Criar a pasta `migrations/` com a estrutura necessária
- Gerar a primeira migração baseada nos seus modelos
- Aplicar a migração ao banco de dados

### 2. Fazer Mudanças no Banco de Dados

Quando você fizer mudanças nos seus modelos (ex: adicionar/remover colunas), use:

```bash
# Detectar mudanças automaticamente e criar migração
python manage.py db migrate -m "Descricao da migracao"

# Exemplo:
python manage.py db migrate -m "Adicionar coluna email na tabela usuarios"
```

### 3. Aplicar Migrações

```bash
# Aplicar todas as migrações pendentes
python manage.py db upgrade
```

### 4. Reverter Migrações

```bash
# Reverter a ultima migracao
python manage.py db downgrade

# Ir para versao especifica
python manage.py db downgrade <revision>
```

## Comandos Disponíveis

```bash
# Ver versao atual do banco
python manage.py db current

# Ver historico completo de migracoes
python manage.py db history

# Atualizar para versao especifica
python manage.py db upgrade <revision>

# Mostrar informações sobre migracao
python manage.py db show <revision>
```

## Exemplo Pratico

### Passo 1: Adicionar Nova Coluna ao Modelo

Edite `app/models/__init__.py`:

```python
class Produto(db.Model):
    __tablename__ = 'produtos'
    
    id_produto = db.Column(db.String(50), primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    categoria = db.Column(db.String(100), nullable=False)
    preco = db.Column(db.Float, nullable=False)
    quantidade = db.Column(db.Integer, nullable=False, default=0)
    minimo = db.Column(db.Integer, nullable=False, default=0)
    localizacao = db.Column(db.String(255))
    sku = db.Column(db.String(50))  # <-- NOVA COLUNA
    # resto das colunas...
```

### Passo 2: Gerar Migração

```bash
python manage.py db migrate -m "Adicionar coluna SKU na tabela produtos"
```

Isso cria um arquivo em `migrations/versions/` com o comando SQL automaticamente gerado.

### Passo 3: Revisar a Migração (opcional)

Verifique o arquivo gerado em `migrations/versions/` para garantir que está correto.

### Passo 4: Aplicar a Migração

```bash
python manage.py db upgrade
```

Pronto! Seu banco foi atualizado com a nova coluna.

## Quando Usar Flask-Migrate

✅ **Use:**
- Em produção para controlar mudanças no banco
- Quando precisa de histórico de mudanças
- Para colaboração (múltiplos desenvolvedores)
- Para facilitar deploy em diferentes ambientes

❌ **Não use:**
- Em desenvolvimento inicial (quando o schema muda muito)
- Se você está criando um novo projeto (use `db.create_all()` uma unica vez)

## Dicas Importantes

1. **Sempre revise as migrações geradas** - Às vezes Alembic pode gerar código não ideal
2. **Commit as migrações no Git** - Trate as migrações como código
3. **Teste antes de aplicar em produção** - Sempre teste em ambiente de staging
4. **Use nomes descritivos** - `python manage.py db migrate -m "Adicionar coluna X"` é melhor que `-m "update"`
5. **Em desenvolvimento, você pode "pular" o Flask-Migrate** - Use `db.drop_all()` e `db.create_all()` se quiser recomeçar

## Recuperação de Desastres

Se você deletou o banco de dados inteiro (como acontecia com XAMPP):

```bash
# Recriar banco do zero
python manage.py db upgrade

# Pronto! Banco está recriado com todas as tabelas
```

Isso é bem mais rápido que recriara estrutura manualmente!

## Referência Rápida

| Comando | O que faz |
|---------|----------|
| `python setup_migrations.py` | Inicializa Flask-Migrate |
| `python manage.py db current` | Mostra versão atual |
| `python manage.py db history` | Mostra histórico |
| `python manage.py db migrate -m "msg"` | Cria nova migração |
| `python manage.py db upgrade` | Aplica migrações |
| `python manage.py db downgrade` | Reverte última migração |

---

Para mais informações, consulte:
- Flask-Migrate: https://flask-migrate.readthedocs.io/
- Alembic: https://alembic.sqlalchemy.org/
