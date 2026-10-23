@echo off

tasklist /FI "IMAGENAME eq C:\Users\natha\AppData\Local\Programs\Anki\anki.exe" 2>NUL | find /I /N "anki.exe">NUL

if "%ERRORLEVEL%"=="0" (
    echo Anki is already running. 
) else (
    echo Anki is not running. Starting now...
    start "" "C:\Users\natha\AppData\Local\Programs\Anki\anki.exe"
)

python "C:\Users\natha\OneDrive\Documents\Unikram\4_sem\Niederlaendisch\textgenanki.py"

pause