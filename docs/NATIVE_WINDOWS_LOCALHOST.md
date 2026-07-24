# Native Windows Localhost Development

This is the no-Docker setup for running Political AI Filter on Windows for development.

Use this when you want the app on:

- Public frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- Internal app: `http://localhost:8000/internal`

The internal development login is:

- Username: `admin`
- Password: `admin`

## The Three Commands

Most of the time, these are the only commands you need.

Run all commands from the repository root:

```powershell
cd D:\repos\PoliticalAiFilter
```

Install or repair local development dependencies:

```powershell
.\scripts\dev-local.ps1 install
```

Start the app:

```powershell
.\scripts\dev-local.ps1 run
```

Stop the app:

```powershell
.\scripts\dev-local.ps1 shutdown
```

## First Time Setup

### Step 1: Open PowerShell

Open a normal PowerShell window.

Go to the repository:

```powershell
cd D:\repos\PoliticalAiFilter
```

### Step 2: Let The Script Upgrade Basic Tools

Run:

```powershell
.\scripts\dev-local.ps1 install -UpgradeTools
```

This checks the basic tools and installs or upgrades what it safely can.

It can handle:

- Git
- Python 3.12
- Node.js
- npm
- PostgreSQL if missing

If Node.js is managed by nvm-windows, the script uses `nvm install` and `nvm use`.

If the script says a command is still old or missing after installing, close PowerShell, open a new PowerShell window, go back to the repository, and run the same command again:

```powershell
cd D:\repos\PoliticalAiFilter
.\scripts\dev-local.ps1 install -UpgradeTools
```

### Step 3: Set The PostgreSQL Admin Password In `.env`

Open `.env`.

Make sure it contains this line:

```env
POSTGRES_ADMIN_PASSWORD=pgadmin
```

Use the real password for the local PostgreSQL `postgres` user. If you do not know it, use the reset step below.

### Step 4: Reset PostgreSQL Password If Needed

Skip this step if `POSTGRES_ADMIN_PASSWORD` already works.

If you do not know the local PostgreSQL `postgres` password:

1. Open PowerShell as Administrator.
2. Go to the repository:

```powershell
cd D:\repos\PoliticalAiFilter
```

3. Run:

```powershell
.\scripts\dev-local.ps1 reset-postgres-password -NewPostgresAdminPassword "pgadmin"
```

4. Close the Administrator PowerShell window.
5. In normal PowerShell, make sure `.env` has:

```env
POSTGRES_ADMIN_PASSWORD=pgadmin
```

The reset command backs up PostgreSQL authentication config, temporarily enables local trust auth, changes the password, restores the config, and restarts the PostgreSQL Windows service.

The default service name is `postgresql-x64-15`. If your service has a different name:

```powershell
.\scripts\dev-local.ps1 reset-postgres-password -PostgresServiceName "postgresql-x64-16" -NewPostgresAdminPassword "pgadmin"
```

### Step 5: Install Project Dependencies

Run:

```powershell
.\scripts\dev-local.ps1 install
```

Expected result near the end:

```text
Native local dependencies are ready.
```

This command:

- creates `.venv/`;
- installs backend Python dependencies;
- installs frontend npm dependencies;
- creates or updates PostgreSQL user `app_user`;
- creates database `politic_bs_filter`;
- verifies that `app_user` can log in.

### Step 6: Start The App

Run:

```powershell
.\scripts\dev-local.ps1 run
```

Expected result:

```text
Native local deployment is running.
Backend API: http://localhost:8000
Public frontend: http://localhost:5173
Internal app: http://localhost:8000/internal
```

Open:

- `http://localhost:5173`
- `http://localhost:8000/health`
- `http://localhost:8000/internal`

## Daily Use

Start work:

```powershell
cd D:\repos\PoliticalAiFilter
.\scripts\dev-local.ps1 run
```

Stop work:

```powershell
.\scripts\dev-local.ps1 shutdown
```

After dependency changes:

```powershell
.\scripts\dev-local.ps1 install
.\scripts\dev-local.ps1 run
```

## How To Know It Worked

Backend health should show:

```powershell
Invoke-WebRequest http://localhost:8000/health -UseBasicParsing
```

Expected content:

```json
{"status":"ok"}
```

Frontend should open in the browser:

```text
http://localhost:5173
```

Internal app should open here:

```text
http://localhost:8000/internal
```

## Troubleshooting

### PowerShell Blocks The Script

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev-local.ps1 install
```

### Node.js Is Too Old

Run:

```powershell
.\scripts\dev-local.ps1 install -UpgradeTools
```

If you use nvm-windows and want a specific Node.js major version:

```powershell
.\scripts\dev-local.ps1 install -UpgradeTools -TargetNodeMajor 24
```

Then close and reopen PowerShell if `node --version` still shows the old version.

### PostgreSQL Password Fails

Make sure `.env` has:

```env
POSTGRES_ADMIN_PASSWORD=pgadmin
```

If you do not know the password, reset it from PowerShell as Administrator:

```powershell
.\scripts\dev-local.ps1 reset-postgres-password -NewPostgresAdminPassword "pgadmin"
```

Then run:

```powershell
.\scripts\dev-local.ps1 install
```

### Port 8000 Or 5173 Is Already In Use

Stop any existing local app processes:

```powershell
.\scripts\dev-local.ps1 shutdown
```

If Docker Compose is running, stop it:

```powershell
docker compose down
```

Then start native localhost again:

```powershell
.\scripts\dev-local.ps1 run
```

### Backend Does Not Open

Check the backend error log:

```powershell
Get-Content .local-dev\backend.err.log -Tail 80
```

Backend startup runs Alembic migrations before Uvicorn starts. If migrations fail, `http://localhost:8000` will not open.

### Frontend Does Not Open

Check the frontend error log:

```powershell
Get-Content .local-dev\frontend.err.log -Tail 80
```

Reinstall frontend dependencies:

```powershell
.\scripts\dev-local.ps1 install
```

Then run again:

```powershell
.\scripts\dev-local.ps1 run
```

## What The Script Does Not Do

The native script does not start Docker, Redis, or Umami.

For this native development path:

- PostgreSQL runs as a normal Windows service.
- Backend runs as a local Python process.
- Frontend runs as a local Vite process.
- Runtime logs and process IDs go into `.local-dev/`.

Docker Compose remains available as a separate development path, but it uses separate container data.

## Advanced Options

Use a different PostgreSQL admin user:

```powershell
.\scripts\dev-local.ps1 install -PostgresAdminUser postgres
```

Pass the PostgreSQL admin password directly instead of reading `.env`:

```powershell
.\scripts\dev-local.ps1 install -PostgresAdminPassword "pgadmin"
```

Skip database setup:

```powershell
.\scripts\dev-local.ps1 install -SkipDatabaseSetup
```

Use different app ports:

```powershell
.\scripts\dev-local.ps1 run -BackendPort 8010 -FrontendPort 5174
```

Use different app database credentials:

```powershell
.\scripts\dev-local.ps1 install -AppDbName politic_bs_filter -AppDbUser app_user -AppDbPassword password
.\scripts\dev-local.ps1 run -AppDbName politic_bs_filter -AppDbUser app_user -AppDbPassword password
```
