@echo off

set PYTHON_HOME=C:\Users\Nina\AppData\Local\Programs\Python
set PYTHON="%PYTHON_HOME%\Python311"

if exist "%~dp0.\_props.bat" call "%~dp0.\_props.bat"

%PYTHON% %*
