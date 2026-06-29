# Onboarding — rodando o Sistema ESTOQUE localmente

Guia passo a passo para colocar a aplicação de pé na sua máquina **do zero**. Se
é seu primeiro contato com o projeto, comece por aqui.

> **Escopo:** ambiente de **desenvolvimento local**. Para expor a aplicação a
> outras máquinas da rede, veja [`SETUP_REMOTO.md`](SETUP_REMOTO.md). Para a
> visão de arquitetura, veja [`ARQUITETURA.md`](ARQUITETURA.md).

Os comandos abaixo são para **Windows (PowerShell)**, o ambiente de referência do
time. Em macOS/Linux a única diferença prática é a ativação da venv
(`source .venv/bin/activate`); o restante é idêntico.

## Pré-requisitos

| Ferramenta | Versão | Para quê |
|------------|--------|----------|
| **Python** | 3.13 (fixado em [`mise.toml`](../mise.toml)) | Rodar a aplicação |
| **Docker Desktop** | recente | Subir o MySQL local (o projeto é 100% MySQL, sem fallback SQLite) |
| **Git** | qualquer | Clonar o repositório |

Instalação rápida no Windows via `winget`:

```powershell
winget install -e --id Python.Python.3.13
winget install -e --id Docker.DockerDesktop
```

> Depois de instalar o Docker Desktop, **abra-o uma vez** para o daemon iniciar
> (a primeira execução inicializa o backend WSL2).

## Passo a passo

### 1. Suba o MySQL

O [`compose.yml`](../compose.yml) já traz tudo configurado: banco `estoque_db`,
usuário de aplicação `estoque` / `estoque123`, na porta `3306`.

```powershell
docker compose up -d
```

Confirme que ficou `healthy` antes de seguir:

```powershell
docker compose ps
```

### 2. Crie a venv e instale as dependências

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> Se o seu `python` padrão não for o 3.13, aponte explicitamente para o
> interpretador correto ao criar a venv (ex.:
> `& "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe" -m venv .venv`).

### 3. Configure o `.env`

O [`.env.example`](../.env.example) vem com valores **de produção** — não copie
cru. Para desenvolvimento, o mínimo necessário é:

```env
FLASK_ENV=development
SECRET_KEY=qualquer-chave-para-dev
DATABASE_URL=mysql+pymysql://estoque:estoque123@127.0.0.1:3306/estoque_db?charset=utf8mb4
SESSION_COOKIE_SECURE=False
```

As demais variáveis (e-mail, Teams, Entra ID) são opcionais — deixe em branco se
não for usá-las. A lista completa está no `.env.example` e no
[`CLAUDE.md`](../CLAUDE.md).

### 4. Rode a aplicação

```powershell
python app.py
```

O boot aplica as migrations, garante o schema, e cria o usuário admin padrão se
ele não existir (ver `init_database()` em `app/database.py`).

### 5. Acesse

- **URL:** http://localhost:5000
- **Login:** `admin` / senha `admin`

> Troque a senha do admin assim que entrar.

## Verificação rápida

Tudo certo se:

- `docker compose ps` mostra `estoque-mysql` com status `healthy`.
- O console do `app.py` exibe `Banco de dados inicializado com sucesso` e
  `Running on http://127.0.0.1:5000`.
- http://localhost:5000/login responde a tela de login.

## Troubleshooting

### `docker-credential-desktop ... not found in %PATH%`
O `compose` não acha o helper de credenciais do Docker. Garanta que
`C:\Program Files\Docker\Docker\resources\bin` está no `PATH` (é onde mora o
`docker-credential-desktop.exe`). Para a sessão atual:

```powershell
$env:PATH = "C:\Program Files\Docker\Docker\resources\bin;" + $env:PATH
```

### `RuntimeError: SECRET_KEY ...` no boot
`SECRET_KEY` só é opcional quando `FLASK_ENV=development`. Confirme que essa
linha está no `.env` (ver passo 3).

### `Migracoes nao aplicadas (SystemExit: 1); seguindo inicializacao`
**Não é bloqueante.** Quando a aplicação das migrations do Alembic falha no boot,
o fallback (`_ensure_schema_columns()` + `db.create_all()`) monta o schema
mesmo assim — comportamento previsto (ver `CLAUDE.md`, seção *Banco de dados*). A
aplicação sobe normalmente.

### Porta 3306 já em uso
Já existe um MySQL local ocupando a porta. Pare o serviço conflitante ou ajuste o
mapeamento de portas no `compose.yml`.

### Não conecta no banco
Confirme que o container está de pé (`docker compose ps`) e que a `DATABASE_URL`
do `.env` aponta para `127.0.0.1:3306` com o usuário `estoque`.

## Comandos do dia a dia

```powershell
# Parar o banco (preserva os dados no volume)
docker compose down

# Zerar o banco (apaga o volume / recomeça do zero)
docker compose down -v

# Rodar os testes (exige o MySQL de pé — usa o banco estoque_test)
pip install -r requirements-dev.txt
pytest
```

## Próximos passos

- [`ARQUITETURA.md`](ARQUITETURA.md) — como o sistema é organizado.
- [`testes/README.md`](testes/README.md) — como escrever e rodar testes.
- [`SETUP_REMOTO.md`](SETUP_REMOTO.md) — acesso pela rede local.
- [`entra-id/SETUP.md`](entra-id/SETUP.md) — login corporativo via Microsoft Entra ID (opcional).
