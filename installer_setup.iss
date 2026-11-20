; Inno Setup Script for CheckHoaDon
#define MyAppName "He Thong Tra Cuu Hoa Don Dien Tu & NNT"
#define MyAppVersion "1.4.1"
#define MyAppPublisher "NDKBVH"
#define MyAppExeName "CheckHoaDon.exe"

#ifndef CacheDir
#define CacheDir "."
#endif

[Setup]
AppId={{E8B75043-4AC5-46D7-9AC3-17257A250819}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\CheckHoaDon
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=dist
OutputBaseFilename=CheckHoaDon_Setup_v1.4.1
SetupIconFile=app_icon.ico
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
Source: "VERSION.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "CheckHoaDon.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "app.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "extractor.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "excel_export.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "free_port.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "rpa_engine.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "rpa_nnt.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "screen_capture.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "watermark.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "run.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "app_icon.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "start_app.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "doi_cong.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "PORT.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "COPYRIGHT.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "static\*"; DestDir: "{app}\static"; Excludes: "screenshots,screenshots\*,uploads,uploads\*,webapp_*.png"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "templates\*"; DestDir: "{app}\templates"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#CacheDir}\python_env\*"; DestDir: "{app}\python_env"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#CacheDir}\pw-browsers\*"; DestDir: "{app}\pw-browsers"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
Name: "{app}\static\screenshots"; Permissions: users-full
Name: "{app}\static\uploads"; Permissions: users-full
Name: "{app}\data"; Permissions: users-full

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app_icon.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Tra Cuu Hoa Don & NNT"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app_icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
