; ============================================================
;  Inno Setup script — Bulk Gmail Mailer Windows Installer
;
;  Prerequisites:
;   1. Run build.bat first to produce dist\BulkMailer\
;   2. Install Inno Setup from https://jrsoftware.org/isinfo.php
;   3. Open this file in Inno Setup Compiler → Build → Compile
;
;  Output: dist\BulkMailer_Setup.exe
; ============================================================

#define MyAppName      "Bulk Gmail Mailer"
#define MyAppVersion   "1.0.0"
#define MyAppPublisher "Your Name"
#define MyAppURL       "https://github.com/rizwanali191025-commits/mailer"
#define MyAppExeName   "BulkMailer.exe"
#define SourceDir      "..\dist\BulkMailer"

[Setup]
AppId={{A3F2B8C1-4D7E-4F9A-B2C3-D4E5F6A7B8C9}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
; Install for current user only — no admin rights needed
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\dist
OutputBaseFilename=BulkMailer_Setup
SetupIconFile=..\assets\icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Everything PyInstaller produced
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu
Name: "{group}\{#MyAppName}";     Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall";        Filename: "{uninstallexe}"
; Desktop (optional)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Offer to launch after install
Filename: "{app}\{#MyAppExeName}"; \
  Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; \
  Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up generated user-data files that aren't tracked by the installer
Type: filesandordirs; Name: "{app}\config\token.json"
Type: filesandordirs; Name: "{app}\config\settings.json"
Type: filesandordirs; Name: "{app}\data"
Type: filesandordirs; Name: "{app}\templates"
