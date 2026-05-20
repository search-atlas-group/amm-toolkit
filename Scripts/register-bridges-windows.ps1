# Register the supervisor + 3 Mission Control bridges as scheduled tasks that
# run at user login.
#
# Architecture parity with macOS LaunchAgents:
#   supervisor       (port 8764) — always-on. RestartCount=999 + 1-min
#                                  interval = equivalent of KeepAlive=true.
#   command-center   (port 8865) — idle-shutdown after 5 min (RestartCount=0).
#   website-build    (port 8866) — idle-shutdown after 5 min.
#   website-rebuild  (port 8867) — idle-shutdown after 5 min.
#
# Usage:
#   .\register-bridges-windows.ps1 -ToolkitPath "C:\Users\xx\AMM-Workspace\amm-toolkit"

param(
  [Parameter(Mandatory=$true)]
  [string]$ToolkitPath
)

$ErrorActionPreference = "Stop"

# Find Git Bash for running the existing run.sh scripts
$GIT_BASH = "C:\Program Files\Git\bin\bash.exe"
if (-not (Test-Path $GIT_BASH)) {
  Write-Host "  [!]  Git Bash not found at $GIT_BASH — bridges won't auto-start"
  exit 1
}

# Each entry: Name, Port, AlwaysOn (mirrors launchd KeepAlive)
$services = @(
  @{ Name = "supervisor";      Port = 8764; AlwaysOn = $true  },
  @{ Name = "command-center";  Port = 8865; AlwaysOn = $false },
  @{ Name = "website-build";   Port = 8866; AlwaysOn = $false },
  @{ Name = "website-rebuild"; Port = 8867; AlwaysOn = $false }
)

foreach ($svc in $services) {
  $taskName = "SearchAtlasAMM-$($svc.Name)"
  # tools/ now lives under mission-control/ — parity with macOS setup.sh
  $runSh = "$ToolkitPath\mission-control\tools\$($svc.Name)\run.sh"

  if (-not (Test-Path $runSh)) {
    Write-Host "  [!]  $runSh not found — skipping"
    continue
  }

  # Convert Windows path to Unix-style for bash
  $unixPath = $runSh -replace "\\", "/" -replace "^([A-Za-z]):", { "/$($_.Value[0].ToString().ToLower())" }

  # Remove existing task if present (idempotent)
  schtasks /Query /TN $taskName >$null 2>&1
  if ($LASTEXITCODE -eq 0) {
    schtasks /Delete /TN $taskName /F >$null 2>&1
  }

  # The action runs Git Bash with the right PORT (and NO_BROWSER for the
  # bridges so they don't try to launch a tab on startup; supervisor doesn't
  # read NO_BROWSER but the variable is harmless).
  $action = "& '$GIT_BASH' -c `"PORT=$($svc.Port) NO_BROWSER=1 bash '$unixPath'`""

  $trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
  $actionObj = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-WindowStyle Hidden -Command `"$action`""

  # Always-on services (supervisor) get aggressive restart-on-failure to
  # approximate macOS KeepAlive=true. Bridges with RestartCount=0 will
  # exit cleanly on idle-shutdown and stay down until next trigger.
  if ($svc.AlwaysOn) {
    $settings = New-ScheduledTaskSettingsSet `
      -AllowStartIfOnBatteries `
      -DontStopIfGoingOnBatteries `
      -StartWhenAvailable `
      -RestartCount 999 `
      -RestartInterval (New-TimeSpan -Minutes 1) `
      -ExecutionTimeLimit (New-TimeSpan -Days 365)
  } else {
    $settings = New-ScheduledTaskSettingsSet `
      -AllowStartIfOnBatteries `
      -DontStopIfGoingOnBatteries `
      -StartWhenAvailable `
      -RestartCount 0 `
      -ExecutionTimeLimit (New-TimeSpan -Hours 24)
  }

  Register-ScheduledTask -TaskName $taskName `
    -Trigger $trigger `
    -Action $actionObj `
    -Settings $settings `
    -Force | Out-Null

  # Start it immediately (so user doesn't have to log out/in)
  Start-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

  $tag = if ($svc.AlwaysOn) { "always-on" } else { "idle-shutdown" }
  Write-Host "  [OK] $($svc.Name) registered (port $($svc.Port), $tag)"
}

# Copy the .bat to Desktop so users can find it without spelunking into
# their workspace folder. Equivalent to the macOS Desktop copy in setup.sh.
# Idempotent: re-running the script just overwrites.
$desktopBat = [Environment]::GetFolderPath("Desktop") + "\SearchAtlas Mission Control.bat"
# Start Bridges.bat now lives under mission-control/
$sourceBat = "$ToolkitPath\mission-control\Start Bridges.bat"
if (Test-Path $sourceBat) {
  Copy-Item -Path $sourceBat -Destination $desktopBat -Force -ErrorAction SilentlyContinue
  if (Test-Path $desktopBat) {
    Write-Host "  [OK] Restart helper on Desktop: SearchAtlas Mission Control.bat"
  }
}

Write-Host ""
Write-Host "  Mission Control is running."
Write-Host "  Supervisor: http://localhost:8764"
Write-Host "  Open welcome.html and click any wizard card to use them."
