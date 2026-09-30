@echo off
rem Reverse SOCKS tunnel: lets the Hetzner server fetch phone numbers via this PC IP.
rem Keep this window open. Server side uses DIVAR_PROXY=socks5h://127.0.0.1:1080
:loop
ssh -N -R 127.0.0.1:1080 -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes 91.107.170.115
echo tunnel dropped, reconnecting in 10s...
timeout /t 10 /nobreak >nul
goto loop
