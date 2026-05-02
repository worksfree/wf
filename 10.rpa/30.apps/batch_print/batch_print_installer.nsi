!include "MUI2.nsh"
Name "Batch Print vv0.7.0.7"
OutFile "batch_print_v0.7.0.7_installer.exe"
InstallDir "$PROGRAMFILES64\WorksFree\batch_print"
RequestExecutionLevel admin
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_LANGUAGE "Korean"
Section
  SetOutPath "$INSTDIR"
  File /r "D:\release\candidates\batch_print_v0.7.0.7\batch_print_v0.7.0.7_portable\*.*"
  WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd
Section "Uninstall"
  RMDir /r "$INSTDIR"
SectionEnd
