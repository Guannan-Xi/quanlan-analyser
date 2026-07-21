#define MyAppName "QLanalyser"
#define MyAppVersion "2.0.5.1.beta"
#define MyAppPublisher "Quanlan, Inc."
#define MyAppURL "eegion.com"
#define MyAppExeName "AR_analyser.exe"
#define MyAppAssocName MyAppName + " File"
#define MyAppAssocExt ".myp"
#define MyAppAssocKey StringChange(MyAppAssocName, " ", "") + MyAppAssocExt

[Setup]
AppId={{0B28AB31-5827-449E-AADC-B8AC100300BC}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
ChangesAssociations=yes
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputBaseFilename=QLanalyser_installer_{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "E:\analyserProject\analyserProjectDir\AR_analyser_PC\dist\AR_analyser\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "E:\analyserProject\analyserProjectDir\AR_analyser_PC\dist\AR_analyser\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "E:\analyserProject\analyserProjectDir\AR_analyser_PC\dist\AR_analyser\QL1.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "E:\analyserProject\analyserProjectDir\AR_analyser_PC\update.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "E:\analyserProject\analyserProjectDir\AR_analyser_PC\dist\AR_analyser\QL1.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "E:\analyserProject\analyserProjectDir\AR_analyser_PC\dist\AR_analyser\config\*"; DestDir: "{app}\config"; Flags: ignoreversion
Source: "E:\analyserProject\analyserProjectDir\AR_analyser_PC\dist\AR_analyser\resource\*"; DestDir: "{app}\resource"; Flags: ignoreversion recursesubdirs createallsubdirs

[Registry]
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocExt}\OpenWithProgids"; ValueType: string; ValueName: "{#MyAppAssocKey}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocKey}"; ValueType: string; ValueName: ""; ValueData: "{#MyAppAssocName}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocKey}\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\QL1.ico"
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocKey}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKA; Subkey: "Software\Classes\Applications\{#MyAppExeName}\SupportedTypes"; ValueType: string; ValueName: ".myp"; ValueData: ""

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\QL1.ico"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\QL1.ico"; WorkingDir: "{app}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
