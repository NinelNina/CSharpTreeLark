@echo off

set PYTHON_HOME=C:\Users\Owner\AppData\Local\Programs\Python
set PYTHON="%PYTHON_HOME%\Python39"

if exist "%~dp0.\_props.bat" call "%~dp0.\_props.bat"

%PYTHON% %*
