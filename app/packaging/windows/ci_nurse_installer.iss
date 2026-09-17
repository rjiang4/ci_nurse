#ifndef MyAppVersion
#define MyAppVersion "0.0.0"
#endif

#define MyAppName "CI Nurse"
#define MyAppPublisher "CI Nurse"
#define MyAppExeName "CI-Nurse.exe"

[Setup]
AppId={{CDAA07CB-A3D4-4DC5-9A17-61BBD43C5A31}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\CI Nurse
DefaultGroupName=CI Nurse
DisableProgramGroupPage=yes
OutputDir=..\..\installer
OutputBaseFilename=CI-Nurse-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
UninstallDisplayName=CI Nurse
UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "..\..\dist\CI-Nurse.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\CI Nurse"; Filename: "{app}\{#MyAppExeName}"
Name: "{userdesktop}\CI Nurse"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch CI Nurse"; Flags: nowait postinstall skipifsilent
