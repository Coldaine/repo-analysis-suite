# Windows Deployment Guide

## Prerequisites

### Required Software
- **Python 3.8+** - [Download](https://www.python.org/downloads/)
- **Git for Windows** - [Download](https://git-scm.com/download/win)
- **Gemini CLI** - Installed and configured
- **Jules CLI** - Installed with valid API key
- **Qwen CLI** - Installed and configured
- **Goose CLI** - Installed and configured

### Verify Installations

```powershell
# Check Python
python --version

# Check Git
git --version

# Check AI Tools
gemini --version
jules version
qwen --version
goose --version
```

## Installation Steps

### 1. Clone Repository

```powershell
# Navigate to your preferred directory
cd C:\Users\%USERNAME%

# Clone the repository
git clone https://github.com/yourusername/agent-council.git
cd agent-council
```

### 2. Set Up Python Environment

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```powershell
# Copy example environment file
copy .env.example .env

# Edit .env file with your API keys
notepad .env
```

Required environment variables:
```env
# API Keys
GEMINI_API_KEY=your_gemini_key_here
JULES_API_KEY=your_jules_key_here
QWEN_API_KEY=your_qwen_key_here
OPENAI_API_KEY=your_openai_key_here

# Paths
AGENT_COUNCIL_HOME=C:\Users\%USERNAME%\agent-council
AGENT_COUNCIL_DATA=C:\Users\%USERNAME%\agent-council\data
AGENT_COUNCIL_LOGS=C:\Users\%USERNAME%\agent-council\data\logs

# Configuration
AGENT_COUNCIL_ENV=production
AGENT_COUNCIL_DEBUG=false
```

### 4. Initialize the System

```powershell
# Run setup script
python scripts\setup.py

# Verify setup
python scripts\status.py
```

## Running Agent Council

### Manual Start

```powershell
# Activate virtual environment
.\venv\Scripts\activate

# Start orchestrator
python scripts\start.py
```

### PowerShell Script

Create `start-agent-council.ps1`:

```powershell
# Start Agent Council
$scriptPath = "C:\Users\$env:USERNAME\agent-council"
Set-Location $scriptPath

# Activate virtual environment
& ".\venv\Scripts\Activate.ps1"

# Set environment variables
$env:PYTHONPATH = $scriptPath

# Start orchestrator with logging
$logFile = ".\data\logs\orchestrator\$(Get-Date -Format 'yyyy-MM-dd').log"
python scripts\start.py 2>&1 | Tee-Object -FilePath $logFile

# Keep window open on error
if ($LASTEXITCODE -ne 0) {
    Write-Host "Agent Council encountered an error. Press any key to exit..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
```

### Batch Script

Create `start-agent-council.bat`:

```batch
@echo off
cd /d C:\Users\%USERNAME%\agent-council
call venv\Scripts\activate.bat
set PYTHONPATH=%cd%
python scripts\start.py
pause
```

## Windows Service Setup

### Using NSSM (Non-Sucking Service Manager)

1. Download NSSM: https://nssm.cc/download

2. Install as service:
```powershell
# Run as Administrator
nssm install AgentCouncil

# Configure in GUI:
# Path: C:\Python39\python.exe
# Startup directory: C:\Users\%USERNAME%\agent-council
# Arguments: scripts\start.py
```

3. Configure service:
```powershell
# Set to start automatically
nssm set AgentCouncil Start SERVICE_AUTO_START

# Set description
nssm set AgentCouncil Description "Agent Council AI Orchestration System"

# Set environment variables
nssm set AgentCouncil AppEnvironmentExtra GEMINI_API_KEY=your_key

# Start service
nssm start AgentCouncil
```

### Using Task Scheduler

1. Open Task Scheduler (`taskschd.msc`)

2. Create Basic Task:
   - Name: "Agent Council Orchestrator"
   - Trigger: "When computer starts"
   - Action: "Start a program"
   - Program: `C:\Python39\python.exe`
   - Arguments: `C:\Users\%USERNAME%\agent-council\scripts\start.py`
   - Start in: `C:\Users\%USERNAME%\agent-council`

3. Configure additional settings:
   - Run whether user is logged on or not
   - Run with highest privileges
   - Configure restart on failure

### PowerShell Scheduled Job

```powershell
# Create scheduled job
$trigger = New-JobTrigger -AtStartup
$options = New-ScheduledJobOption -RunElevated -RequireNetwork

Register-ScheduledJob -Name "AgentCouncil" `
    -Trigger $trigger `
    -ScheduledJobOption $options `
    -ScriptBlock {
        Set-Location "C:\Users\$env:USERNAME\agent-council"
        & ".\venv\Scripts\python.exe" "scripts\start.py"
    }
```

## Monitoring

### Check Status

```powershell
# Check if running
python scripts\status.py

# View recent logs
Get-Content .\data\logs\orchestrator\*.log -Tail 50

# Monitor in real-time
Get-Content .\data\logs\orchestrator\today.log -Wait
```

### PowerShell Monitoring Script

Create `monitor.ps1`:

```powershell
# Monitor Agent Council
param(
    [int]$RefreshSeconds = 5
)

while ($true) {
    Clear-Host
    Write-Host "=== Agent Council Status ===" -ForegroundColor Cyan
    Write-Host "Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`n"

    # Check process
    $process = Get-Process python -ErrorAction SilentlyContinue |
               Where-Object {$_.CommandLine -like "*agent-council*"}

    if ($process) {
        Write-Host "Status: RUNNING" -ForegroundColor Green
        Write-Host "PID: $($process.Id)"
        Write-Host "Memory: $([math]::Round($process.WS / 1MB, 2)) MB"
        Write-Host "CPU: $([math]::Round($process.CPU, 2)) seconds"
    } else {
        Write-Host "Status: STOPPED" -ForegroundColor Red
    }

    # Recent logs
    Write-Host "`n=== Recent Activity ===" -ForegroundColor Cyan
    Get-Content .\data\logs\orchestrator\*.log -Tail 10

    Start-Sleep -Seconds $RefreshSeconds
}
```

## Troubleshooting

### Common Issues

#### 1. Python Path Issues
```powershell
# Add Python to PATH
$env:Path += ";C:\Python39;C:\Python39\Scripts"

# Or use full paths
C:\Python39\python.exe scripts\start.py
```

#### 2. Permission Errors
```powershell
# Run PowerShell as Administrator
# Or grant permissions to data directory
icacls ".\data" /grant Users:F /T
```

#### 3. API Key Not Found
```powershell
# Set environment variables for session
$env:GEMINI_API_KEY = "your_key"

# Set permanently (requires admin)
[System.Environment]::SetEnvironmentVariable("GEMINI_API_KEY", "your_key", "User")
```

#### 4. Port Already in Use
```powershell
# Find process using port
netstat -ano | findstr :8080

# Kill process
taskkill /PID <process_id> /F
```

### Debug Mode

```powershell
# Enable debug logging
$env:AGENT_COUNCIL_DEBUG = "true"
python scripts\start.py --debug

# Verbose output
python scripts\start.py -vv
```

### Log Locations

```
C:\Users\%USERNAME%\agent-council\data\logs\
├── orchestrator\       # Main system logs
├── gemini\             # Gemini agent logs
├── jules\              # Jules agent logs
├── qwen\               # Qwen agent logs
├── goose\              # Goose agent logs
└── errors\             # Error logs
```

## Performance Optimization

### Windows Defender Exclusions

Add exclusions to reduce scanning overhead:

```powershell
# Run as Administrator
Add-MpPreference -ExclusionPath "C:\Users\$env:USERNAME\agent-council"
Add-MpPreference -ExclusionProcess "python.exe"
```

### Power Settings

Prevent sleep/hibernation:
```powershell
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
```

### Resource Limits

Set process priority:
```powershell
# In start script
$process = Get-Process python | Where {$_.CommandLine -like "*agent-council*"}
$process.PriorityClass = "BelowNormal"
```

## Backup and Recovery

### Backup Script

Create `backup.ps1`:

```powershell
# Backup Agent Council data
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupDir = ".\backups\backup-$timestamp"

New-Item -ItemType Directory -Path $backupDir -Force

# Backup state and logs
Copy-Item -Path ".\data\state" -Destination "$backupDir\state" -Recurse
Copy-Item -Path ".\data\logs" -Destination "$backupDir\logs" -Recurse
Copy-Item -Path ".\.env" -Destination "$backupDir\.env"

# Compress
Compress-Archive -Path $backupDir -DestinationPath "$backupDir.zip"
Remove-Item -Path $backupDir -Recurse -Force

Write-Host "Backup created: $backupDir.zip"
```

### Scheduled Backup

```powershell
# Schedule daily backup
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" `
    -Argument "-File C:\Users\$env:USERNAME\agent-council\backup.ps1"

$trigger = New-ScheduledTaskTrigger -Daily -At 3AM

Register-ScheduledTask -TaskName "AgentCouncilBackup" `
    -Action $action -Trigger $trigger
```

## Security Considerations

### File Permissions

```powershell
# Restrict access to sensitive files
icacls ".\.env" /inheritance:r /grant:r "$env:USERNAME:(R)"
icacls ".\data\state" /inheritance:r /grant:r "$env:USERNAME:(F)"
```

### Credential Storage

Use Windows Credential Manager:
```powershell
# Store credentials securely
cmdkey /add:AgentCouncil /user:api /pass:your_api_key

# Retrieve in script
$cred = Get-StoredCredential -Target "AgentCouncil"
```

## Integration with Windows Terminal

### Custom Profile

Add to Windows Terminal settings.json:

```json
{
    "name": "Agent Council",
    "commandline": "powershell.exe -NoExit -Command \"cd C:\\Users\\%USERNAME%\\agent-council; .\\venv\\Scripts\\Activate.ps1\"",
    "startingDirectory": "C:\\Users\\%USERNAME%\\agent-council",
    "icon": "🤖",
    "colorScheme": "Campbell Powershell"
}
```

## Next Steps

1. **Test the installation**:
   ```powershell
   python scripts\test_agents.py
   ```

2. **Configure agents** in `config\agents.yaml`

3. **Customize prompts** in `config\prompts\`

4. **Set up monitoring** dashboard

5. **Configure backups** for production use

For Linux deployment instructions, see [linux-setup.md](linux-setup.md).