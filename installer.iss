[Setup]
AppName=VIDEOAI
AppVersion=1.0.0
DefaultDirName={pf}\VIDEOAI
OutputDir=installer_output
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
Source: "dist\VIDEOAI.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "main.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "config.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "pipeline.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "config.yaml"; DestDir: "{app}"; Flags: ignoreversion
Source: ".env.example"; DestDir: "{app}"; Flags: ignoreversion
Source: "launcher.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "INSTALL.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "templates\*"; DestDir: "{app}\templates"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "static\*"; DestDir: "{app}\static"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "prompts\*"; DestDir: "{app}\prompts"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "helpers\*"; DestDir: "{app}\helpers"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\VIDEOAI"; Filename: "{app}\VIDEOAI.exe"
Name: "{autodesktop}\VIDEOAI"; Filename: "{app}\VIDEOAI.exe"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\VIDEOAI"; Filename: "{app}\VIDEOAI.exe"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\VIDEOAI.exe"; Description: "{cm:LaunchProgram,VIDEOAI}"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;
  
  // Verificar si Python está instalado (opcional)
  if not Exec('python', '--version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    if MsgBox('Python no parece estar instalado. ¿Desea continuar de todos modos?', mbConfirmation, MB_YESNO) = ID_NO then
      Result := False;
  end;
end;
