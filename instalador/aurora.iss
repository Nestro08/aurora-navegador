; Instalador de Aurora para Windows (Inno Setup 6: https://jrsoftware.org/isinfo.php)
; Compílalo con construir.bat, o abriendo este archivo en Inno Setup y pulsando "Compile".
; Registra Aurora como navegador para que aparezca en Configuración > Aplicaciones predeterminadas.

#define Nombre "Aurora"
#define Version "4.0"
#define Exe "Aurora.exe"

[Setup]
AppId={{290C8904-778F-4234-9949-F3C773031949}
AppName={#Nombre}
AppVersion={#Version}
AppVerName={#Nombre} {#Version}
AppPublisher={#Nombre}
DefaultDirName={autopf}\{#Nombre}
DefaultGroupName={#Nombre}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=Aurora-Setup-{#Version}
SetupIconFile=..\recursos\aurora.ico
UninstallDisplayIcon={app}\{#Exe}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ChangesAssociations=yes
CloseApplications=yes

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "escritorio"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

[Files]
Source: "..\dist\Aurora\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#Nombre}"; Filename: "{app}\{#Exe}"
Name: "{group}\{#Nombre} (incógnito)"; Filename: "{app}\{#Exe}"; Parameters: "--incognito"
Name: "{group}\Desinstalar {#Nombre}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#Nombre}"; Filename: "{app}\{#Exe}"; Tasks: escritorio

[Registry]
; Tipo de documento que abre Aurora
Root: HKA; Subkey: "Software\Classes\AuroraHTML"; ValueType: string; ValueData: "Documento web de Aurora"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\AuroraHTML\DefaultIcon"; ValueType: string; ValueData: "{app}\{#Exe},0"
Root: HKA; Subkey: "Software\Classes\AuroraHTML\shell\open\command"; ValueType: string; ValueData: """{app}\{#Exe}"" ""%1"""
; Registro como navegador (StartMenuInternet + Capabilities)
Root: HKA; Subkey: "Software\Clients\StartMenuInternet\Aurora"; ValueType: string; ValueData: "{#Nombre}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Clients\StartMenuInternet\Aurora\DefaultIcon"; ValueType: string; ValueData: "{app}\{#Exe},0"
Root: HKA; Subkey: "Software\Clients\StartMenuInternet\Aurora\shell\open\command"; ValueType: string; ValueData: """{app}\{#Exe}"""
Root: HKA; Subkey: "Software\Clients\StartMenuInternet\Aurora\Capabilities"; ValueType: string; ValueName: "ApplicationName"; ValueData: "{#Nombre}"
Root: HKA; Subkey: "Software\Clients\StartMenuInternet\Aurora\Capabilities"; ValueType: string; ValueName: "ApplicationDescription"; ValueData: "Navegador web rápido, bonito y con herramientas para desarrolladores"
Root: HKA; Subkey: "Software\Clients\StartMenuInternet\Aurora\Capabilities"; ValueType: string; ValueName: "ApplicationIcon"; ValueData: "{app}\{#Exe},0"
Root: HKA; Subkey: "Software\Clients\StartMenuInternet\Aurora\Capabilities\StartMenu"; ValueType: string; ValueName: "StartMenuInternet"; ValueData: "Aurora"
Root: HKA; Subkey: "Software\Clients\StartMenuInternet\Aurora\Capabilities\URLAssociations"; ValueType: string; ValueName: "http"; ValueData: "AuroraHTML"
Root: HKA; Subkey: "Software\Clients\StartMenuInternet\Aurora\Capabilities\URLAssociations"; ValueType: string; ValueName: "https"; ValueData: "AuroraHTML"
Root: HKA; Subkey: "Software\Clients\StartMenuInternet\Aurora\Capabilities\FileAssociations"; ValueType: string; ValueName: ".html"; ValueData: "AuroraHTML"
Root: HKA; Subkey: "Software\Clients\StartMenuInternet\Aurora\Capabilities\FileAssociations"; ValueType: string; ValueName: ".htm"; ValueData: "AuroraHTML"
Root: HKA; Subkey: "Software\Clients\StartMenuInternet\Aurora\Capabilities\FileAssociations"; ValueType: string; ValueName: ".xhtml"; ValueData: "AuroraHTML"
Root: HKA; Subkey: "Software\Clients\StartMenuInternet\Aurora\Capabilities\FileAssociations"; ValueType: string; ValueName: ".pdf"; ValueData: "AuroraHTML"
Root: HKA; Subkey: "Software\Clients\StartMenuInternet\Aurora\Capabilities\FileAssociations"; ValueType: string; ValueName: ".svg"; ValueData: "AuroraHTML"
Root: HKA; Subkey: "Software\RegisteredApplications"; ValueType: string; ValueName: "Aurora"; ValueData: "Software\Clients\StartMenuInternet\Aurora\Capabilities"; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#Exe}"; Description: "Abrir {#Nombre}"; Flags: nowait postinstall skipifsilent
Filename: "ms-settings:defaultapps"; Description: "Elegir Aurora como navegador predeterminado"; Flags: shellexec postinstall skipifsilent unchecked

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Messages]
spanish.FinishedLabel=Aurora se ha instalado. Tus datos (historial, contraseñas, perfiles) están en la carpeta .aurora de tu usuario y no se borran al desinstalar.
