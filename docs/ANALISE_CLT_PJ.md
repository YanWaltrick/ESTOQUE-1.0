# Análise Completa: Sistema de Gerenciamento de Usuários CLT vs PJ

## Resumo Executivo

O projeto ESTOQUE utiliza um sistema de gerenciamento de usuários que diferencia entre dois tipos de contrato:
- **CLT**: Colaborador com vínculo direto à empresa
- **PJ**: Colaborador com contrato de prestação de serviços (Pessoa Jurídica)

O sistema implementa validações, campos específicos, interfaces adaptadas e APIs para cada tipo de contrato.

---

## 1. ESTRUTURA DE MODELOS DE DADOS

### Localização: [app/models/__init__.py](app/models/__init__.py#L1)

#### Classe User (SQLAlchemy)

**Campos Compartilhados (para ambos CLT e PJ):**
```python
id                    # Chave primária (Integer)
username              # Identificador único (String 150)
password              # Hash seguro (String 255)
role                  # RBAC: 'admin' ou 'usuario' (String 50)
tipo_contrato         # 'CLT' ou 'PJ' (String 10, default='CLT')
area                  # Área da empresa (String 255)
localizacao           # Cidade (String 255)
ativo                 # Status ativo/bloqueado (Boolean)
data_criacao          # Timestamp de criação (DateTime)
data_atualizacao      # Timestamp de atualização (DateTime)
foto_perfil           # Nome do arquivo de avatar (String 255)
ultimo_login          # Último login bem-sucedido (DateTime)
tentativas_login_falhas # Para detecção de força bruta (Integer)
bloqueado_ate         # Bloqueio temporário até data (DateTime)
```

#### Campos Específicos para CLT:
```python
empresa               # Nome da empresa (String 255)
cnpj                  # CNPJ da empresa (String 18)
endereco              # Endereço (String 500)
cargo                 # Cargo/posição (String 255)
cpf                   # CPF do colaborador (String 14)
data_admissao         # Data de admissão (Date)
departamento          # Departamento (String 255)
local_trabalho        # Local de trabalho específico (String 255)
```

#### Campos Específicos para PJ:
```python
pj_contratante        # Nome empresa contratante (String 255)
pj_contratante_cnpj   # CNPJ contratante (String 18)
pj_contratante_endereco # Endereço contratante (String 500)
pj_contratada         # Nome PJ contratada (String 255)
pj_contratada_cnpj    # CNPJ PJ contratada (String 18)
pj_data_contrato      # Data do contrato (Date)
```

#### Método `__init__`:
O construtor recebe TODOS os parâmetros (CLT e PJ) e:
- Valida `tipo_contrato` (default 'CLT', normalizado para UPPERCASE)
- Faz `.strip()` em todas as strings
- Armazena campos PJ mesmo para usuários CLT (como vazio '')
- Inicializa `ativo=True` por padrão

#### Método `to_dict()`:
Serializa todo usuário para dicionário JSON, incluindo:
- Todos os campos CLT
- Todos os campos PJ
- Datas formatadas como "dd/mm/yyyy"
- Retorna sem a senha (por segurança)

---

## 2. CARREGAMENTO E PREENCHIMENTO DE USUÁRIOS CLT

### Fluxo de Criação de CLT

#### **Rota:** [app/routes/admin.py - criar_usuario()](app/routes/admin.py#L82)

**Passos:**

1. **Captura de Campos CLT do Formulário:**
   ```python
   area = request.form.get('area', '').strip()
   localizacao = request.form.get('localizacao', '').strip()
   empresa = request.form.get('empresa', '').strip()
   cnpj = request.form.get('cnpj', '').strip()
   endereco = request.form.get('endereco', '').strip()
   cargo = request.form.get('cargo', '').strip()
   cpf = request.form.get('cpf', '').strip()
   departamento = request.form.get('departamento', '').strip()
   local_trabalho = request.form.get('local_trabalho', '').strip()
   data_admissao_str = request.form.get('data_admissao', '').strip()
   ```

2. **Conversão de Data:**
   ```python
   data_admissao = None
   if data_admissao_str:
       try:
           data_admissao = datetime.strptime(data_admissao_str, '%Y-%m-%d').date()
       except:
           flash('Erro ao processar a data de admissão.', 'error')
           return redirect(url_for('admin.criar_usuario'))
   ```

3. **Validações:**
   - Username é validado via `validate_username(username)`
   - Verifica se username já existe: `User.query.filter_by(username=username).first()`
   - Senha validada via `PasswordValidator.validate(password)`
   - Role validado: deve estar em `['admin', 'usuario']`
   - Tipo de contrato validado: deve estar em `['CLT', 'PJ']`
   - **Para CLT**: Nenhuma validação extra obrigatória (todos campos opcionais)

4. **Criação do Objeto User:**
   ```python
   novo_usuario = User(
       username=username,
       password=PasswordValidator.hash_password(password),
       role=role,
       tipo_contrato='CLT',
       area=area,
       localizacao=localizacao,
       empresa=empresa,
       cnpj=cnpj,
       endereco=endereco,
       cargo=cargo,
       cpf=cpf,
       data_admissao=data_admissao,
       departamento=departamento,
       local_trabalho=local_trabalho
       # Campos PJ não são passados (ficam vazios)
   )
   ```

5. **Persistência:**
   ```python
   db.session.add(novo_usuario)
   db.session.flush()  # Gera ID antes de commit
   
   # Criar automaticamente Termo de Entrega
   termo = TermoEntrega(
       id_usuario=novo_usuario.id,
       empresa=empresa,
       cnpj=cnpj,
       endereco=endereco,
       nome_colaborador=username,
       cargo_funcao=cargo,
       cpf_cnpj=cpf,
       departamento=departamento,
       local_trabalho=local_trabalho,
       data_admissao=data_admissao
   )
   db.session.add(termo)
   db.session.commit()
   ```

6. **Registro de Evento:**
   ```python
   registrar_evento(
       tipo_evento='usuario_criado',
       descricao=f'Novo usuário criado: "{username}" com role "{role}" e Termo de Entrega gerado',
       usuario_responsavel=current_user.username
   )
   ```

### Fluxo de Edição de CLT

#### **Rota:** [app/routes/admin.py - editar_usuario()](app/routes/admin.py#L209)

**Diferenças em relação à criação:**
- Carrega usuário existente: `usuario = User.query.get_or_404(user_id)`
- Mantém valores anteriores se campo vazio: `request.form.get('campo', usuario.campo).strip()`
- Não pode editar a si mesmo (proteção de segurança)
- Pode alterar entre CLT e PJ (muda apenas `tipo_contrato`)
- Valida campo `ativo` como checkbox: `ativo = request.form.get('ativo') == 'on'`
- Atualiza cada campo do objeto: `usuario.campo = novo_valor`
- Faz um único `db.session.commit()` ao final

---

## 3. TRATAMENTO DE USUÁRIOS PJ

### Fluxo de Criação de PJ

#### **Rota:** [app/routes/admin.py - criar_usuario()](app/routes/admin.py#L82)

**Passos Específicos para PJ:**

1. **Captura de Campos PJ do Formulário:**
   ```python
   pj_contratante = request.form.get('pj_contratante', '').strip()
   pj_contratante_cnpj = request.form.get('pj_contratante_cnpj', '').strip()
   pj_contratante_endereco = request.form.get('pj_contratante_endereco', '').strip()
   pj_contratada = request.form.get('pj_contratada', '').strip()
   pj_contratada_cnpj = request.form.get('pj_contratada_cnpj', '').strip()
   pj_data_contrato_str = request.form.get('pj_data_contrato', '').strip()
   ```

2. **Conversão de Data do Contrato PJ:**
   ```python
   pj_data_contrato = None
   if pj_data_contrato_str:
       try:
           pj_data_contrato = datetime.strptime(pj_data_contrato_str, '%Y-%m-%d').date()
       except:
           flash('Erro ao processar a data do contrato PJ.', 'error')
           return redirect(url_for('admin.criar_usuario'))
   ```

3. **Validações PJ:**
   ```python
   if tipo_contrato == 'PJ':
       if not pj_contratante or not pj_contratante_cnpj:
           flash('Para contrato PJ, informe Contratante e CNPJ do Contratante.', 'error')
           return redirect(url_for('admin.criar_usuario'))
   ```
   - **Campos obrigatórios para PJ:** `pj_contratante` e `pj_contratante_cnpj`
   - Demais campos PJ são opcionais

4. **Criação do Objeto User (PJ):**
   ```python
   novo_usuario = User(
       # ... campos básicos ...
       tipo_contrato='PJ',
       # Não passa campos CLT (ficam vazios)
       pj_contratante=pj_contratante,
       pj_contratante_cnpj=pj_contratante_cnpj,
       pj_contratante_endereco=pj_contratante_endereco,
       pj_contratada=pj_contratada,
       pj_contratada_cnpj=pj_contratada_cnpj,
       pj_data_contrato=pj_data_contrato
   )
   ```

5. **Persistência (sem Termo de Entrega):**
   ```python
   db.session.add(novo_usuario)
   db.session.commit()
   # NOTA: PJ não gera Termo de Entrega automaticamente
   ```

### Fluxo de Edição de PJ

**Semelhante à edição CLT, mas com campos PJ:**
```python
pj_contratante = request.form.get('pj_contratante', usuario.pj_contratante).strip()
pj_contratante_cnpj = request.form.get('pj_contratante_cnpj', usuario.pj_contratante_cnpj).strip()
# ... demais campos ...

usuario.pj_contratante = pj_contratante
usuario.pj_contratante_cnpj = pj_contratante_cnpj
# ... demais campos ...

db.session.commit()
```

### API de Criação de Usuário PJ

#### **Rota:** [app/routes/api.py - criar_usuario_api()](app/routes/api.py#L376)

**Diferenças em relação ao fluxo web:**
- Não suporta campos PJ via API (falta implementação)
- API apenas cria CLT atualmente:
  ```python
  tipo_contrato = (dados.get('tipo_contrato') or 'CLT').strip().upper()
  # ... validação ...
  novo_usuario = User(
      # ... campos CLT apenas ...
      tipo_contrato=tipo_contrato  # Mas aceita 'PJ' se informado
  )
  ```
- **BUG/LIMITAÇÃO:** API valida tipo_contrato mas não captura/processa campos PJ

---

## 4. DIFERENÇAS ESTRUTURAIS ENTRE CLT E PJ

### Tabela Comparativa

| Aspecto | CLT | PJ |
|---------|-----|-----|
| **Campo tipo_contrato** | 'CLT' | 'PJ' |
| **Campos Obrigatórios** | Nenhum | `pj_contratante`, `pj_contratante_cnpj` |
| **Campos Opcionais (CLT)** | `empresa`, `cnpj`, `endereco`, `cargo`, `cpf`, `data_admissao`, `departamento`, `local_trabalho` | Não utilizados (vazios) |
| **Campos Opcionais (PJ)** | Não utilizados (vazios) | `pj_contratante_endereco`, `pj_contratada`, `pj_contratada_cnpj`, `pj_data_contrato` |
| **Geração Termo Entrega** | ✅ Automático | ❌ Não |
| **Armazenamento Banco** | Mesma tabela `users` | Mesma tabela `users` |
| **Modo UI** | Campos CLT visíveis | Campos PJ visíveis |
| **Ordenação Listagem** | Primeiro (0) | Segundo (1) |

### Migração CLT ↔ PJ

**É possível alterar tipo de contrato em edição:**
1. CLT → PJ: Limpar campos CLT, preencher PJ
2. PJ → CLT: Limpar campos PJ, preencher CLT
3. Campos não utilizados persistem no banco (compatibilidade)

---

## 5. LOCALIZAÇÃO: TEMPLATES E ROTAS

### ESTRUTURA DE ROTAS

#### Rotas Admin (RBAC)

**Arquivo:** [app/routes/admin.py](app/routes/admin.py)

| Rota | Método | Função | Permissão |
|------|--------|--------|-----------|
| `/admin/users` | GET | `listar_usuarios()` | manage_users |
| `/admin/users/create` | GET/POST | `criar_usuario()` | create_user |
| `/admin/users/<id>/edit` | GET/POST | `editar_usuario(id)` | manage_users |
| `/admin/users/<id>/delete` | POST | `deletar_usuario(id)` | delete_user |

**Decoradores de Proteção:**
```python
@admin_bp.before_request
@login_required
@require_role('admin')
def before_admin_request():
    """Proteger todas as rotas admin"""
    pass
```

#### Rotas API

**Arquivo:** [app/routes/api.py](app/routes/api.py)

| Rota | Método | Função | Autenticação |
|------|--------|--------|-------------|
| `/api/users` | GET | `get_users()` | login_required + admin |
| `/api/users/<id>` | GET | `get_user_details(id)` | login_required + admin |
| `/api/users` | POST | `criar_usuario_api()` | login_required + admin |
| `/api/users/<id>` | DELETE | `deletar_usuario_api(id)` | login_required + admin |

**Ordenação Padrão na API:**
```python
usuarios = User.query.order_by(
    case((User.tipo_contrato == 'CLT', 0), else_=1),  # CLT primeiro
    User.ativo.desc(),  # Ativos primeiro
    User.username.asc()  # Alfabético
).all()
```

---

### TEMPLATES E INTERFACES

#### Template de Listagem

**Arquivo:** [templates/admin/usuarios.html](templates/admin/usuarios.html)

**Funcionalidades:**
- Lista usuários com paginação (10 por página)
- Busca por username (case-insensitive)
- Filtro por tipo de contrato: "TODOS", "CLT", "PJ"
- Exibe para cada usuário:
  - Foto de perfil (avatar)
  - **Badge com tipo_contrato** (CLT/PJ)
  - Username
  - Role (ADMIN/USUÁRIO)
  - Status (Bloqueado se inativo)
  - Área, localização, data de criação

**Query String Suportada:**
```
/admin/users?page=1&q=usuario&tipo=CLT
```

#### Template de Criação de Usuário (Dual-Mode)

**Arquivo:** [templates/admin/user_form.html](templates/admin/user_form.html) (modo 'create')

**Fluxo UI:**

1. **Fase 1 - Campos Iniciais:**
   - Username (obrigatório)
   - Tipo de Contrato (obrigatório) - dropdown CLT/PJ

2. **Evento: onChange do tipo_contrato**
   ```javascript
   function toggle(){
     const val = (tipo.value||'').toUpperCase();
     if (val === 'PJ'){
       pjFields.style.display = 'block';      // Mostra campos PJ
       cltFields.style.display = 'none';      // Esconde campos CLT
     } else if (val === 'CLT'){
       cltFields.style.display = 'block';     // Mostra campos CLT
       pjFields.style.display = 'none';       // Esconde campos PJ
     } else {
       // Ambos escondidos até seleção
       cltFields.style.display = 'none';
       pjFields.style.display = 'none';
     }
     // Mostra/esconde senha e role
     pwd.style.display = '';
     role.style.display = '';
   }
   tipo.addEventListener('change', toggle);
   ```

3. **Fase 2 - Campos Condicionais (após seleção):**

   **Se CLT:**
   - Senha (obrigatório após seleção)
   - Role (obrigatório)
   - Empresa, CNPJ, Endereço, Cargo, CPF, Data Admissão, Departamento, Local Trabalho

   **Se PJ:**
   - Senha (obrigatório após seleção)
   - Role (obrigatório)
   - Contratante, CNPJ Contratante, Endereço Contratante, Contratada, CNPJ Contratada, Data Contrato

**Design Visual:**
- Seção CLT tem **borda azul** (`border-left: 3px solid #198754`)
- Seção PJ tem **borda verde** (`border-left: 3px solid #0d6efd`)
- Campos organizados em divs com `id="clt-fields"` e `id="pj-fields"`

#### Template de Edição de Usuário

**Arquivo:** [templates/admin/user_form.html](templates/admin/user_form.html) (modo 'edit')

**Diferenças em relação à criação:**
- Username pré-preenchido (não editável neste template)
- Campos pré-preenchidos com valores do usuário
- Permite trocar entre CLT e PJ (limpa campos antigos)
- Checkbox "Ativo" para bloquear/desbloquear
- Mesma lógica JavaScript de toggle

#### Template Admin Dashboard (Criação Inline)

**Arquivo:** [templates/admin.html](templates/admin.html) - linha ~50

**Criação Inline com AJAX:**
- Formulário `form-adicionar-usuario` com integração JavaScript
- Mesma estrutura de toggle que user_form.html
- Campos CLT com border esquerda verde
- Campos PJ com border esquerda azul
- Validação frontend antes de envio

---

## 6. FLUXO DE DADOS: VISUALIZAÇÃO COMPLETA

### Diagrama: Criação de Usuário (Simplificado)

```
┌─────────────────────────────────────────────────────┐
│ Templates (admin.html ou user_form.html)           │
│ ├─ Username + Tipo Contrato (inicial)              │
│ └─ Toggle JavaScript baseado em tipo_contrato      │
└─────────────────────────────────────────────────────┘
                       ↓
         Usuário seleciona CLT ou PJ
                       ↓
    ┌──────────────────┴──────────────────┐
    ↓                                      ↓
  ┌────────────────┐           ┌──────────────────┐
  │ Campos CLT     │           │ Campos PJ        │
  │ (Empresa)      │           │ (Contratante)    │
  │ (CPF)          │           │ (CNPJ Contrat.)  │
  │ (Cargo)        │           │ (Data Contrato)  │
  │ (Data Admissão)│           │ ...              │
  └────────────────┘           └──────────────────┘
         ↓                             ↓
    [POST] /admin/users/create    [POST] /admin/users/create
    └─────────────────────────────────────────┘
                       ↓
        Routes (app/routes/admin.py)
        criar_usuario() ou editar_usuario()
                       ↓
        ┌──────────────────────────────────────┐
        │ Validações                           │
        │ - Username unique                    │
        │ - Senha forte                        │
        │ - Se PJ: contratante + CNPJ req     │
        └──────────────────────────────────────┘
                       ↓
        ┌──────────────────────────────────────┐
        │ Criação Objeto User                  │
        │ Model: app/models/__init__.py        │
        │ - Inicializa __init__                │
        │ - Armazena tipo_contrato             │
        │ - Limpa campos não-utilizados com '' │
        └──────────────────────────────────────┘
                       ↓
        ┌──────────────────────────────────────┐
        │ Persistência (SQLAlchemy)            │
        │ - db.session.add(novo_usuario)       │
        │ - db.session.flush() (gera ID)       │
        │ - Se CLT: TermoEntrega criado        │
        │ - db.session.commit()                │
        └──────────────────────────────────────┘
                       ↓
        ┌──────────────────────────────────────┐
        │ Auditoria                            │
        │ - registrar_evento() chamado         │
        │ - Tipo: 'usuario_criado'             │
        │ - Descrição: detalhes do usuário     │
        └──────────────────────────────────────┘
                       ↓
        Redirect: /admin/users (lista atualizada)
```

---

## 7. ARQUIVOS E LOCALIZAÇÃO RESUMIDA

### Modelo de Dados
- **[app/models/__init__.py](app/models/__init__.py)** - Classe User (linha 13-200)
  - Definição de campos CLT/PJ
  - Método `__init__`
  - Método `to_dict()`

### Rotas Web
- **[app/routes/admin.py](app/routes/admin.py)** 
  - `criar_usuario()` (GET/POST) - linha 82
  - `editar_usuario()` (GET/POST) - linha 209
  - `deletar_usuario()` (POST) - linha 275
  - `listar_usuarios()` (GET) - linha 43

### API REST
- **[app/routes/api.py](app/routes/api.py)**
  - `get_users()` (GET) - linha 65
  - `get_user_details()` (GET) - linha 79
  - `criar_usuario_api()` (POST) - linha 376
  - `deletar_usuario_api()` (DELETE) - linha ~475

### Templates
- **[templates/admin.html](templates/admin.html)** - Dashboard admin com criação inline
  - Formulário `form-adicionar-usuario` - linha 50
  - Campos CLT - linha 70+
  - Campos PJ - linha 138+

- **[templates/admin/user_form.html](templates/admin/user_form.html)** - Formulário criar/editar
  - Modo create/edit - linha 8
  - Toggle JavaScript - linha 126+
  - Campos CLT - linha 45+
  - Campos PJ - linha 80+

- **[templates/admin/usuarios.html](templates/admin/usuarios.html)** - Listagem de usuários
  - Display tipo_contrato - linha 53
  - Filtros CLT/PJ - linha 25+

### Migrações
- **[migrations/versions/f1a2b3c4d5e6_add_tipo_contrato_to_users.py](migrations/versions/f1a2b3c4d5e6_add_tipo_contrato_to_users.py)**
  - Adição do campo `tipo_contrato`
  - Valor padrão: 'CLT'

---

## 8. OBSERVAÇÕES IMPORTANTES

### ✅ Implementado Corretamente
1. Separação clara de campos CLT e PJ
2. Validação de campos obrigatórios por tipo
3. UI responsiva com toggle JavaScript
4. Ordenação CLT antes de PJ na listagem
5. Historicidade com `registrar_evento()`
6. Armazenamento eficiente (mesma tabela)
7. Proteção com RBAC e permissões

### ⚠️ Limitações/Gaps
1. **API não suporta campos PJ** - criar_usuario_api() não captura dados PJ
2. **PJ não gera Termo de Entrega** - Apenas CLT gera
3. **Campos vazios persistem** - PJ guarda campos CLT vazios e vice-versa
4. **Sem validação de CNPJ/CPF** - Aceita qualquer string
5. **Sem filtro de tipo na API** - GET /api/users retorna ambos sem filtro

### 💡 Sugestões de Melhoria
1. Adicionar suporte PJ na API
2. Implementar Termo de Entrega para PJ
3. Validar formato de CNPJ/CPF antes de salvar
4. Adicionar endpoint `/api/users?tipo=PJ` para filtro
5. Criar índice no banco para `tipo_contrato` (melhora filtros)
6. Limpeza de campos não-utilizados ao salvar (dados mais limpos)

---

## 9. SEQUÊNCIA DE EXECUÇÃO NA CRIAÇÃO

### Timeline Completo

```
1. Usuário acessa: /admin/users/create

2. Template renderizado: user_form.html (modo='create')
   - Form vazio
   - JavaScript listener ativado
   - Campos CLT e PJ ocultos

3. Usuário escolhe tipo_contrato = "CLT"
   - JavaScript toggle() executado
   - Mostra #clt-fields
   - Esconde #pj-fields

4. Usuário preenche:
   - username: "joao.silva"
   - password: "Senha123!"
   - role: "usuario"
   - empresa: "Acme Corp"
   - cpf: "123.456.789-00"
   - data_admissao: "2026-05-27"
   - ... demais campos CLT ...

5. Clica "Salvar"
   - POST /admin/users/create
   - Content-Type: application/x-www-form-urlencoded

6. Backend: criar_usuario()
   - Captura todos os fields
   - Valida username único
   - Valida senha
   - Converte data_admissao
   - tipo_contrato validado = 'CLT'

7. Criação User object:
   User(
       username="joao.silva",
       password=hash("Senha123!"),
       tipo_contrato='CLT',
       empresa="Acme Corp",
       cpf="123.456.789-00",
       data_admissao=date(2026,5,27),
       # pj_contratante='', pj_contratante_cnpj='', etc (vazios)
   )

8. Flush/Commit:
   - INSERT INTO users (...) VALUES (...)
   - novo_usuario.id = 42 (gerado)

9. TermoEntrega criado automaticamente:
   TermoEntrega(id_usuario=42, empresa="Acme Corp", ...)

10. Auditoria:
    registrar_evento(
        tipo_evento='usuario_criado',
        descricao='Novo usuário criado: "joao.silva" com role "usuario" e Termo de Entrega gerado'
    )

11. Flash message: "Usuário criado com sucesso"

12. Redirect: /admin/users
    - Usuário "joao.silva" visível na lista com badge "CLT"
```

---

## Conclusão

O sistema ESTOQUE implementa um gerenciamento robusto de usuários CLT vs PJ com:
- **Separação lógica clara** de dados por tipo de contrato
- **UI intuitiva** com toggle JavaScript
- **Backend validador** com regras específicas
- **Persistência unificada** em tabela `users`
- **Auditoria completa** de operações

O código está bem estruturado para manutenção e expansão, com poucas limitações técnicas que não impactam o funcionamento core.
