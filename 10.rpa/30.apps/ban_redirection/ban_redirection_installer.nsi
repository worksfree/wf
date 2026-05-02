; ban_redirection_installer.nsi
; Usage: makensis /DVERSION=X.X.X.X ban_redirection_installer.nsi

!ifndef VERSION
  !define VERSION "0.7.0.0"
!endif

!define APP_NAME   "Ban Redirection"
!define APP_FOLDER "ban_redirection"
!define APP_EXE    "ban_redirection.exe"
!define PUBLISHER  "WorksFree Co., Ltd."
!define REG_KEY    "Software\WorksFree\ban_redirection"
!define UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\ban_redirection"

!include "MUI2.nsh"
!include "nsDialogs.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"

Name "${APP_NAME} v${VERSION}"
OutFile "ban_redirection_${VERSION}_installer.exe"
InstallDir "$PROGRAMFILES64\WorksFree\${APP_FOLDER}"
InstallDirRegKey HKLM "${REG_KEY}" "InstallPath"
RequestExecutionLevel admin

VIProductVersion "${VERSION}"
VIAddVersionKey "ProductName"     "${APP_NAME}"
VIAddVersionKey "CompanyName"     "${PUBLISHER}"
VIAddVersionKey "ProductVersion"  "${VERSION}"
VIAddVersionKey "FileVersion"     "${VERSION}"
VIAddVersionKey "FileDescription" "DNS Redirection Blocker"
VIAddVersionKey "LegalCopyright"  "Copyright 2025 ${PUBLISHER}"

!if /FileExists "res\BR.ico"
  !define MUI_ICON   "res\BR.ico"
  !define MUI_UNICON "res\BR.ico"
!endif

!define MUI_ABORTWARNING

!insertmacro MUI_PAGE_WELCOME
Page custom LangSelectPage LangSelectLeave
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "Korean"
!insertmacro MUI_LANGUAGE "English"

Var LangDialog
Var RadioKo
Var RadioEn
Var SelectedLocale

Function .onInit
  StrCpy $SelectedLocale "ko"
FunctionEnd

Function LangSelectPage
  !insertmacro MUI_HEADER_TEXT \
    "Language Selection" \
    "Select the language to use after installation."

  nsDialogs::Create 1018
  Pop $LangDialog
  ${If} $LangDialog == error
    Abort
  ${EndIf}

  ${NSD_CreateLabel} 0 0 100% 16u "Language:"
  Pop $0

  ${NSD_CreateRadioButton} 10u 20u 100% 14u "Korean"
  Pop $RadioKo
  ${NSD_Check} $RadioKo

  ${NSD_CreateRadioButton} 10u 38u 100% 14u "English"
  Pop $RadioEn

  nsDialogs::Show
FunctionEnd

Function LangSelectLeave
  ${NSD_GetState} $RadioKo $0
  ${If} $0 == ${BST_CHECKED}
    StrCpy $SelectedLocale "ko"
  ${Else}
    StrCpy $SelectedLocale "en"
  ${EndIf}
FunctionEnd

Section "!${APP_NAME} (required)" SecMain
  SectionIn RO

  SetOutPath "$INSTDIR"
  File /r "dist\${APP_FOLDER}\*.*"

  CreateDirectory "$PROFILE\.wf_rpa"
  FileOpen $0 "$PROFILE\.wf_rpa\.locale" w
  FileWrite $0 $SelectedLocale
  FileClose $0

  WriteUninstaller "$INSTDIR\uninstall.exe"

  WriteRegStr HKLM "${REG_KEY}" "InstallPath" "$INSTDIR"
  WriteRegStr HKLM "${REG_KEY}" "Version"     "${VERSION}"

  WriteRegStr   HKLM "${UNINST_KEY}" "DisplayName"     "${APP_NAME} v${VERSION}"
  WriteRegStr   HKLM "${UNINST_KEY}" "UninstallString"  '"$INSTDIR\uninstall.exe"'
  WriteRegStr   HKLM "${UNINST_KEY}" "DisplayIcon"      "$INSTDIR\${APP_EXE}"
  WriteRegStr   HKLM "${UNINST_KEY}" "Publisher"        "${PUBLISHER}"
  WriteRegStr   HKLM "${UNINST_KEY}" "DisplayVersion"   "${VERSION}"
  WriteRegStr   HKLM "${UNINST_KEY}" "InstallLocation"  "$INSTDIR"
  WriteRegDWORD HKLM "${UNINST_KEY}" "NoModify" 1
  WriteRegDWORD HKLM "${UNINST_KEY}" "NoRepair"  1

  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  IntFmt $0 "0x%08X" $0
  WriteRegDWORD HKLM "${UNINST_KEY}" "EstimatedSize" "$0"
SectionEnd

Section "Desktop Shortcut" SecDesktop
  CreateShortCut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}"
SectionEnd

Section "Start Menu" SecStartMenu
  CreateDirectory "$SMPROGRAMS\WorksFree"
  CreateShortCut "$SMPROGRAMS\WorksFree\${APP_NAME}.lnk"         "$INSTDIR\${APP_EXE}"
  CreateShortCut "$SMPROGRAMS\WorksFree\${APP_NAME} Uninstall.lnk" "$INSTDIR\uninstall.exe"
SectionEnd

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecMain}      "Install Ban Redirection core files."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop}   "Create a desktop shortcut."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecStartMenu} "Add items to the Start Menu."
!insertmacro MUI_FUNCTION_DESCRIPTION_END

Section "Uninstall"
  nsExec::Exec 'taskkill /F /IM ${APP_EXE} /T'
  Sleep 500

  RMDir /r "$INSTDIR"

  DeleteRegKey HKLM "${REG_KEY}"
  DeleteRegKey HKLM "${UNINST_KEY}"

  Delete "$DESKTOP\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\WorksFree\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\WorksFree\${APP_NAME} Uninstall.lnk"
  RMDir  "$SMPROGRAMS\WorksFree"

  MessageBox MB_YESNO "Remove user settings? ($PROFILE\.wf_rpa\ban_redirection)" IDNO skip_user_data
    RMDir /r "$PROFILE\.wf_rpa\ban_redirection"
  skip_user_data:

  MessageBox MB_OK "${APP_NAME} has been removed."
SectionEnd
