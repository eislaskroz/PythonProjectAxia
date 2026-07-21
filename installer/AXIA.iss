#define MyAppName "AXIA"
#define MyAppVersion "0.96.1"
#define MyAppPublisher "AXIA Comunicaciones"
#define MyAppExeName "AXIA.exe"

[Setup]
AppId={{9B5A9E1C-BDC2-4E75-A842-5B1189702F37}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}

DefaultDirName={autopf}\AXIA
DefaultGroupName=AXIA
DisableProgramGroupPage=yes

OutputDir=..\release
OutputBaseFilename=AXIA_Setup_{#MyAppVersion}

Compression=lzma2
SolidCompression=yes
WizardStyle=modern

ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

PrivilegesRequired=admin

UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}

SetupIconFile=..\assets\SoloAxia.ico

CloseApplications=yes
RestartApplications=no

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; \
    Description: "Crear acceso directo en el escritorio"; \
    GroupDescription: "Accesos directos:"; \
    Flags: unchecked

[Files]
Source: "..\dist\AXIA\*"; \
    DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\AXIA"; \
    Filename: "{app}\{#MyAppExeName}"; \
    WorkingDir: "{app}"

Name: "{autodesktop}\AXIA"; \
    Filename: "{app}\{#MyAppExeName}"; \
    WorkingDir: "{app}"; \
    Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; \
    Description: "Ejecutar AXIA"; \
    Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"