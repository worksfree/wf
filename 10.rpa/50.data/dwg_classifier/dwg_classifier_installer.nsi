!include "MUI2.nsh"
Name "DWG Classifier vv0.7.8.8"
OutFile "dwg_classifier_v0.7.8.8_installer.exe"
InstallDir "$PROGRAMFILES64\WorksFree\dwg_classifier"
RequestExecutionLevel admin
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_LANGUAGE "Korean"
Section
  SetOutPath "$INSTDIR"
  File /r "D:\release\candidates\dwg_classifier_v0.7.8.8\dwg_classifier_v0.7.8.8_portable\*.*"
  WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd
Section "Uninstall"
  RMDir /r "$INSTDIR"
SectionEnd
