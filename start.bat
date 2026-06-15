@echo off
title MailSwift Server
cd /d "%~dp0"

echo ========================================
echo  MailSwift - 邮件发送工具
echo ========================================
echo.

echo [1/2] 启动 MySQL...
start "MySQL" /MIN "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqld.exe" --datadir="%USERPROFILE%\mysql_data" --port=3306

REM 等待 MySQL 就绪
:wait_mysql
timeout /t 1 /nobreak >nul
python -c "import pymysql; pymysql.connect(host='localhost', port=3306, user='root', password=''); exit(0)" 2>nul
if %errorlevel% neq 0 goto wait_mysql
echo        MySQL 已就绪

echo [2/2] 启动 MailSwift 服务...
echo.
python app.py

pause
