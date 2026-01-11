!include "MUI2.nsh"
Name "BOM2Excel vv0.8.3.8"
OutFile "bom_exporter_v0.8.3.8_installer.exe"
InstallDir "$PROGRAMFILES64\WorksFree\bom_exporter"
RequestExecutionLevel admin
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_LANGUAGE "Korean"
Section
  SetOutPath "$INSTDIR"
  File /r "D:\release\candidates\bom_exporter_v0.8.3.8\bom_exporter_v0.8.3.8_portable\*.*"
  WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd
Section "Uninstall"
  RMDir /r "$INSTDIR"
SectionEnd
