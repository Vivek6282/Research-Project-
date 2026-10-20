@echo off
setlocal
cd /d "%~dp0"

echo Building protocol security tests with g++...
g++ -std=c++11 -Wall -Wextra -Werror -I..\shared test_protocol.cpp -o test_protocol.exe
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Test compilation failed!
    exit /b %ERRORLEVEL%
)

echo Executing host protocol tests...
test_protocol.exe
