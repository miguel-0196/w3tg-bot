pyinstaller --onefile wallet_info.py
pyinstaller --onefile w-txt2db.py
move dist\*.exe .\
del /q dist/*
rd /s /q dist
del /q build/*
rd /s /q build
del /q *.spec