!include "MUI2.nsh"

Unicode true

!ifndef APP_VERSION
  !error "APP_VERSION is required. Pass /DAPP_VERSION=1.2.3"
!endif
!ifndef INPUT_DIR
  !error "INPUT_DIR is required. Pass /DINPUT_DIR=C:\\path\\to\\nuitka.dist"
!endif
!ifndef OUTPUT_EXE
  !error "OUTPUT_EXE is required. Pass /DOUTPUT_EXE=dist\\release\\Cheremsha-Setup-v1.2.3.exe"
!endif

!define APP_NAME "Cheremsha"
!define APP_PUBLISHER "stream-cheremsha"
!define APP_EXE "cheremsha.exe"
!define APP_REGKEY "Software\\${APP_PUBLISHER}\\${APP_NAME}"
!define UNINST_KEY "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}"

Name "${APP_NAME}"
OutFile "${OUTPUT_EXE}"

RequestExecutionLevel user
InstallDir "$LOCALAPPDATA\\${APP_NAME}"

SetCompressor /SOLID lzma
ShowInstDetails show
ShowUninstDetails show

!define MUI_ABORTWARNING
!define MUI_ICON "..\\..\\dist\\nuitka\\icon.ico"
!define MUI_UNICON "..\\..\\dist\\nuitka\\icon.ico"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "English"


Section "Install"
  SetOutPath "$INSTDIR"

  ; Copy all Nuitka standalone build files.
  File /r "${INPUT_DIR}\\*.*"

  ; Shortcuts
  CreateDirectory "$SMPROGRAMS\\${APP_NAME}"
  CreateShortCut "$SMPROGRAMS\\${APP_NAME}\\${APP_NAME}.lnk" "$INSTDIR\\${APP_EXE}" "" "$INSTDIR\\${APP_EXE}" 0
  CreateShortCut "$DESKTOP\\${APP_NAME}.lnk" "$INSTDIR\\${APP_EXE}" "" "$INSTDIR\\${APP_EXE}" 0

  ; Registry (per-user)
  WriteRegStr HKCU "${APP_REGKEY}" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "${APP_REGKEY}" "Version" "${APP_VERSION}"

  ; Add/Remove Programs entry (per-user)
  WriteRegStr HKCU "${UNINST_KEY}" "DisplayName" "${APP_NAME}"
  WriteRegStr HKCU "${UNINST_KEY}" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKCU "${UNINST_KEY}" "Publisher" "${APP_PUBLISHER}"
  WriteRegStr HKCU "${UNINST_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${UNINST_KEY}" "UninstallString" '"$INSTDIR\\Uninstall.exe"'
  WriteRegStr HKCU "${UNINST_KEY}" "QuietUninstallString" '"$INSTDIR\\Uninstall.exe" /S'
  WriteRegDWORD HKCU "${UNINST_KEY}" "NoModify" 1
  WriteRegDWORD HKCU "${UNINST_KEY}" "NoRepair" 1

  WriteUninstaller "$INSTDIR\\Uninstall.exe"
SectionEnd


Section "Uninstall"
  ; Remove shortcuts
  Delete "$DESKTOP\\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\\${APP_NAME}\\${APP_NAME}.lnk"
  RMDir "$SMPROGRAMS\\${APP_NAME}"

  ; Remove installed files
  RMDir /r "$INSTDIR"

  ; Remove registry keys
  DeleteRegKey HKCU "${UNINST_KEY}"
  DeleteRegKey HKCU "${APP_REGKEY}"
SectionEnd

