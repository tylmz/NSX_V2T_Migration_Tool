@echo off
REM Build NSX Migration for VCD (patched 1.4.2.2.H001) on Windows - run from CMD in this folder
REM Prereqs: Python 3.8 x64 (py launcher), Win64 OpenSSL installed in C:\Program Files\OpenSSL-Win64
setlocal
set OPENSSL_BIN=C:\Program Files\OpenSSL-Win64\bin

py -3.8 -m venv venv || goto :error
call venv\Scripts\activate.bat || goto :error
python -m pip install --upgrade "pip<24" "setuptools<60" wheel || goto :error
pip install -r requirements_build.txt || goto :error
pip install -r src\requirements-windows.txt || goto :error

python -m PyInstaller --noconfirm src\vcdNSXMigrator.spec || goto :error

if exist "%OPENSSL_BIN%\openssl.exe" (
    xcopy "%OPENSSL_BIN%\*" dist\vcdNSXMigrator\ /E /Y /Q >nul
) else (
    echo WARNING: openssl.exe not found in %OPENSSL_BIN% - certificate checks will fail unless openssl is on PATH
)
copy /Y PATCHES.md dist\vcdNSXMigrator\ >nul

dist\vcdNSXMigrator\vcdNSXMigrator.exe --help || goto :error
echo.
echo Build OK: dist\vcdNSXMigrator\vcdNSXMigrator.exe
exit /b 0

:error
echo Build FAILED (errorlevel %errorlevel%)
exit /b 1
