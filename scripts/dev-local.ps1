param(
    [Parameter(Position = 0)]
    [ValidateSet("install", "run", "shutdown", "reset-postgres-password")]
    [string]$Action = "run",

    [string]$PostgresAdminUser = "postgres",
    [string]$AppDbName = "politic_bs_filter",
    [string]$AppDbUser = "app_user",
    [string]$AppDbPassword = "password",
    [string]$PostgresAdminPassword = "",
    [int]$TargetNodeMajor = 24,
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173,
    [string]$PostgresServiceName = "postgresql-x64-15",
    [string]$PostgresDataDir = "",
    [string]$NewPostgresAdminPassword = "",
    [switch]$SkipDatabaseSetup,
    [switch]$UpgradeTools
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Resolve-Path (Join-Path $ScriptDir "..")
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"
$VenvDir = Join-Path $RootDir ".venv"
$StateDir = Join-Path $RootDir ".local-dev"
$PidFile = Join-Path $StateDir "pids.json"
$BackendLog = Join-Path $StateDir "backend.log"
$FrontendLog = Join-Path $StateDir "frontend.log"
$script:SystemToolsChanged = $false

function Import-DotEnv {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        return
    }

    foreach ($line in Get-Content $Path) {
        $trimmed = $line.Trim()
        if ($trimmed.Length -eq 0 -or $trimmed.StartsWith("#")) {
            continue
        }

        $parts = $trimmed.Split("=", 2)
        if ($parts.Count -ne 2) {
            continue
        }

        $name = $parts[0].Trim()
        $value = $parts[1].Trim()
        if ($value.Length -ge 2 -and (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'")))) {
            $value = $value.Substring(1, $value.Length - 2)
        }

        if (-not [Environment]::GetEnvironmentVariable($name, "Process")) {
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

function Invoke-Checked {
    param(
        [scriptblock]$Command,
        [string]$FailureMessage
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw $FailureMessage
    }
}

function ConvertTo-SqlLiteral {
    param([string]$Value)

    return "'" + $Value.Replace("'", "''") + "'"
}

function ConvertTo-PostgresIdentifier {
    param([string]$Value)

    return '"' + $Value.Replace('"', '""') + '"'
}

function Write-Utf8NoBom {
    param(
        [string]$Path,
        [string]$Value
    )

    $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($Path, $Value, $utf8NoBom)
}

function Get-DatabaseUrl {
    return "postgresql+psycopg://${AppDbUser}:${AppDbPassword}@localhost:5432/${AppDbName}"
}

function Assert-Command {
    param(
        [string]$Name,
        [string]$InstallHint
    )

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Missing required command '$Name'. $InstallHint"
    }
}

function Assert-Winget {
    if (-not (Get-Command "winget" -ErrorAction SilentlyContinue)) {
        throw "Missing required command 'winget'. Install the tool manually or install App Installer from Microsoft Store."
    }
}

function Invoke-WingetInstall {
    param(
        [string]$PackageId,
        [string]$DisplayName
    )

    Assert-Winget
    Write-Host "Installing or upgrading $DisplayName with winget..."
    Invoke-Checked { & winget install --id $PackageId --exact --source winget --accept-package-agreements --accept-source-agreements } "winget could not install or upgrade $DisplayName."
    $script:SystemToolsChanged = $true
}

function Update-ProcessPath {
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $processPath = [Environment]::GetEnvironmentVariable("Path", "Process")
    $paths = @($machinePath, $userPath, $processPath) -join ";"
    $env:Path = (($paths -split ";") | Where-Object { $_ } | Select-Object -Unique) -join ";"
}

function Test-NodeIsManagedByNvm {
    $nodeCommand = Get-Command "node" -ErrorAction SilentlyContinue
    if ($null -eq $nodeCommand) {
        return $false
    }

    return $nodeCommand.Source -match "\\nvm4w\\|\\nvm\\"
}

function Invoke-NvmNodeInstall {
    Assert-Command "nvm" "Install Node.js LTS manually, then reopen PowerShell."
    Write-Host "Node.js is managed by nvm-windows. Installing and selecting Node.js $TargetNodeMajor..."
    Invoke-Checked { & nvm install $TargetNodeMajor } "nvm could not install Node.js $TargetNodeMajor."
    Invoke-Checked { & nvm use $TargetNodeMajor } "nvm could not switch to Node.js $TargetNodeMajor. You may need to rerun PowerShell as Administrator, or run 'nvm use $TargetNodeMajor' manually."
    $script:SystemToolsChanged = $true
}

function Get-NodeMajorVersion {
    if (-not (Get-Command "node" -ErrorAction SilentlyContinue)) {
        return $null
    }

    $versionText = (& node --version).Trim()
    $versionMatch = [regex]::Match($versionText, "^v(?<major>\d+)\.")
    if (-not $versionMatch.Success) {
        throw "Could not read Node.js version from '$versionText'."
    }

    return [int]$versionMatch.Groups["major"].Value
}

function Get-PostgresMajorVersion {
    if (-not (Get-Command "psql" -ErrorAction SilentlyContinue)) {
        return $null
    }

    $versionText = (& psql --version).Trim()
    $versionMatch = [regex]::Match($versionText, "\s(?<major>\d+)\.")
    if (-not $versionMatch.Success) {
        throw "Could not read PostgreSQL client version from '$versionText'."
    }

    return [int]$versionMatch.Groups["major"].Value
}

function Install-SystemTools {
    Write-Host "Checking system tools..."

    if (-not (Get-Command "git" -ErrorAction SilentlyContinue)) {
        Invoke-WingetInstall "Git.Git" "Git"
    }

    if (-not (Get-Command "py" -ErrorAction SilentlyContinue) -and -not (Get-Command "python" -ErrorAction SilentlyContinue)) {
        Invoke-WingetInstall "Python.Python.3.12" "Python 3.12"
    }
    elseif (Get-Command "py" -ErrorAction SilentlyContinue) {
        & py -3.12 --version *> $null
        if ($LASTEXITCODE -ne 0) {
            Invoke-WingetInstall "Python.Python.3.12" "Python 3.12"
        }
    }

    $nodeMajor = Get-NodeMajorVersion
    if ($null -eq $nodeMajor -or $nodeMajor -lt 20) {
        if (Test-NodeIsManagedByNvm) {
            Invoke-NvmNodeInstall
        }
        else {
            Invoke-WingetInstall "OpenJS.NodeJS.LTS" "Node.js LTS"
        }
        Update-ProcessPath
    }

    $postgresMajor = Get-PostgresMajorVersion
    if ($null -eq $postgresMajor) {
        Invoke-WingetInstall "PostgreSQL.PostgreSQL.16" "PostgreSQL 16"
    }
    elseif ($postgresMajor -lt 15) {
        throw "PostgreSQL 15 or newer is required. Current psql major version is $postgresMajor. Upgrade PostgreSQL manually because major PostgreSQL upgrades can require data migration."
    }

    if ($script:SystemToolsChanged) {
        Update-ProcessPath
        Write-Host "System tools were installed or upgraded. If a command is still not found or still reports an old version, reopen PowerShell and rerun this script."
    }
}

function Assert-NodeVersion {
    Assert-Command "node" "Install Node.js 20 or newer, then reopen PowerShell."
    $versionText = (& node --version).Trim()
    $major = Get-NodeMajorVersion
    if ($major -lt 20) {
        throw "Node.js 20 or newer is required. Current version is $versionText. Run '.\scripts\dev-local.ps1 install -UpgradeTools', or install Node.js LTS and reopen PowerShell."
    }
}

function Invoke-ProjectPython {
    param([string[]]$Arguments)

    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3.12 @Arguments
        return
    }

    Assert-Command "python" "Install Python 3.12 or newer, then reopen PowerShell."
    & python @Arguments
}

function Set-AppEnvironment {
    $env:DATABASE_URL = Get-DatabaseUrl
    $env:REDIS_URL = "redis://localhost:6379/0"
    $env:APP_ENV = "development"
    $env:APP_SECRET_KEY = "change-this-development-secret"
    $env:SESSION_COOKIE_NAME = "politic_bs_session"
    $env:ROOT_ADMIN_USERNAME = "admin"
    $env:ROOT_ADMIN_PASSWORD_HASH = "plain:admin"
    $env:ROOT_ADMIN_ENABLED = "true"
    $env:PUBLIC_BASE_URL = "http://localhost:$FrontendPort"
    $env:BACKEND_BASE_URL = "http://localhost:$BackendPort"
    $env:MEDIA_STORAGE_PATH = Join-Path $BackendDir "media"
    $env:CORS_ALLOWED_ORIGINS = "http://localhost:$FrontendPort"
    $env:VITE_API_BASE_URL = "http://localhost:$BackendPort/api"
    $env:VITE_PUBLIC_BASE_URL = "http://localhost:$FrontendPort"
}

function Initialize-StateDirectory {
    if (-not (Test-Path $StateDir)) {
        New-Item -ItemType Directory -Path $StateDir | Out-Null
    }
}

function Assert-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "This action must be run from PowerShell as Administrator."
    }
}

function Get-PostgresDataDirectory {
    if ($PostgresDataDir) {
        return (Resolve-Path $PostgresDataDir).Path
    }

    $service = Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\$PostgresServiceName" -ErrorAction Stop
    $imagePath = $service.ImagePath
    $match = [regex]::Match($imagePath, "-D\s+`"(?<path>[^`"]+)`"")
    if (-not $match.Success) {
        $match = [regex]::Match($imagePath, "-D\s+(?<path>\S+)")
    }
    if (-not $match.Success) {
        throw "Could not detect PostgreSQL data directory from service '$PostgresServiceName'. Pass -PostgresDataDir explicitly."
    }

    return (Resolve-Path $match.Groups["path"].Value).Path
}

function Set-LocalPostgresTrustAuth {
    param(
        [string]$PgHbaPath
    )

    $lines = Get-Content -Path $PgHbaPath
    $updated = foreach ($line in $lines) {
        if ($line -match "^\s*local\s+all\s+all\s+\S+") {
            "local   all             all                                     trust"
        }
        elseif ($line -match "^\s*host\s+all\s+all\s+127\.0\.0\.1/32\s+\S+") {
            "host    all             all             127.0.0.1/32            trust"
        }
        elseif ($line -match "^\s*host\s+all\s+all\s+::1/128\s+\S+") {
            "host    all             all             ::1/128                 trust"
        }
        else {
            $line
        }
    }

    $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllLines($PgHbaPath, [string[]]$updated, $utf8NoBom)
}

function Reset-PostgresPassword {
    Assert-Administrator
    Assert-Command "psql" "Install PostgreSQL and add its bin folder to PATH, then reopen PowerShell."

    if (-not $NewPostgresAdminPassword) {
        throw "Pass -NewPostgresAdminPassword with the new local PostgreSQL '$PostgresAdminUser' password."
    }

    $dataDir = Get-PostgresDataDirectory
    $pgHbaPath = Join-Path $dataDir "pg_hba.conf"
    if (-not (Test-Path $pgHbaPath)) {
        throw "Could not find pg_hba.conf at $pgHbaPath."
    }

    Initialize-StateDirectory
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $backupPath = Join-Path $StateDir "pg_hba.$timestamp.conf.bak"
    Copy-Item -LiteralPath $pgHbaPath -Destination $backupPath

    $postgresUserIdentifier = ConvertTo-PostgresIdentifier $PostgresAdminUser
    $passwordLiteral = ConvertTo-SqlLiteral $NewPostgresAdminPassword
    Write-Host "Backed up pg_hba.conf to $backupPath"
    Write-Host "Temporarily enabling local trust auth..."

    try {
        Set-LocalPostgresTrustAuth $pgHbaPath
        Restart-Service -Name $PostgresServiceName -Force -ErrorAction Stop

        Write-Host "Resetting PostgreSQL password for '$PostgresAdminUser'..."
        Invoke-Checked { & psql -w -v ON_ERROR_STOP=1 -h localhost -U $PostgresAdminUser -d postgres -c "ALTER USER $postgresUserIdentifier WITH PASSWORD $passwordLiteral;" } "Could not reset PostgreSQL password."

        Write-Host "Updating current process POSTGRES_ADMIN_PASSWORD..."
        $env:POSTGRES_ADMIN_PASSWORD = $NewPostgresAdminPassword
    }
    finally {
        Write-Host "Restoring original pg_hba.conf..."
        Copy-Item -LiteralPath $backupPath -Destination $pgHbaPath -Force
        Restart-Service -Name $PostgresServiceName -Force -ErrorAction Stop
    }

    $previousPgPassword = $env:PGPASSWORD
    try {
        $env:PGPASSWORD = $NewPostgresAdminPassword
        Invoke-Checked { & psql -w -v ON_ERROR_STOP=1 -h localhost -U $PostgresAdminUser -d postgres -c "select current_user;" } "Password reset verification failed."
    }
    finally {
        $env:PGPASSWORD = $previousPgPassword
    }

    Write-Host "PostgreSQL password reset complete. Put this value in .env as POSTGRES_ADMIN_PASSWORD."
}

function Initialize-Database {
    if ($SkipDatabaseSetup) {
        Write-Host "Skipping PostgreSQL database setup."
        return
    }

    Assert-Command "psql" "Install PostgreSQL 16 and add its bin folder to PATH, then reopen PowerShell."

    $adminPassword = $PostgresAdminPassword
    if (-not $adminPassword) {
        $adminPassword = $env:POSTGRES_ADMIN_PASSWORD
    }
    if (-not $adminPassword) {
        $adminPassword = $env:PGPASSWORD
    }

    Initialize-StateDirectory
    $SqlFile = Join-Path $StateDir "init-db.sql"
    $appUserLiteral = ConvertTo-SqlLiteral $AppDbUser
    $appPasswordLiteral = ConvertTo-SqlLiteral $AppDbPassword
    $appDbLiteral = ConvertTo-SqlLiteral $AppDbName
    $appUserIdentifier = ConvertTo-PostgresIdentifier $AppDbUser
    $appDbIdentifier = ConvertTo-PostgresIdentifier $AppDbName
    $createDatabaseSqlLiteral = ConvertTo-SqlLiteral "CREATE DATABASE $appDbIdentifier OWNER $appUserIdentifier"
    $Sql = @"
DO `$`$
BEGIN
    IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = $appUserLiteral) THEN
        ALTER ROLE $appUserIdentifier WITH LOGIN PASSWORD $appPasswordLiteral;
    ELSE
        CREATE ROLE $appUserIdentifier WITH LOGIN PASSWORD $appPasswordLiteral;
    END IF;
END
`$`$;

SELECT $createDatabaseSqlLiteral
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = $appDbLiteral)
\gexec

ALTER DATABASE $appDbIdentifier OWNER TO $appUserIdentifier;
"@
    Write-Utf8NoBom -Path $SqlFile -Value $Sql

    Write-Host "Ensuring PostgreSQL database '$AppDbName' and user '$AppDbUser' exist..."
    $previousPgPassword = $env:PGPASSWORD
    try {
        if ($adminPassword) {
            $env:PGPASSWORD = $adminPassword
        }

        Invoke-Checked { & psql -w -v ON_ERROR_STOP=1 -U $PostgresAdminUser -d postgres -f $SqlFile } "PostgreSQL setup failed. Add the correct POSTGRES_ADMIN_PASSWORD to .env or pass -PostgresAdminPassword, then run '.\scripts\dev-local.ps1 install' again."

        $env:PGPASSWORD = $AppDbPassword
        Invoke-Checked { & psql -w -v ON_ERROR_STOP=1 -U $AppDbUser -d $AppDbName -c "select current_user, current_database();" } "PostgreSQL app-user verification failed."
    }
    finally {
        $env:PGPASSWORD = $previousPgPassword
    }
}

function Install-LocalDev {
    if ($UpgradeTools) {
        Install-SystemTools
    }

    Assert-NodeVersion
    Assert-Command "npm" "Install Node.js 22 or newer, then reopen PowerShell."

    if (-not (Test-Path $VenvDir)) {
        Write-Host "Creating Python virtual environment..."
        Invoke-ProjectPython @("-m", "venv", $VenvDir)
    }

    $VenvPython = Join-Path $VenvDir "Scripts\python.exe"
    if (-not (Test-Path $VenvPython)) {
        throw "The virtual environment was not created correctly at $VenvDir."
    }

    Write-Host "Installing backend dependencies..."
    Invoke-Checked { & $VenvPython -m pip install -e $BackendDir } "Backend dependency installation failed."

    Write-Host "Installing frontend dependencies..."
    Push-Location $FrontendDir
    try {
        if (Test-Path (Join-Path $FrontendDir "package-lock.json")) {
            Invoke-Checked { & npm ci } "Frontend dependency installation failed."
        }
        else {
            Invoke-Checked { & npm install } "Frontend dependency installation failed."
        }
    }
    finally {
        Pop-Location
    }

    Initialize-Database

    $MediaDir = Join-Path $BackendDir "media"
    if (-not (Test-Path $MediaDir)) {
        New-Item -ItemType Directory -Path $MediaDir | Out-Null
    }

    Write-Host "Native local dependencies are ready."
}

function Read-StartedProcesses {
    if (-not (Test-Path $PidFile)) {
        return @()
    }

    $records = Get-Content $PidFile -Raw | ConvertFrom-Json
    if ($null -eq $records) {
        return @()
    }

    return @($records)
}

function Stop-LocalDev {
    $records = @(Read-StartedProcesses)
    if ($records.Count -eq 0) {
        Write-Host "No local dev process file found."
        return
    }

    foreach ($record in $records) {
        $process = Get-Process -Id $record.pid -ErrorAction SilentlyContinue
        if ($null -eq $process) {
            Write-Host "$($record.name) is already stopped."
            continue
        }

        Write-Host "Stopping $($record.name) on PID $($record.pid)..."
        Stop-Process -Id $record.pid
    }

    if (Test-Path $PidFile) {
        Remove-Item -LiteralPath $PidFile
    }
}

function Start-LocalDev {
    if ($UpgradeTools) {
        Install-SystemTools
    }

    Assert-NodeVersion
    Assert-Command "npm" "Install Node.js 22 or newer, then reopen PowerShell."
    Set-AppEnvironment

    $VenvPython = Join-Path $VenvDir "Scripts\python.exe"
    $AlembicExe = Join-Path $VenvDir "Scripts\alembic.exe"
    $UvicornExe = Join-Path $VenvDir "Scripts\uvicorn.exe"

    if (-not (Test-Path $VenvPython) -or -not (Test-Path $AlembicExe) -or -not (Test-Path $UvicornExe) -or -not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
        Write-Host "Local dependencies are missing. Running install first..."
        Install-LocalDev
        Set-AppEnvironment
    }

    Initialize-StateDirectory
    Stop-LocalDev

    Write-Host "Running Alembic migrations..."
    Push-Location $BackendDir
    try {
        Invoke-Checked { & $AlembicExe upgrade head } "Alembic migrations failed."
    }
    finally {
        Pop-Location
    }

    Write-Host "Starting backend..."
    $backendProcess = Start-Process `
        -FilePath $UvicornExe `
        -ArgumentList @("app.main:app", "--reload", "--host", "127.0.0.1", "--port", "$BackendPort") `
        -WorkingDirectory $BackendDir `
        -PassThru `
        -WindowStyle Hidden `
        -RedirectStandardOutput $BackendLog `
        -RedirectStandardError (Join-Path $StateDir "backend.err.log")

    Write-Host "Starting frontend..."
    $npmCommand = (Get-Command "npm.cmd" -ErrorAction SilentlyContinue)
    if ($null -eq $npmCommand) {
        $npmCommand = Get-Command "npm"
    }

    $frontendProcess = Start-Process `
        -FilePath $npmCommand.Source `
        -ArgumentList @("run", "dev", "--", "--host", "127.0.0.1") `
        -WorkingDirectory $FrontendDir `
        -PassThru `
        -WindowStyle Hidden `
        -RedirectStandardOutput $FrontendLog `
        -RedirectStandardError (Join-Path $StateDir "frontend.err.log")

    @(
        [pscustomobject]@{ name = "backend"; pid = $backendProcess.Id; url = "http://localhost:$BackendPort" },
        [pscustomobject]@{ name = "frontend"; pid = $frontendProcess.Id; url = "http://localhost:$FrontendPort" }
    ) | ConvertTo-Json | Set-Content -Path $PidFile -Encoding UTF8

    Write-Host "Native local deployment is running."
    Write-Host "Backend API: http://localhost:$BackendPort"
    Write-Host "Public frontend: http://localhost:$FrontendPort"
    Write-Host "Internal app: http://localhost:$BackendPort/internal"
    Write-Host "Logs: $StateDir"
    Write-Host "Run '.\scripts\dev-local.ps1 shutdown' to stop the app processes."
}

Import-DotEnv (Join-Path $RootDir ".env")

switch ($Action) {
    "install" { Install-LocalDev }
    "run" { Start-LocalDev }
    "shutdown" { Stop-LocalDev }
    "reset-postgres-password" { Reset-PostgresPassword }
}
