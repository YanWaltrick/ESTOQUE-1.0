# Quick Start - Sistema de Estoque

## ⚡ Começar em 30 Segundos

### Sem Docker (Local)
```bash
pip install -r requirements.txt
python init_db_simple.py
python app.py
```

Acesse: http://127.0.0.1:5000

---

### Com Docker (Recomendado) 🐳

**Pré-requisito:** Instale [Docker Desktop](https://www.docker.com/products/docker-desktop)

```bash
docker-compose up
```

Acesse: http://localhost:5000

---

## Login Padrão

O sistema agora possui **autenticação segura com RBAC**:

```
Admin (Total acesso):
  Usuário: admin
  Senha: Admin@123

Gerente (Gerenciar estoque):
  Usuário: gerente
  Senha: Gerente@123

Operador (Registrar movimentação):
  Usuário: operador
  Senha: Operador@123

Usuário (Apenas visualizar):
  Usuário: usuario
  Senha: Usuario@123
```

**🔐 Segurança:**
- Proteção contra força bruta (bloqueio após 5 tentativas)
- Senhas criptografadas com PBKDF2-SHA256
- Auditoria completa de acessos
- Controle de permissões por role

---

## Próximos Passos

1. Explore a interface
2. Crie produtos no estoque
3. Registre entrada/saída
4. Veja relatórios

---

## Problemas?

### Com Docker:
```bash
# Ver logs
docker-compose logs -f

# Entrar no container
docker-compose exec flask-app bash

# Reiniciar
docker-compose restart
```

### Sem Docker:
```bash
# Verificar Python
python --version

# Reinstalar dependências
pip install -r requirements.txt --force-reinstall

# Resetar banco
rm instance/estoque.db
python init_db_simple.py
```

---

## Documentação Completa

- [DOCUMENTATION_INDEX.md](./DOCUMENTATION_INDEX.md) - índice de todos os docs
- [README.md](./README.md) - Visão geral do projeto
- [RBAC_GUIDE.md](./RBAC_GUIDE.md) - Autenticação, Autorização e Segurança
- [ARCHITECTURE.md](./ARCHITECTURE.md) - Estrutura do projeto
- [DOCKER_GUIDE.md](./DOCKER_GUIDE.md) - Guia detalhado de Docker
- [MIGRATIONS_GUIDE.md](./MIGRATIONS_GUIDE.md) - Como gerenciar banco de dados

---

**Pronto para começar?** 🚀
