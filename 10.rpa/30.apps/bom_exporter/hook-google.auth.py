# PyInstaller hook for google.auth
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all('google.auth')
