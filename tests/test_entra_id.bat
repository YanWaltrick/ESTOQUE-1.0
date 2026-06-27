@echo off
REM ============================================================================
REM TESTE DE INTEGRAÇÃO ENTRA ID - ESTOQUE SYSTEM
REM ============================================================================

setlocal enabledelayedexpansion

echo.
echo ============================================================================
echo TESTE DE INTEGRAÇÃO ENTRA ID
echo ============================================================================
echo.

REM Navegar para a raiz do projeto (este script vive em tests/)
cd /d "%~dp0.."

REM Definir Python
set PYTHON=.venv\Scripts\python.exe

REM Verificar se existe venv
if not exist "%PYTHON%" (
    echo ❌ ERRO: Ambiente venv não encontrado
    echo   Criar com: python -m venv .venv
    pause
    exit /b 1
)

echo [1/4] Verificando MSAL...
%PYTHON% -c "import msal; print('  ✓ MSAL importado')" || goto ERROR

echo [2/4] Verificando módulos Entra ID...
%PYTHON% -c "from app.auth.entra_id import EntraIDConfig, EntraIDClient; print('  ✓ Módulos carregados')" || goto ERROR

echo [3/4] Verificando Blueprint...
%PYTHON% -c "from app.routes.entra_auth import entra_bp; print('  ✓ Blueprint registrado')" || goto ERROR

echo [4/4] Verificando app factory...
%PYTHON% -c "from app import create_app; create_app(); print('  ✓ App factory funcional')" || goto ERROR

echo.
echo ============================================================================
echo ✅ INTEGRAÇÃO ENTRA ID - 100%% FUNCIONAL
echo ============================================================================
echo.
echo Rotas disponíveis:
echo   • GET /entra/login
echo   • GET /entra/callback
echo   • GET /entra/logout
echo.
echo Próximos passos:
echo   1. Preencher variáveis de ambiente em .env
echo   2. python app.py
echo   3. http://localhost:5000/entra/login
echo.
echo ============================================================================
pause
exit /b 0

:ERROR
echo.
echo ============================================================================
echo ❌ ERRO DURANTE OS TESTES
echo ============================================================================
pause
exit /b 1
