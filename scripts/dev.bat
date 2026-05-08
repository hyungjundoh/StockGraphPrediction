@echo off
REM Start FastAPI backend and Vite dev server.
REM Usage: scripts\dev.bat
setlocal
pushd "%~dp0\.."

REM Activate venv if present.
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat

REM LLM features are opt-in. Scrub ANTHROPIC_API_KEY from the backend env unless
REM ENABLE_LLM is explicitly set. Run as `set ENABLE_LLM=true && scripts\dev.bat`
REM (with ANTHROPIC_API_KEY also set) to turn the LLM endpoints back on.
if /I not "%ENABLE_LLM%"=="true" if not "%ENABLE_LLM%"=="1" set "ANTHROPIC_API_KEY="

echo [dev.bat] starting backend on :8000 (ENABLE_LLM=%ENABLE_LLM%)
start "risk-backend" cmd /c "python -m uvicorn api.main:app --reload --port 8000"

echo [dev.bat] starting frontend on :5173 (Ctrl-C here will stop the frontend)
cd web
call npm run dev

popd
endlocal
