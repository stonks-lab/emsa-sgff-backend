# Runbook: despliegue del SGFF en Windows Server

Procedimiento para instalar, actualizar y operar el SGFF en el Windows Server de producción de EMSA.
Todos los pasos se pueden repetir: saltan lo que ya está hecho y corrigen lo que está mal. Para
instalar desde cero, ejecútalo completo; para retomar una instalación a medias, también.

> **Este repo es público.** Aquí no van el nombre del servidor, IPs, usuarios ni claves. Donde haga
> falta, el runbook dice `<servidor>`: el nombre está en el gestor de claves del equipo.

| Qué | Valor |
|---|---|
| URL | `http://<servidor>/sgff`. Es una aplicación dentro del *Default Web Site* de IIS, igual que las otras apps del servidor |
| Carpeta | `E:\EMSA\apps\sgff\` con `backend\` (este repo) y `frontend\` (repo `emsa-sgff-frontend`) |
| Backend | uvicorn en `127.0.0.1:8007`, lanzado por la tarea programada `EMSA-SGFF-Backend` como **LOCAL SERVICE** |
| Frontend | Build de Vite en `frontend\dist`, compilado para la sub-ruta `/sgff/`. Lo sirve el mismo backend gracias a una *junction* `backend\frontend` → `..\frontend` |
| IIS | La aplicación `/sgff` reenvía todo a `127.0.0.1:8007` y le quita el `/sgff` |
| Python | El global de la máquina **solo crea el `.venv`**. Las librerías van en el `.venv`, nunca en el global |
| Logs | `E:\EMSA\shared\logs\sgff\` (`sgff.log`, `sgff-access.log` y `sgff-consola.log`) |
| Secretos | `backend\.env` y `E:\EMSA\secretos\sgff\` (`logging.json` y respaldos del `.env`) |

## Decisiones de diseño

- **Sub-ruta `/sgff` en el Default Web Site.** Es la convención del servidor: cada app en
  `/<nombre-de-la-app>`. El frontend se compila con `base: '/sgff/'` (ver `src/config/base.ts` del
  frontend) y IIS quita el prefijo antes de reenviar, así que **el backend no sabe que vive bajo
  `/sgff`**.
- **Tarea como LOCAL SERVICE**, no una cuenta con clave. Es una cuenta del sistema con privilegios
  mínimos. No tiene clave que guardar ni que caduque, y no necesita el derecho "Log on as a batch
  job", que la GPO del servidor puede bloquear. Para el SQL no importa qué cuenta corre el proceso,
  porque se conecta con usuario y clave de SQL. Solo habría que cambiar a una cuenta de dominio si
  algún día se usa `SQL_AUTH=windows`.
- **La tarea lanza Python dentro de `cmd /c ... >> sgff-consola.log 2>&1`.** Si Python se cae antes
  de configurar sus logs (falta un permiso, un error en el `.env`), el error queda en ese archivo en
  vez de perderse.
- **El build usa `npx vite build`, no `npm run build`.** Este último corre antes `tsc`, que hoy falla
  por errores de tipos previos del frontend (su backlog, ítem 1). El resultado es el mismo. Revisar
  tipos es tarea de desarrollo; un despliegue no debe caerse por eso.
- **El Paso 6.1 prueba las credenciales SQL antes de escribir el `.env`**, conectándose exactamente
  como la app. Así un error de clave aparece en la instalación, y no como pantallas vacías.

---

## Cómo usar este runbook

- Usa **Windows PowerShell 5.1 elevado** (“Ejecutar como administrador”) y **la misma consola de
  principio a fin**. Si la cierras, vuelve a pegar el **Paso 1 completo (1.1 y 1.2)** antes de seguir.
- Pega **un bloque a la vez** y lee la salida antes del siguiente. Busca las líneas `FALLA`: si
  aparece una, no sigas hasta resolverla (ver “Si algo falla” al final).
- Los bloques críticos van dentro de `. { $ErrorActionPreference = 'Stop'; ... }`: si una línea
  falla, se detiene el bloque entero. Los comandos nativos (`git`, `pip`, `npm`, `python`) van
  **fuera** de esos bloques.
- Las contraseñas y el token **se pegan en la ventana de `Get-Credential`**, no en la consola: por
  escritorio remoto, el pegado en la consola deja un solo carácter.

---

## Paso 0. Antes de empezar: tener a mano

- [ ] **SQL principal (DAB):** host (o `host,puerto`), nombre de la base, usuario y clave
      confirmados. Si puedes, prueba la clave por SSMS desde otro equipo.
- [ ] **SQL BI** (`BI_dev`): usuario y clave de lectura de avance/PAI.
- [ ] **Monday.com:** token y `MONDAY_BOARD_ID`.
- [ ] **Credenciales de GitHub**, si los repos dejan de ser públicos.
- [ ] **Usuario y clave del primer `admin` del SGFF.** Los demás usuarios se crean después desde la
      pantalla Usuarios.
- [ ] **Una ventana de tiempo.** No se toca nada de las otras apps. Excepción: si el proxy de ARR
      está apagado, el Paso 11 lo enciende para todo el servidor (ver la nota ahí).

---

## Paso 1. Variables y funciones (pegar siempre primero, los dos bloques)

### 1.1 Variables

```powershell
$Raiz          = 'E:\EMSA\apps\sgff'
$Backend       = "$Raiz\backend"
$Frontend      = "$Raiz\frontend"
$Secretos      = 'E:\EMSA\secretos\sgff'
$Logs          = 'E:\EMSA\shared\logs\sgff'
$Backups       = 'E:\EMSA\backups\sgff'
$IisDir        = 'C:\inetpub\sgff'          # solo contiene el web.config de la aplicacion /sgff
$SitioIis      = 'Default Web Site'
$SubRuta       = 'sgff'                     # debe coincidir con base en vite.config.ts del frontend
$UrlLocal      = "http://localhost/$SubRuta"
$Puerto        = 8007                       # uvicorn, solo 127.0.0.1
$Tarea         = 'EMSA-SGFF-Backend'
$SvcSid        = '*S-1-5-19'                # LOCAL SERVICE (para icacls)
$SvcCuenta     = (New-Object Security.Principal.SecurityIdentifier 'S-1-5-19').Translate([Security.Principal.NTAccount]).Value
$PyGlobal      = 'C:\Program Files\Python312\python.exe'
$RepoBackend   = 'https://github.com/stonks-lab/emsa-sgff-backend.git'
$RepoFrontend  = 'https://github.com/stonks-lab/emsa-sgff-frontend.git'
$Venv          = "$Backend\.venv\Scripts"
Import-Module WebAdministration
"Variables cargadas: SGFF en $Raiz, backend en 127.0.0.1:$Puerto, publicado en $UrlLocal, cuenta $SvcCuenta"
```

### 1.2 Funciones de apoyo

Definen las pruebas que usan los pasos siguientes. No cambian nada en el servidor.

```powershell
$SgffSqlTestPy = @'
import os, sys
sys.stdout.reconfigure(errors='replace')
import pyodbc
srv, db, usr, pwd, nom = (os.environ[k] for k in ('T_SERVER', 'T_DB', 'T_USER', 'T_PWD', 'T_NOMBRE'))
drivers = sorted(d for d in pyodbc.drivers() if 'SQL Server' in d)
if not drivers:
    print('FALLA ' + nom + ': no hay driver ODBC para SQL Server')
    sys.exit(2)
drv = drivers[-1]
raros = sorted(set(pwd) & set(';{}'))
print(nom + ': usuario=' + usr + ' | base=' + db + ' | driver que usa la app=' + drv + ' | largo clave=' + str(len(pwd)))

def probar(cs):
    try:
        cn = pyodbc.connect(cs, timeout=15)
        fila = cn.execute('select db_name(), suser_sname()').fetchone()
        cn.close()
        return True, 'base=' + str(fila[0]) + ' login=' + str(fila[1])
    except pyodbc.Error as e:
        return False, str(e.args[-1])[:400]

base = 'DRIVER={' + drv + '};SERVER=' + srv + ';'
ok, msg = probar(base + 'DATABASE=' + db + ';UID=' + usr + ';PWD=' + pwd + ';')
print('  OK    como la app: ' + msg if ok else '  FALLA como la app: ' + msg)
if ok:
    sys.exit(0)
ok2, msg2 = probar(base + 'UID=' + usr + ';PWD={' + pwd.replace('}', '}}') + '};')
print('  OK    solo login: ' + msg2 if ok2 else '  FALLA solo login: ' + msg2)
if ok2 and raros:
    print('  => La clave es correcta, pero trae ' + ' '.join(raros) + ' y la app arma mal la conexion con esos caracteres. Pide cambiar la clave por una sin ; { }')
elif ok2:
    print('  => Usuario y clave correctos, pero sin acceso a la base ' + db + '. Revisa el nombre de la base o pide al DBA que de acceso a ' + usr + ' en ' + db)
else:
    print('  => SQL Server rechaza el usuario o la clave. Si estas seguro de la clave, pide al DBA el "state" del error 18456 en el log de SQL Server: 8 = clave incorrecta, 5 = el login no existe, 7 = login deshabilitado')
sys.exit(1)
'@

function Test-SqlLogin([string]$Servidor, [string]$Base, [pscredential]$Cred, [string]$Nombre) {
  $ErrorActionPreference = 'Continue'
  $f = Join-Path $env:TEMP 'sgff_sqltest.py'
  [IO.File]::WriteAllText($f, $SgffSqlTestPy, (New-Object Text.UTF8Encoding($false)))
  $env:T_SERVER = $Servidor; $env:T_DB = $Base; $env:T_NOMBRE = $Nombre
  $env:T_USER = $Cred.UserName.TrimStart('\'); $env:T_PWD = $Cred.GetNetworkCredential().Password
  try { & "$Venv\python.exe" -I $f | Out-Host; $ok = ($LASTEXITCODE -eq 0) }
  finally {
    Remove-Item Env:T_PWD, Env:T_USER, Env:T_SERVER, Env:T_DB, Env:T_NOMBRE -ErrorAction SilentlyContinue
    Remove-Item $f -ErrorAction SilentlyContinue
  }
  return $ok
}

function Stop-Sgff {
  Stop-ScheduledTask -TaskName $Tarea -ErrorAction SilentlyContinue
  $ids  = @(Get-NetTCPConnection -LocalPort $Puerto -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess)
  $ids += @(Get-CimInstance Win32_Process -Filter "CommandLine LIKE '%--port $Puerto%'" | Select-Object -ExpandProperty ProcessId)
  $ids | Where-Object { $_ -and $_ -ne $PID } | Sort-Object -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
  Start-Sleep 2
  if (Get-NetTCPConnection -LocalPort $Puerto -State Listen -ErrorAction SilentlyContinue) { "FALLA el puerto $Puerto sigue ocupado" } else { "OK    SGFF detenido (puerto $Puerto libre)" }
}

function Wait-Sgff([string]$Base = "http://127.0.0.1:$Puerto", [int]$Segundos = 60) {
  for ($i = 0; $i -lt $Segundos; $i += 3) {
    try { if ((Invoke-RestMethod "$Base/api/health" -TimeoutSec 3).status -eq 'ok') { return $true } } catch { }
    Start-Sleep 3
  }
  return $false
}

function Test-Sgff([string]$Base = "http://127.0.0.1:$Puerto") {
  try { $h = Invoke-RestMethod "$Base/api/health" -TimeoutSec 10; "OK    health: $($h.status)" } catch { "FALLA health: $($_.Exception.Message)" }
  try {
    $w = Invoke-WebRequest "$Base/" -UseBasicParsing -TimeoutSec 10
    if ($w.Content -notmatch 'id="root"') { "FALLA interfaz: HTTP $($w.StatusCode), pero no es el index de React" }
    elseif ($w.Content -notmatch "/$SubRuta/assets/") { "FALLA interfaz: el build no es para /$SubRuta (frontend desactualizado: Paso 4 y Paso 7)" }
    else { "OK    interfaz: HTTP $($w.StatusCode), build para /$SubRuta" }
  } catch { "FALLA interfaz: $($_.Exception.Message) (si dice Not Found, el backend no ve dist: Paso 7)" }
  if (-not $script:AdminCred) { $script:AdminCred = Get-Credential -Message 'Usuario y clave del admin del SGFF (solo para probar el login)' }
  $body = [Text.Encoding]::UTF8.GetBytes((@{ username = $script:AdminCred.UserName.TrimStart('\'); password = $script:AdminCred.GetNetworkCredential().Password } | ConvertTo-Json))
  try { $l = Invoke-RestMethod -Method Post "$Base/api/auth/login" -ContentType 'application/json; charset=utf-8' -Body $body -TimeoutSec 10; "OK    login: $($l.user.username) ($($l.user.role))" }
  catch { "FALLA login: $($_.Exception.Message) (401 = usuario/clave o hash; 503 = falta users.json o permisos)" }
}

function Get-SgffDiag {
  $i = Get-ScheduledTaskInfo -TaskName $Tarea -ErrorAction SilentlyContinue
  if ($i) {
    $hex = '0x{0:X}' -f $i.LastTaskResult
    $txt = @{ '0x0' = 'el proceso termino (no deberia: uvicorn no se cierra solo)'; '0x1' = 'Python termino con error: mira sgff-consola.log'
              '0x41301' = 'en ejecucion'; '0x41303' = 'nunca se ha ejecutado'; '0x41306' = 'detenida a mano'
              '0x8007052E' = 'usuario o clave incorrectos'; '0x80070569' = 'la cuenta no tiene derecho de inicio de sesion por lotes (GPO)'
              '0xC000013A' = 'proceso cortado (Stop-Sgff o Ctrl+C)' }[$hex]
    "Tarea: ultimo inicio $($i.LastRunTime) | resultado $hex $txt"
    "Tarea: corre como $((Get-ScheduledTask -TaskName $Tarea).Principal.UserId)"
  } else { 'Tarea: no existe' }
  $esc = Get-NetTCPConnection -LocalPort $Puerto -State Listen -ErrorAction SilentlyContinue
  if ($esc) { "Puerto ${Puerto}: escuchando (PID $($esc[0].OwningProcess))" } else { "Puerto ${Puerto}: nadie escuchando" }
  Get-CimInstance Win32_Process -Filter "CommandLine LIKE '%--port $Puerto%'" | ForEach-Object { "Proceso: PID $($_.ProcessId) $($_.Name) como $((Invoke-CimMethod -InputObject $_ -MethodName GetOwner).User)" }
  foreach ($f in "$Logs\sgff-consola.log", "$Logs\sgff.log") {
    "----- $f (ultimas 20 lineas)"
    if (Test-Path $f) { Get-Content $f -Tail 20 -ErrorAction SilentlyContinue } else { '(no existe)' }
  }
}
'OK funciones cargadas: Test-SqlLogin, Stop-Sgff, Wait-Sgff, Test-Sgff, Get-SgffDiag'
```

---

## Paso 2. Revisión previa (solo lectura)

```powershell
. {
  function Linea($ok, $texto) { if ($ok) { "OK    $texto" } else { "FALLA $texto" } }
  if (Test-Path $PyGlobal) {
    $v = [version](& $PyGlobal -c "import platform; print(platform.python_version())")
    Linea ($v -ge [version]'3.10') "Python global $v"
  } else { Linea $false "No existe $PyGlobal (mira 'py -0p' y corrige `$PyGlobal en el Paso 1.1)" }
  if (Get-Command git -ErrorAction SilentlyContinue) { Linea $true (git --version) } else { Linea $false 'Git no instalado' }
  if (Get-Command node -ErrorAction SilentlyContinue) {
    $nv = [version]((node -v).TrimStart('v'))
    Linea ((($nv.Major -eq 20) -and ($nv.Minor -ge 19)) -or ($nv -ge [version]'22.12')) "Node $nv (Vite 8 pide 20.19+ o 22.12+)"
  } else { Linea $false 'Node no instalado: usa la alternativa del Paso 7' }
  $excl = netsh int ipv4 show excludedportrange protocol=tcp | ForEach-Object { if ($_ -match '^\s*(\d+)\s+(\d+)') { [pscustomobject]@{ Ini = [int]$matches[1]; Fin = [int]$matches[2] } } }
  Linea (-not ($excl | Where-Object { $Puerto -ge $_.Ini -and $Puerto -le $_.Fin })) "Puerto $Puerto fuera de los rangos reservados por Windows"
  $esc = Get-NetTCPConnection -LocalPort $Puerto -State Listen -ErrorAction SilentlyContinue
  if ($esc) { $cl = (Get-CimInstance Win32_Process -Filter "ProcessId=$($esc[0].OwningProcess)").CommandLine; Linea ($cl -match 'uvicorn') "Puerto $Puerto ocupado por: $cl (si es uvicorn del SGFF, esta bien)" }
  else { Linea $true "Puerto $Puerto libre" }
  Linea (Test-Path "IIS:\Sites\$SitioIis") "Sitio de IIS '$SitioIis' existe"
  $app = Get-WebApplication -Site $SitioIis -Name $SubRuta
  $vdir = Get-WebVirtualDirectory -Site $SitioIis -Name $SubRuta
  Linea ((-not $vdir) -and ((-not $app) -or ($app.applicationPool -eq 'SGFF'))) "/$SubRuta libre en '$SitioIis' (o ya es la aplicacion del SGFF)"
  $mods = @(Get-WebGlobalModule | Select-Object -ExpandProperty Name)
  Linea ($mods -contains 'RewriteModule') 'IIS URL Rewrite instalado'
  Linea ($mods -contains 'ApplicationRequestRouting') 'IIS ARR instalado'
  $px = Get-WebConfigurationProperty -PSPath 'MACHINE/WEBROOT/APPHOST' -Filter 'system.webServer/proxy' -Name enabled
  Linea ($(if ($px -is [bool]) { $px } else { [bool]$px.Value })) 'Proxy de ARR activado (si sale FALLA, lo activa el Paso 11)'
  $drv = @(Get-OdbcDriver -Platform '64-bit' | Where-Object Name -match 'SQL Server' | Select-Object -ExpandProperty Name)
  Linea ($drv.Count -gt 0) "Drivers ODBC: $($drv -join ', ')"
}
```

Las únicas `FALLA` aceptables aquí son la del proxy de ARR (la corrige el Paso 11) y la de Node, si
vas a usar la alternativa del Paso 7.

- [ ] Python · [ ] Git · [ ] Node · [ ] Puerto 8007 · [ ] `/sgff` libre · [ ] Rewrite + ARR · [ ] Drivers ODBC

---

## Paso 3. Carpetas

```powershell
. {
  $ErrorActionPreference = 'Stop'
  foreach ($d in $Raiz, $Secretos, $Logs, $Backups, $IisDir) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d | Out-Null; "creada  $d" } else { "existe  $d" }
  }
}
```

---

## Paso 4. Código

Clona solo si falta y, si ya existe, lo trae al día.

```powershell
if (-not (Test-Path "$Backend\.git"))  { git clone $RepoBackend  $Backend }
if (-not (Test-Path "$Frontend\.git")) { git clone $RepoFrontend $Frontend }
git -C $Backend  pull --ff-only
git -C $Frontend pull --ff-only
git -C $Backend  status -sb
git -C $Frontend status -sb
git -C $Backend  log -1 --format='backend  %h %ad %s' --date=short
git -C $Frontend log -1 --format='frontend %h %ad %s' --date=short
```

- `status -sb` debe mostrar solo `## main...origin/main`, sin más líneas.
- Anota los dos hashes: sirven para volver atrás.
- Si el pull del backend se detiene por `users.json`, sigue el procedimiento del Paso 14.

---

## Paso 5. Backend: `.venv` y dependencias

```powershell
cd $Backend
if (-not (Test-Path "$Venv\python.exe")) { & $PyGlobal -m venv "$Backend\.venv" }
& "$Venv\python.exe" -m pip install --upgrade pip
& "$Venv\python.exe" -m pip install -r requirements.txt
& "$Venv\python.exe" -m pip check
& "$Venv\python.exe" -m compileall -q app
```

`compileall` deja los `.pyc` listos, porque LOCAL SERVICE no puede escribirlos y sin ellos el
arranque es más lento. `pip check` debe decir `No broken requirements found.`

Si `pip` no llega a PyPI: descarga los *wheels* `win_amd64` en otro equipo, cópialos e instala con
`pip install --no-index --find-links <carpeta> -r requirements.txt`.

---

## Paso 6. Configuración

### 6.1 `.env`: probar las credenciales y escribirlo

El bloque:

1. Lee el `.env` anterior, si existe, y lo ofrece como valor por defecto (Enter lo acepta).
2. **Pide siempre** el usuario y la clave del SQL principal y **los prueba contra el SQL**. Si
   fallan, explica por qué y te deja reintentar.
3. Para el BI, prueba primero lo que ya había en el `.env`. Solo te lo pide si falla o no existe.
4. Reutiliza el token y el board de Monday si ya estaban. Si no, los pide.
5. Genera un `JWT_SECRET` nuevo, respalda el `.env` anterior en `$Secretos` y escribe el nuevo
   (UTF-8 sin BOM: con BOM la app no arranca). Mantiene cualquier otra variable del `.env`
   anterior, como `HTTPS_PROXY`.

Si una conexión falla y aún no puedes resolverla (por ejemplo, porque esperas al DBA), puedes
responder `c` para **continuar igual**. El SGFF levanta, pero las pantallas de esa base salen
vacías. Después repites solo este paso.

```powershell
. {
  $ErrorActionPreference = 'Stop'
  $script:SqlPendiente = $false
  $viejo = [ordered]@{}
  if (Test-Path "$Backend\.env") {
    foreach ($l in Get-Content "$Backend\.env") { if ($l -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$') { $viejo[$matches[1]] = $matches[2].Trim().Trim("'").Trim('"') } }
    "Se encontro un .env anterior con $($viejo.Count) variables."
  }
  function Def($a, $b) { if ($a) { $a } else { $b } }
  function Pedir([string]$texto, [string]$actual) {
    $v = if ($actual) { Read-Host "$texto [Enter = $actual]" } else { Read-Host $texto }
    if ($v) { $v.Trim() } else { $actual }
  }
  function Login([string]$titulo, [string]$db, [string]$usuario, [pscredential]$inicial) {
    $c = $inicial
    while ($true) {
      if (-not $c) {
        $c = Get-Credential -UserName $usuario -Message "$titulo (base $db): usuario y clave"
        if (-not $c) { throw "Cancelado en $titulo" }
      }
      if (Test-SqlLogin $sqlServer $db $c $titulo) { return $c }
      $r = Read-Host "$titulo fallo. s = reintentar con otra clave | c = continuar igual | n = cancelar"
      if ($r -eq 'c') { $script:SqlPendiente = $true; return $c }
      if ($r -ne 's') { throw "$titulo fallo: no se escribio el .env" }
      $c = $null
    }
  }
  $sqlServer = Pedir 'SQL_SERVER (host o host,puerto)' $viejo['SQL_SERVER']
  $sqlDb     = Pedir 'SQL_DATABASE (base principal)' $viejo['SQL_DATABASE']
  $sql = Login 'SQL principal' $sqlDb (Def $viejo['SQL_USER'] 'usuario') $null
  $biDb  = Def $viejo['SQL_BI_DATABASE'] 'BI_dev'
  $biIni = if ($viejo['SQL_BI_USER'] -and $viejo['SQL_BI_PASSWORD']) { New-Object PSCredential($viejo['SQL_BI_USER'], (ConvertTo-SecureString $viejo['SQL_BI_PASSWORD'] -AsPlainText -Force)) } else { $null }
  $bi = Login 'SQL BI' $biDb (Def $viejo['SQL_BI_USER'] 'usuario') $biIni
  $board = Pedir 'MONDAY_BOARD_ID' $viejo['MONDAY_BOARD_ID']
  $mondayKey = $viejo['MONDAY_API_KEY']
  if (-not $mondayKey) {
    $m = Get-Credential -UserName 'monday' -Message 'Pega el TOKEN de Monday en la clave'
    if ($m) { $mondayKey = $m.GetNetworkCredential().Password }
  }
  $rnd = New-Object byte[] 32; [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($rnd)
  $jwt = -join ($rnd | ForEach-Object { $_.ToString('x2') })
  function Q([string]$v) { if ($v.Contains("'") -or $v.Contains("`n")) { throw 'Un valor trae comilla simple o salto de linea: escribelo a mano' }; "'$v'" }
  $nuevas = [ordered]@{
    SQL_SERVER = $sqlServer; SQL_DATABASE = $sqlDb; SQL_AUTH = 'sql'
    SQL_USER = (Q $sql.UserName.TrimStart('\')); SQL_PASSWORD = (Q $sql.GetNetworkCredential().Password)
    SQL_BI_USER = (Q $bi.UserName.TrimStart('\')); SQL_BI_PASSWORD = (Q $bi.GetNetworkCredential().Password); SQL_BI_DATABASE = $biDb
    JWT_SECRET = $jwt; MONDAY_API_KEY = (Q ([string]$mondayKey)); MONDAY_BOARD_ID = $board
  }
  $lineas = @('# SGFF produccion. No versionar. Generado ' + (Get-Date -Format 'yyyy-MM-dd HH:mm'))
  foreach ($k in $nuevas.Keys) { $lineas += "$k=$($nuevas[$k])" }
  foreach ($k in $viejo.Keys) { if (-not $nuevas.Contains($k)) { $lineas += "$k=" + (Q $viejo[$k]); "se mantiene $k del .env anterior" } }
  if (Test-Path "$Backend\.env") { Copy-Item "$Backend\.env" "$Secretos\env-anterior-$(Get-Date -Format yyyyMMdd-HHmm).txt" }
  [IO.File]::WriteAllText("$Backend\.env", (($lineas -join "`r`n") + "`r`n"), (New-Object Text.UTF8Encoding($false)))
  "OK    .env escrito ($((Get-Item "$Backend\.env").Length) bytes). El anterior, si habia, quedo respaldado en $Secretos"
  if ($script:SqlPendiente) { 'FALLA quedo al menos una conexion SQL sin funcionar (elegiste continuar). Repite este paso cuando tengas la clave correcta.' }
}
```

Confirmación final **a través del código de la app**:

```powershell
cd $Backend
& "$Venv\python.exe" -c "from app.data.sql_server import get_connection; print('OK    principal (app):', get_connection().execute('select db_name()').fetchone()[0])"
& "$Venv\python.exe" -c "from app.data.sql_server import get_connection_bi; print('OK    BI (app):', get_connection_bi().execute('select db_name()').fetchone()[0])"
```

**Cómo leer el diagnóstico del SQL:**

| Lo que dice | Qué significa | Qué hacer |
|---|---|---|
| `FALLA como la app` y `FALLA solo login` | SQL Server rechaza ese usuario con esa clave | Confirma la clave. Si es la correcta, pide al DBA el *state* del 18456 |
| `FALLA como la app` y `OK solo login`, con `; { }` en la clave | La clave es correcta, pero la app no soporta esos caracteres (backlog, ítem 7) | Pide una clave sin `;`, `{` ni `}` |
| `FALLA como la app` y `OK solo login`, sin caracteres raros | El login es válido, pero no tiene acceso a esa base o el nombre está mal | Revisa `SQL_DATABASE` o pide al DBA el acceso |

- [ ] SQL principal OK · [ ] SQL BI OK · [ ] `.env` escrito

### 6.2 `users.json`: un admin real

El `users.json` del repo trae usuarios de prueba con la clave pública `sgff-local`. Este bloque
**verifica** que ya no estén:

```powershell
. {
  $ErrorActionPreference = 'Stop'
  $f = "$Backend\users.json"
  if (-not (Test-Path $f)) { 'FALLA no existe users.json: ejecuta 6.2b'; return }
  $b = [IO.File]::ReadAllBytes($f)
  if ($b.Length -ge 3 -and $b[0] -eq 0xEF -and $b[1] -eq 0xBB -and $b[2] -eq 0xBF) { 'FALLA users.json tiene BOM: ejecuta 6.2b'; return }
  $hashPrueba = '5e7cd08cb6633d99667bc515ba05b2e182b1d8ba39fa8a08899b46c68f68a7fe'   # sha256('sgff-local')
  $us = (Get-Content $f -Raw | ConvertFrom-Json) | ForEach-Object { $_ }
  foreach ($u in $us) { if ($u.password_hash -eq $hashPrueba) { "FALLA el usuario '$($u.username)' tiene la clave de prueba publica: ejecuta 6.2b" } else { "OK    usuario $($u.username) ($($u.role))" } }
}
git -C $Backend update-index --skip-worktree users.json
```

**6.2b. Solo si el bloque anterior dio `FALLA`:** reemplaza `users.json` por un solo admin, con el
hash SHA-256 en minúsculas que espera `app/routers/auth.py`.

```powershell
. {
  $ErrorActionPreference = 'Stop'
  $u      = Read-Host 'Usuario del admin del SGFF (p. ej. admin)'
  $nombre = Read-Host 'Nombre visible'
  $c      = Get-Credential -UserName $u -Message 'Clave del admin del SGFF'
  $sha    = [Security.Cryptography.SHA256]::Create()
  $hash   = -join ($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($c.GetNetworkCredential().Password)) | ForEach-Object { $_.ToString('x2') })
  $json   = ConvertTo-Json -InputObject @([ordered]@{ username = $u; name = $nombre; role = 'admin'; password_hash = $hash })
  [IO.File]::WriteAllText("$Backend\users.json", $json, (New-Object Text.UTF8Encoding($false)))
  $script:AdminCred = $c
  'OK    users.json con 1 admin'
}
git -C $Backend update-index --skip-worktree users.json
```

`--skip-worktree` evita que git marque `users.json` como cambio o lo pise en un `pull`. Si un pull
futuro trae cambios a ese archivo, el pull se detiene: ver el Paso 14.

### 6.3 `logging.json`: logs a archivo

Sin este archivo, los errores del backend se pierden: corre sin consola.

```powershell
. {
  $ErrorActionPreference = 'Stop'
  $cfg = [ordered]@{
    version = 1; disable_existing_loggers = $false
    formatters = [ordered]@{
      default = @{ format = '%(asctime)s %(levelname)s %(name)s %(message)s' }
      access  = [ordered]@{ '()' = 'uvicorn.logging.AccessFormatter'; fmt = '%(asctime)s %(client_addr)s "%(request_line)s" %(status_code)s'; use_colors = $false }
    }
    handlers = [ordered]@{
      app    = [ordered]@{ class = 'logging.handlers.RotatingFileHandler'; filename = "$Logs\sgff.log";        maxBytes = 10485760; backupCount = 10; encoding = 'utf-8'; formatter = 'default' }
      access = [ordered]@{ class = 'logging.handlers.RotatingFileHandler'; filename = "$Logs\sgff-access.log"; maxBytes = 10485760; backupCount = 10; encoding = 'utf-8'; formatter = 'access' }
    }
    loggers = [ordered]@{
      uvicorn          = [ordered]@{ handlers = @('app');    level = 'INFO'; propagate = $false }
      'uvicorn.access' = [ordered]@{ handlers = @('access'); level = 'INFO'; propagate = $false }
    }
    root = [ordered]@{ handlers = @('app'); level = 'INFO' }
  }
  [IO.File]::WriteAllText("$Secretos\logging.json", ($cfg | ConvertTo-Json -Depth 6), (New-Object Text.UTF8Encoding($false)))
  'OK    logging.json'
}
```

---

## Paso 7. Frontend: build y junction

**7.1 Build.** El frontend se compila para la sub-ruta `/sgff/` (está fijado en su `vite.config.ts`).

```powershell
cd $Frontend
if (Get-Process node -ErrorAction SilentlyContinue) { 'OJO: hay procesos node corriendo. Si npm ci falla con EPERM, cierralos' }
npm ci --no-audit --no-fund
npx vite build
Select-String -Path "$Frontend\dist\index.html" -Pattern "/$SubRuta/assets/" -Quiet   # True = build para /sgff
```

Debe terminar con `✓ built in ...` y la última línea debe dar `True`. Los avisos de *chunks larger
than 500 kB* e `INEFFECTIVE_DYNAMIC_IMPORT` son normales. Si da `False`, el repo del frontend no
está al día: vuelve al Paso 4.

**Alternativa sin Node en el servidor:** en otro equipo, sobre el mismo commit, corre
`npm ci && npx vite build` y comprime `dist`. Cópialo y descomprímelo en `E:\EMSA\apps\sgff\frontend\dist`.

**7.2 Junction y verificación.** `app/main.py` busca el build en `backend\frontend\dist`. La junction
lo hace calzar con los dos repos lado a lado, sin tocar código, y `frontend/` ya está en el
`.gitignore` del backend.

```powershell
. {
  $ErrorActionPreference = 'Stop'
  if (-not (Test-Path "$Frontend\dist\index.html")) { throw 'No existe frontend\dist\index.html: el build fallo, revisa la salida de 7.1' }
  $j = Get-Item "$Backend\frontend" -ErrorAction SilentlyContinue
  if (-not $j) { New-Item -ItemType Junction -Path "$Backend\frontend" -Target $Frontend | Out-Null; 'OK    junction creada' }
  elseif ($j.LinkType -eq 'Junction') { 'OK    junction ya existia' }
  else { throw "$Backend\frontend existe y NO es una junction: revisalo a mano" }
  if (Test-Path "$Backend\frontend\dist\index.html") { 'OK    el backend ve el build' } else { throw 'El backend no ve dist a traves de la junction' }
}
```

> ⚠️ **Nunca borres la junction con `Remove-Item -Recurse`.** En PowerShell 5.1 puede borrar el
> contenido del repo del frontend. Para quitarla usa solo `cmd /c rmdir "$Backend\frontend"`.

---

## Paso 8. Prueba manual como administrador

Levanta el backend en segundo plano, lo prueba y lo apaga. Si te pide credenciales, son las del
**admin del SGFF**.

```powershell
Stop-Sgff
$err = "$env:TEMP\sgff-prueba-err.log"
$null = Start-Process -FilePath "$Venv\python.exe" -ArgumentList "-m uvicorn app.main:app --host 127.0.0.1 --port $Puerto" -WorkingDirectory $Backend -NoNewWindow -RedirectStandardOutput "$env:TEMP\sgff-prueba-out.log" -RedirectStandardError $err -PassThru
$ok = Wait-Sgff
if ($ok) { Test-Sgff }
Stop-Sgff
if (-not $ok) { 'FALLA el backend no levanto. Ultimas lineas:'; Get-Content $err -Tail 30 }
```

Deben salir tres `OK` (health, interfaz y login) y `OK SGFF detenido`.

> No abras `http://127.0.0.1:8007` en un navegador para revisar la interfaz: el HTML pide los
> archivos a `/sgff/assets/...`, que solo existe pasando por IIS. Para eso está el Paso 12.

- [ ] health · [ ] interfaz · [ ] login

---

## Paso 9. Permisos para LOCAL SERVICE

LOCAL SERVICE recibe lectura del código, del `.env` y del `logging.json`, más escritura sobre
`users.json` (la pantalla Usuarios lo modifica) y sobre los logs. La app no escribe en ningún otro
lugar del disco. Se usan SID para no depender del idioma: `*S-1-5-18` es SYSTEM, `*S-1-5-32-544`
es Administradores y `*S-1-5-19` es LOCAL SERVICE.

```powershell
icacls $Raiz /grant "${SvcSid}:(OI)(CI)RX"
icacls "$Backend\users.json" /grant "${SvcSid}:M"
icacls "$Backend\.env" /inheritance:r /grant:r "*S-1-5-18:F" "*S-1-5-32-544:F" "${SvcSid}:R"
icacls $Secretos /inheritance:r /grant:r "*S-1-5-18:(OI)(CI)F" "*S-1-5-32-544:(OI)(CI)F" "${SvcSid}:(OI)(CI)RX"
icacls $Logs /grant "${SvcSid}:(OI)(CI)M"
icacls "$Backend\.env"
```

La última línea debe mostrar `NT AUTHORITY\LOCAL SERVICE:(R)`, Administradores y SYSTEM.

Opcional: los logs traen IPs. Si quieres cortar la herencia en esa carpeta, aplica
`/inheritance:r` como en `$Secretos`, con `"${SvcSid}:(OI)(CI)M"`.

---

## Paso 10. Tarea programada

**10.1 Registrar la tarea.** `-Force` reemplaza la tarea si ya existe.

```powershell
Stop-Sgff
. {
  $ErrorActionPreference = 'Stop'
  foreach ($p in $Venv, $Secretos, $Logs) { if ($p -match '\s') { throw "La ruta '$p' tiene espacios: la accion de la tarea no los soporta" } }
  $arg = "/c $Venv\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port $Puerto --log-config $Secretos\logging.json >> $Logs\sgff-consola.log 2>&1"
  $accion     = New-ScheduledTaskAction -Execute "$env:SystemRoot\System32\cmd.exe" -Argument $arg -WorkingDirectory $Backend
  $disparador = New-ScheduledTaskTrigger -AtStartup
  $ajustes    = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) `
                -MultipleInstances IgnoreNew -StartWhenAvailable -Priority 5
  $cuenta     = New-ScheduledTaskPrincipal -UserId $SvcCuenta -LogonType ServiceAccount -RunLevel Limited
  Register-ScheduledTask -TaskName $Tarea -Action $accion -Trigger $disparador -Settings $ajustes -Principal $cuenta `
    -Description "SGFF backend + frontend (uvicorn 127.0.0.1:$Puerto)" -Force | Out-Null
  "OK    tarea registrada como $SvcCuenta"
}
```

La prioridad 5 es normal. Por defecto, las tareas corren con prioridad baja (7).

**10.2 Iniciar y verificar:**

```powershell
Start-ScheduledTask -TaskName $Tarea
if (Wait-Sgff) { 'OK    la tarea levanto el SGFF'; Test-Sgff; Get-SgffDiag } else { 'FALLA la tarea no levanto el SGFF. Diagnostico:'; Get-SgffDiag }
```

Debe decir `resultado 0x41301 en ejecucion` y mostrar procesos como `LOCAL SERVICE`. Es normal
ver tres procesos: `cmd.exe`, el `python.exe` del `.venv` y el intérprete base, que el `.venv` lanza
como proceso hijo.

**10.3 Instalaciones anteriores: retirar la cuenta `svc_sgff`.** Las primeras pruebas, de noviembre
de 2026, crearon una cuenta local con clave para la tarea. Con LOCAL SERVICE ya no se usa, y una
cuenta con clave que nadie usa es un riesgo. Si no existe, el bloque no hace nada.

```powershell
. {
  $viejo = "$env:COMPUTERNAME\svc_sgff"
  if (-not (Get-LocalUser -Name svc_sgff -ErrorAction SilentlyContinue)) { 'OK    svc_sgff no existe: nada que limpiar'; return }
  if ((Get-ScheduledTask -TaskName $Tarea).Principal.UserId -match 'svc_sgff') { 'FALLA la tarea todavia usa svc_sgff: repite 10.1 antes'; return }
  foreach ($p in $Raiz, "$Backend\users.json", "$Backend\.env", $Secretos, $Logs) { icacls $p /remove $viejo | Out-Null }
  Remove-LocalUser -Name svc_sgff
  'OK    svc_sgff eliminada y quitada de los permisos'
}
```

---

## Paso 11. IIS: la aplicación `/sgff`

**11.1 `web.config`** de la aplicación. La carpeta `$IisDir` contiene solo este archivo: todo lo
sirve el backend. Dentro de una aplicación de IIS, la URL que ve la regla ya viene **sin** `/sgff`,
así que `{R:1}` es la ruta que espera el backend.

```powershell
. {
  $ErrorActionPreference = 'Stop'
  $xml = @"
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <system.webServer>
    <rewrite>
      <rules>
        <clear />
        <rule name="sgff-backend" stopProcessing="true">
          <match url="^(.*)$" />
          <action type="Rewrite" url="http://127.0.0.1:$Puerto/{R:1}" appendQueryString="true" />
        </rule>
      </rules>
    </rewrite>
    <httpErrors existingResponse="PassThrough" />
    <security>
      <requestFiltering>
        <requestLimits maxAllowedContentLength="104857600" />
      </requestFiltering>
    </security>
  </system.webServer>
</configuration>
"@
  [IO.File]::WriteAllText("$IisDir\web.config", $xml, (New-Object Text.UTF8Encoding($false)))
  'OK    web.config'
}
```

- `<clear />`: la aplicación no hereda las reglas de reescritura del Default Web Site.
- `PassThrough`: IIS no reemplaza los 401 y 503 del backend por sus páginas genéricas.
- `maxAllowedContentLength`: sube a 100 MB el límite de subida. Por defecto son unos 30 MB, y la
  pantalla de carga sube planillas Excel.

**11.2 Proxy de ARR, app pool, aplicación y autenticación:**

```powershell
. {
  $ErrorActionPreference = 'Stop'
  $px = Get-WebConfigurationProperty -PSPath 'MACHINE/WEBROOT/APPHOST' -Filter 'system.webServer/proxy' -Name enabled
  if ($(if ($px -is [bool]) { $px } else { [bool]$px.Value })) { 'OK    proxy de ARR ya estaba activo' }
  else { Set-WebConfigurationProperty -PSPath 'MACHINE/WEBROOT/APPHOST' -Filter 'system.webServer/proxy' -Name enabled -Value $true; 'OK    proxy de ARR activado' }
  if (-not (Test-Path IIS:\AppPools\SGFF)) { New-WebAppPool -Name SGFF | Out-Null; 'OK    app pool SGFF creado' }
  Set-ItemProperty IIS:\AppPools\SGFF -Name managedRuntimeVersion -Value ''
  if (-not (Get-WebApplication -Site $SitioIis -Name $SubRuta)) {
    New-WebApplication -Site $SitioIis -Name $SubRuta -PhysicalPath $IisDir -ApplicationPool SGFF | Out-Null
    "OK    aplicacion /$SubRuta creada en '$SitioIis'"
  } else { "OK    aplicacion /$SubRuta ya existia" }
  $loc = "$SitioIis/$SubRuta"
  Set-WebConfigurationProperty -PSPath 'MACHINE/WEBROOT/APPHOST' -Location $loc -Filter 'system.webServer/security/authentication/anonymousAuthentication' -Name enabled -Value $true
  try { Set-WebConfigurationProperty -PSPath 'MACHINE/WEBROOT/APPHOST' -Location $loc -Filter 'system.webServer/security/authentication/windowsAuthentication' -Name enabled -Value $false } catch { }
  "OK    /$SubRuta con acceso anonimo (el SGFF tiene su propio login)"
  $a = Get-WebApplication -Site $SitioIis -Name $SubRuta
  "OK    /$SubRuta -> $($a.PhysicalPath) (pool $($a.applicationPool))"
}
```

- **Proxy de ARR:** es un ajuste de todo el servidor, pero solo afecta a las reglas que reescriben
  hacia otra URL (`http://...`), como la del SGFF. Si otra app ya hace proxy, estará activo y el
  bloque no cambia nada. Si estaba apagado, ninguna otra app lo estaba usando.
- **Autenticación:** si el Default Web Site exige autenticación de Windows, la aplicación la
  heredaría y el navegador pediría usuario de dominio antes del login del SGFF. El bloque la
  desactiva **solo para `/sgff`**.
- El puerto 80 del Default Web Site ya está abierto en el firewall: no hace falta otra regla.

**11.3 Instalaciones anteriores: retirar el sitio del puerto 8080.** Las primeras pruebas publicaron
el SGFF como un sitio propio en el puerto 8080. Si no existe, el bloque no hace nada.

```powershell
. {
  $ErrorActionPreference = 'Stop'
  if (Test-Path IIS:\Sites\SGFF) { Stop-Website -Name SGFF; Remove-Website -Name SGFF; 'OK    sitio SGFF (puerto 8080) eliminado' } else { 'OK    no hay sitio SGFF aparte' }
  $fw = Get-NetFirewallRule -DisplayName 'SGFF IIS 8080' -ErrorAction SilentlyContinue
  if ($fw) { $fw | Remove-NetFirewallRule; 'OK    regla de firewall del 8080 eliminada' } else { 'OK    no hay regla de firewall del 8080' }
}
```

El app pool `SGFF` y la carpeta `C:\inetpub\sgff` se mantienen: ahora los usa la aplicación `/sgff`.

---

## Paso 12. Verificación final

Desde el servidor, pasando por IIS:

```powershell
Test-Sgff $UrlLocal
(Invoke-WebRequest "$UrlLocal/favicon.svg" -UseBasicParsing).Headers['Content-Type']   # image/svg+xml
Get-Content "$Logs\sgff-access.log" -Tail 5
```

Desde un PC de la oficina, abre `http://<servidor>/sgff`:

- [ ] Carga la pantalla de login y entra con el `admin`.
- [ ] Al recargar la página (F5) estando en una pantalla interna, por ejemplo `/sgff/saldo`, sigue cargando.
- [ ] Home, Saldo de contratos, Estados de pago y Metros muestran datos (eso prueba el SQL principal y el BI).
- [ ] Licitaciones y Modificaciones muestran datos de Monday (si dan 503, falta el token).
- [ ] Las otras apps del servidor siguen funcionando.
- [ ] En `sgff-access.log` aparece la IP de tu PC, no `127.0.0.1`.
- [ ] Reinicia el servidor (en una ventana acordada) y confirma que el SGFF levanta solo: pega el
      Paso 1 y ejecuta `Get-SgffDiag` y `Test-Sgff $UrlLocal`.

Registra la instalación en el worklog del backend: fecha, los commits de los dos repos y quién la hizo.

---

## Paso 13. Operación diaria

Pega el Paso 1 y usa:

```powershell
Get-SgffDiag                                       # estado de la tarea, procesos y ultimas lineas de log
Stop-Sgff                                          # detener (incluye procesos que queden vivos)
Start-ScheduledTask -TaskName $Tarea; Wait-Sgff    # iniciar (True = levanto)
Test-Sgff $UrlLocal                                # health, interfaz y login, pasando por IIS
Get-Content "$Logs\sgff-access.log" -Tail 20 -Wait # accesos en vivo
```

---

## Paso 14. Actualizar a una versión nueva

Pega el Paso 1. Después:

```powershell
# 0. anotar desde donde partes (para volver atras)
$antesBack = git -C $Backend rev-parse --short HEAD; $antesFront = git -C $Frontend rev-parse --short HEAD
"antes: backend $antesBack | frontend $antesFront"
Compress-Archive -Path "$Frontend\dist\*" -DestinationPath "$Backups\dist-$antesFront-$(Get-Date -Format yyyyMMdd-HHmm).zip"
Copy-Item "$Backend\users.json" "$Backups\users-$(Get-Date -Format yyyyMMdd-HHmm).json"

# 1. backend
Stop-Sgff
git -C $Backend pull --ff-only
& "$Venv\python.exe" -m pip install -r "$Backend\requirements.txt"
& "$Venv\python.exe" -m compileall -q "$Backend\app"

# 2. frontend
git -C $Frontend pull --ff-only
cd $Frontend; npm ci --no-audit --no-fund; npx vite build

# 3. levantar y verificar
Start-ScheduledTask -TaskName $Tarea
if (Wait-Sgff) { Test-Sgff $UrlLocal } else { Get-SgffDiag }
git -C $Backend log -1 --format='backend  %h %s'; git -C $Frontend log -1 --format='frontend %h %s'
```

Los respaldos de `users.json` en `$Backups` traen los hashes de las claves. Si `$Backups` hereda
permisos amplios, aplícale `/inheritance:r` como a `$Secretos`.

**Si el pull se detiene por `users.json`** (alguien lo cambió en el repo):

```powershell
git -C $Backend update-index --no-skip-worktree users.json
git -C $Backend stash push users.json
git -C $Backend pull --ff-only
git -C $Backend checkout stash@{0} -- users.json; git -C $Backend stash drop
git -C $Backend update-index --skip-worktree users.json
```

Con esto mantienes los usuarios reales. Repite la verificación del Paso 6.2.

---

## Paso 15. Volver atrás o desinstalar

**Volver a la versión anterior** (usa los hashes del Paso 14):

```powershell
Stop-Sgff
git -C $Backend checkout $antesBack
& "$Venv\python.exe" -m compileall -q "$Backend\app"
Expand-Archive "$Backups\dist-<hash>-<fecha>.zip" -DestinationPath "$Frontend\dist" -Force
Start-ScheduledTask -TaskName $Tarea; Wait-Sgff
```

Esto deja el repo en *detached HEAD*. Para volver a seguir `main`: `git -C $Backend checkout main`.

**Desinstalar** (no toca nada de otras apps):

```powershell
Stop-Sgff; Unregister-ScheduledTask -TaskName $Tarea -Confirm:$false
Remove-WebApplication -Site $SitioIis -Name $SubRuta; Remove-WebAppPool -Name SGFF
cmd /c rmdir "$Backend\frontend"     # quita SOLO la junction
# las carpetas de E:\EMSA\apps\sgff, secretos, logs, backups y C:\inetpub\sgff se borran a mano, mirando antes que contienen
```

---

## Si algo falla

Primero ejecuta `Get-SgffDiag`: muestra el resultado de la tarea, los procesos y los últimos logs.

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| Paso 6.1: `FALLA` en un SQL | Ver la tabla del Paso 6.1 | Clave correcta, clave sin `; { }` o acceso a la base |
| Paso 7.1: `npm ci` da `EPERM` | Un Vite o Node sigue corriendo | Ciérralo, borra `node_modules` y repite |
| Paso 7.1: `vite build` dice que la versión de Node no sirve | Node antiguo | Actualiza Node a 22 LTS o usa la alternativa de otro equipo |
| Paso 7.1 da `False` o `Test-Sgff` dice “el build no es para /sgff” | El frontend es anterior a la sub-ruta | Paso 4 (pull) y Paso 7 |
| `interfaz` da `Not Found` | El backend no vio `dist` al arrancar | Paso 7.2 y reinicia (Stop-Sgff y Start-ScheduledTask) |
| `login` da 401 | Clave equivocada al probar, o hash mal generado | Prueba de nuevo con `$AdminCred = $null; Test-Sgff`. Si sigue, haz el 6.2b |
| `login` da 503 | Falta `users.json` o LOCAL SERVICE no puede leerlo | Paso 6.2 y Paso 9 |
| Tarea con resultado `0x1` | Python se cayó al arrancar | Lee `sgff-consola.log` en el diagnóstico: casi siempre es un permiso (Paso 9) o el `.env` |
| `PermissionError` o `Access is denied` en `sgff-consola.log` | A LOCAL SERVICE le falta un permiso | Repite el Paso 9 y vuelve al 10.2 |
| `[WinError 10013]` o `10048` | Puerto reservado u ocupado | `Stop-Sgff`; si sigue, Paso 2 (rangos reservados) y cambia `$Puerto` aquí, en la tarea y en el `web.config` |
| `http://<servidor>/sgff` da 404 de IIS | No existe la aplicación `/sgff` o falta URL Rewrite | Paso 2 y Paso 11 |
| `/sgff` da 502 | Backend caído o proxy de ARR apagado | `Get-SgffDiag`; Paso 11.2 |
| El navegador pide usuario de Windows antes del login | La aplicación heredó la autenticación de Windows del sitio | Paso 11.2 |
| Página en blanco; en la consola del navegador, 404 en `/sgff/assets/...` | Build viejo o junction rota | Paso 7 |
| El login entra y vuelve a pedir clave | Token antiguo en el navegador o `JWT_SECRET` cambiado | Cierra sesión o borra los datos del sitio en el navegador y entra de nuevo |
| 413 al subir una planilla | Límite de IIS | `maxAllowedContentLength` en el `web.config` |
| “Usuarios” no guarda | LOCAL SERVICE no tiene `M` sobre `users.json` | Paso 9 |
| Pantallas vacías, sin error en la UI | Falla de SQL silenciada (backlog, ítem 10) | Confirmación del Paso 6.1 y `sgff.log` |
| Monday da 503 | Falta `MONDAY_API_KEY` o `MONDAY_BOARD_ID` | Paso 6.1 |
| Monday da timeout | El servidor sale a internet por un proxy | Agrega `HTTPS_PROXY=http://<proxy>:<puerto>` al `.env` (el 6.1 lo mantiene si repites el paso) y reinicia |
| `git`: *detected dubious ownership* | El clon es de otro administrador | `git config --global --add safe.directory E:/EMSA/apps/sgff/backend` (y lo mismo para `frontend`) |

---

## Antes de abrir el SGFF a más usuarios

Pendientes del código que afectan a producción (detalle en [`BACKLOG.md`](BACKLOG.md)):

1. **La API no exige token** (ítem 1b). Cualquiera que llegue a `http://<servidor>/sgff/api/*`
   puede leer y cargar datos sin hacer login. Mientras no se arregle, conviene limitar la aplicación
   `/sgff` con *IP and Domain Restrictions* de IIS al rango de la oficina.
2. Contraseñas con SHA-256 sin sal (ítem 2) y CORS abierto (ítem 3). Con el mismo origen, CORS es un
   riesgo menor.
3. Dependencias sin versión fija (ítem 9): cada `pip install` puede traer versiones distintas.
4. Claves SQL con `;`, `{` o `}` y elección del driver ODBC (ítem 7).

## Fuera de este runbook

- **ETL** (`etl/`: Power BI → `dbo.proyecciones`). **No lo actives** hasta resolver la carga AdC
  (backlog, ítem 1a): la próxima carga hace `TRUNCATE` y borra las filas AdC. `schedule_etl.ps1`
  además trae rutas fijas.
- `setup_servicio.ps1`, `run_servicio.bat` y `start.ps1` son la instalación anterior, en el equipo
  de desarrollo (backlog, ítem 6). En el servidor no se usan.
- **HTTPS**, que se coordina con el resto de las apps del servidor.
