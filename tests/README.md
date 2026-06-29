# Testes

Verificações da aplicação. Execute sempre a partir da raiz do projeto, com o ambiente virtual ativo e as dependências instaladas (`pip install -r requirements.txt`).

## Integração Microsoft Entra ID

Teste de fumaça (smoke test) que valida imports, módulos, blueprint e a fábrica da aplicação:

```bash
# Linux/Mac
python tests/test_entra_id.py

# Windows
tests\test_entra_id.bat
```
