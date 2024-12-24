pyinstaller --onefile wallet_info.py --hidden-import=solders
move dist\wallet_info.exe .\
del /q dist/*
rd /s /q dist
del /q build/*
rd /s /q build
del /q wallet_info.spec