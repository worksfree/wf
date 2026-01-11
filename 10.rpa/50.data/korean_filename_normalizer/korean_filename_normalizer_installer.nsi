!include "MUI2.nsh"
Name "Korean Filename Normalizer vv0.7.7.9"
OutFile "korean_filename_normalizer_v0.7.7.9_installer.exe"
InstallDir "$PROGRAMFILES64\WorksFree\korean_filename_normalizer"
RequestExecutionLevel admin
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_LANGUAGE "Korean"
Section
  SetOutPath "$INSTDIR"
  File /r "D:\release\candidates\korean_filename_normalizer_v0.7.7.9\korean_filename_normalizer_v0.7.7.9_portable\*.*"
  WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd
Section "Uninstall"
  RMDir /r "$INSTDIR"
SectionEnd
