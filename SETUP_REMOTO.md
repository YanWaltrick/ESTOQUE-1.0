# 🌐 Configuração para Acesso Remoto

## Resumo das Mudanças Realizadas

Foram feitas as seguintes mudanças para permitir acesso remoto ao sistema:

### 1. ✅ **app.py** (já estava correto)
```python
app.run(host='0.0.0.0', port=5000, debug=True)
```
- O Flask já estava configurado para escutar em `0.0.0.0` (todas as interfaces de rede)

### 2. ✅ **wsgi.py** (já estava correto)
```python
serve(app, host="0.0.0.0", port=5000)
```
- Waitress já estava configurado para modo produção remoto

### 3. ✅ **.env** (ATUALIZADO)
```env
# Novo: Hosts permitidos para acesso remoto
ALLOWED_HOSTS=localhost,127.0.0.1
```
- Adicionada variável para configurar hosts permitidos dinamicamente
- Você pode adicionar novos hosts aqui quando necessário

### 4. ✅ **app/routes/auth.py** (ATUALIZADO)
- Modificada função `url_has_allowed_host_and_scheme()` para:
  - Ler hosts permitidos da variável de ambiente `ALLOWED_HOSTS`
  - Permitir configuração dinâmica sem modificar código
  - Manter segurança contra open redirect vulnerabilities

---

## 📋 Como Usar em Outro PC

### **No PC Servidor (onde o app.py está rodando):**

#### **Passo 1: Descobrir o IP local**
```powershell
ipconfig
```
Procure por `IPv4 Address` (exemplo: `192.168.1.100`)

#### **Passo 2: Configurar hosts permitidos** (se necessário)

Edite o arquivo `.env`:
```env
# Adicionar o IP e nome do computador cliente
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.105,NOME_DO_PC_CLIENTE
```

#### **Passo 3: Garantir que o firewall permite porta 5000**

**Windows Firewall:**
```powershell
netsh advfirewall firewall add rule name="Flask 5000" dir=in action=allow protocol=tcp localport=5000
```

#### **Passo 4: Iniciar a aplicação**
```powershell
python app.py
```

Você verá:
```
 * Running on http://0.0.0.0:5000
 * WARNING: This is a development server. Do not use it in production deployment.
```

---

### **No PC Cliente (outro computador na rede):**

#### **Opção 1: Usar o IP local do servidor**
Abra o navegador e acesse:
```
http://192.168.1.100:5000
```

#### **Opção 2: Usar o nome do computador servidor** (se configurado)
```
http://NOME_DO_PC_SERVIDOR:5000
```

#### **Opção 3: Usar localhost** (se na mesma máquina)
```
http://localhost:5000
```

---

## 🔧 Troubleshooting

### ❌ "Não consegue conectar"
1. Verifique se ambos os PCs estão na **mesma rede WiFi/LAN**
2. Confirme que o servidor está rodando (`python app.py`)
3. Tente fazer ping do cliente para o servidor:
   ```powershell
   ping 192.168.1.100
   ```

### ❌ "ERR_BLOCKED_BY_CLIENT" ou "Conexão recusada"
1. Verifique o firewall do Windows no servidor
2. Execute como admin para liberar a porta:
   ```powershell
   netsh advfirewall firewall add rule name="Flask 5000" dir=in action=allow protocol=tcp localport=5000
   ```

### ❌ "Erro de redirecionamento de login"
1. Verifique se o IP/nome do cliente está em `ALLOWED_HOSTS` no `.env`
2. Exemplo de `.env` com múltiplos hosts:
   ```env
   ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.100,192.168.1.105
   ```

### ❌ "Banco de dados não encontrado"
O banco de dados está em `localhost:3306`. Se estiver em outro PC:
1. Edite `.env`:
   ```env
   DATABASE_URL=mysql+pymysql://mamute:QAZwsxEDCrfv@192.168.1.100:3306/estoque
   ```
2. Reinicie a aplicação

---

## 🚀 Para Produção (não recomendado com Flask padrão)

Use **Gunicorn** ou **Waitress**:

```powershell
# Instalar
pip install gunicorn

# Rodar em produção
gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
```

---

## ✅ Checklist Final

- [ ] IP do servidor identificado (`ipconfig`)
- [ ] Hosts permitidos configurados no `.env` (se necessário)
- [ ] Firewall permite porta 5000
- [ ] Aplicação rodando (`python app.py`)
- [ ] Pode conectar do cliente (`http://IP_SERVIDOR:5000`)
- [ ] Login funciona sem erros
- [ ] Sistema funciona normalmente

---

## 📝 Exemplo Completo

**Servidor PC-01 (192.168.1.100):**
```bash
cd c:\Users\Laboratorio\Desktop\apps vsCode\ESTOQUE\ESTOQUE-1.0
python app.py
```

**Cliente PC-02:**
Abre navegador: `http://192.168.1.100:5000`

✅ Pronto! Você está acessando o sistema remotamente!
