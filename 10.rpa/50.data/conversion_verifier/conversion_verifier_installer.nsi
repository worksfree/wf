!include "MUI2.nsh"
Name "Conversion Verifier vv0.7.7.5"
OutFile "conversion_verifier_v0.7.7.5_installer.exe"
InstallDir "$PROGRAMFILES64\WorksFree\conversion_verifier"
RequestExecutionLevel admin
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_LANGUAGE "Korean"
Section
  SetOutPath "$INSTDIR"
  File /r "D:\release\candidates\conversion_verifier_v0.7.7.5\conversion_verifier_v0.7.7.5_portable\*.*"
  WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd
Section "Uninstall"
  RMDir /r "$INSTDIR"
SectionEnd
