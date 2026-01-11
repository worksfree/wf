!include "MUI2.nsh"
Name "DWG Batch Print vv0.7.0.7"
OutFile "dwg_batch_print_v0.7.0.7_installer.exe"
InstallDir "$PROGRAMFILES64\WorksFree\dwg_batch_print"
RequestExecutionLevel admin
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_LANGUAGE "Korean"
Section
  SetOutPath "$INSTDIR"
  File /r "D:\release\candidates\dwg_batch_print_v0.7.0.7\dwg_batch_print_v0.7.0.7_portable\*.*"
  WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd
Section "Uninstall"
  RMDir /r "$INSTDIR"
SectionEnd
