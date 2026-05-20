# Register the Mission Control bridges as scheduled tasks that run at user login.
# Equivalent to macOS LaunchAgents with RunAtLoad=true, KeepAlive=false.
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

$bridges = @(
  @{ Name = "command-center";  Port = 8765 },
  @{ Name = "website-build";   Port = 8766 },
  @{ Name = "website-rebuild"; Port = 8767 }
)

foreach ($bridge in $bridges) {
  $taskName = "SearchAtlasAMM-$($bridge.Name)"
  $runSh = "$ToolkitPath\tools\$($bridge.Name)\run.sh"

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

  # Create the task. Trigger=AtLogOn, runs as the current user.
  # Environment: NO_BROWSER=1 (skip browser open), PORT=<port>
  $action = "& '$GIT_BASH' -c `"PORT=$($bridge.Port) NO_BROWSER=1 bash '$unixPath'`""

  $trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
  $actionObj = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-WindowStyle Hidden -Command `"$action`""
  $settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 0 `
    -ExecutionTimeLimit (New-TimeSpan -Hours 24)

  Register-ScheduledTask -TaskName $taskName `
    -Trigger $trigger `
    -Action $actionObj `
    -Settings $settings `
    -Force | Out-Null

  # Start it immediately (so user doesn't have to log out/in)
  Start-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

  Write-Host "  [OK] $($bridge.Name) bridge registered (port $($bridge.Port))"
}

# Copy the .bat to Desktop so users can find it without spelunking into
# their workspace folder. Equivalent to the macOS Desktop copy in setup.sh.
# Idempotent: re-running the script just overwrites.
$desktopBat = [Environment]::GetFolderPath("Desktop") + "\SearchAtlas Mission Control.bat"
$sourceBat = "$ToolkitPath\Start Bridges.bat"
if (Test-Path $sourceBat) {
  Copy-Item -Path $sourceBat -Destination $desktopBat -Force -ErrorAction SilentlyContinue
  if (Test-Path $desktopBat) {
    Write-Host "  [OK] Restart helper on Desktop: SearchAtlas Mission Control.bat"
  }
}

Write-Host ""
Write-Host "  Mission Control bridges are running."
Write-Host "  Open welcome.html and click any wizard card to use them."
