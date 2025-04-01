# PowerShell script to set up RingCentral-Zoho Integration
# PowerShell installation script for RingCentral-Zoho Integration
# This script is created during setup_integration.bat execution

# Set execution policy to allow script execution
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force

# Configuration
$repoUrl = "https://raw.githubusercontent.com/inimical023/rc_zoho/main"
$requiredPythonVersion = "3.8"

# Get the last modified timestamp of the installation file
try {
    $response = Invoke-WebRequest -Uri "$repoUrl/install.ps1" -Method Head
    $lastModified = $response.Headers['Last-Modified']
    if ($lastModified) {
        Write-Host "`nInstallation file last modified: $lastModified" -ForegroundColor Cyan
    }
} catch {
    Write-Host "`nCould not fetch installation file timestamp: $_" -ForegroundColor Yellow
}

# Prompt for installation directory
Write-Host "`nPlease enter the installation directory path:"
Write-Host "Press Enter to use the default path ($env:USERPROFILE\RingCentralZoho)"
$installDir = Read-Host
if ([string]::IsNullOrWhiteSpace($installDir)) {
    $installDir = Join-Path $env:USERPROFILE "RingCentralZoho"
}

# Create installation directory and logs folder first
try {
    New-Item -ItemType Directory -Force -Path $installDir | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $installDir "logs") | Out-Null
} catch {
    Write-Host "Error creating directories: $_" -ForegroundColor Red
    exit 1
}

# Setup logging in both temp and installation directories
$tempLogDir = Join-Path $env:TEMP "RingCentralZoho_Install"
New-Item -ItemType Directory -Force -Path $tempLogDir | Out-Null
$tempLogFile = Join-Path $tempLogDir "install_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
$installLogFile = Join-Path $installDir "logs\installation_log_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

# Function to capture and log all output
function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    
    # Write to both log files
    Add-Content -Path $tempLogFile -Value $logMessage
    Add-Content -Path $installLogFile -Value $logMessage
    
    # Display in console with appropriate color
    switch ($Level) {
        "ERROR" { Write-Host $Message -ForegroundColor Red }
        "WARNING" { Write-Host $Message -ForegroundColor Yellow }
        "SUCCESS" { Write-Host $Message -ForegroundColor Green }
        default { Write-Host $Message }
    }
}

# Function to capture and log command output
function Invoke-CommandWithLogging {
    param(
        [string]$Command,
        [string]$Description
    )
    Write-Log "Starting: $Description"
    $output = & $Command 2>&1
    $output | ForEach-Object {
        Write-Log $_ -Level "INFO"
    }
    return $LASTEXITCODE
}

Write-Log "Starting RingCentral-Zoho Integration Installation"
Write-Log "========================================"
Write-Log "Selected installation directory: $installDir"
Write-Log "Temp log file location: $tempLogFile"
Write-Log "Installation log file location: $installLogFile"

# Validate the installation directory
$dirExists = Test-Path $installDir
$dirEmpty = $false
if ($dirExists) {
    $dirEmpty = -not (Get-ChildItem -Path $installDir -Force | Where-Object { $_.Name -notin @('logs') })
    if (-not $dirEmpty) {
        Write-Log "`nWarning: Directory '$installDir' exists and contains files." -Level "WARNING"
        Write-Log "Do you want to continue and potentially overwrite existing files? (Y/N)"
        $response = Read-Host
        if ($response -ne "Y") {
            Write-Log "Installation cancelled by user." -Level "WARNING"
            exit 1
        }
    } else {
        Write-Log "Directory exists but is empty, proceeding with installation..." -Level "INFO"
    }
}

# Function to check Python installation
function Test-PythonInstallation {
    try {
        $pythonVersion = python -c "import sys; print('.'.join(map(str, sys.version_info[:2])))"
        $pythonVersion = [version]$pythonVersion
        $requiredVersion = [version]$requiredPythonVersion
        
        if ($pythonVersion -ge $requiredVersion) {
            Write-Log "Python $pythonVersion found." -Level "SUCCESS"
            return $true
        } else {
            Write-Log "Python $requiredPythonVersion or higher is required. Found version $pythonVersion" -Level "ERROR"
            return $false
        }
    } catch {
        Write-Log "Python is not installed or not in PATH: $_" -Level "ERROR"
        return $false
    }
}

# Main installation process
Write-Log "RingCentral-Zoho Integration Setup" -Level "INFO"
Write-Log "=================================" -Level "INFO"

# Check Python installation
if (-not (Test-PythonInstallation)) {
    Write-Log "Please install Python $requiredPythonVersion or higher and add it to PATH." -Level "WARNING"
    Write-Log "Download Python from: https://www.python.org/downloads/" -Level "WARNING"
    exit 1
}

# Create installation directory
Write-Log "`nCreating installation directory..." -NoNewline
try {
    New-Item -ItemType Directory -Force -Path $installDir | Out-Null
    Write-Log "Done" -Level "SUCCESS"
} catch {
    Write-Log "Failed" -Level "ERROR"
    Write-Log "Error creating directory: $_" -Level "ERROR"
    exit 1
}

# Create required subdirectories
@('logs', 'data') | ForEach-Object {
    $dir = Join-Path $installDir $_
    try {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
    } catch {
        Write-Log "Error creating subdirectory $_`: $_" -Level "ERROR"
    }
}

# Download setup_integration.bat first
Write-Log "`nDownloading setup_integration.bat..."
try {
    $setupFile = Join-Path $installDir "setup_integration.bat"
    Invoke-WebRequest -Uri "$repoUrl/setup_integration.bat" -OutFile $setupFile
    Write-Log "Downloaded setup_integration.bat successfully" -Level "SUCCESS"
} catch {
    Write-Log "Failed to download setup_integration.bat: $_" -Level "ERROR"
    exit 1
}

# Run setup_integration.bat
Write-Log "`nStarting integration setup..."
try {
    Push-Location $installDir
    $setupFile = Join-Path $installDir "setup_integration.bat"
    if (-not (Test-Path $setupFile)) {
        Write-Log "Error: setup_integration.bat not found at $setupFile" -Level "ERROR"
        exit 1
    }
    
    # Run the batch file with proper error handling
    $process = Start-Process -FilePath $setupFile -Wait -NoNewWindow -PassThru
    if ($process.ExitCode -ne 0) {
        Write-Log "Error during setup: setup_integration.bat exited with code $($process.ExitCode)" -Level "ERROR"
        Write-Log "Check the logs for more details." -Level "ERROR"
        exit 1
    }
    
    Write-Log "`nSetup completed successfully!" -Level "SUCCESS"
    Write-Log "Installation directory: $installDir" -Level "INFO"
    Write-Log "`nYou can now run the Unified Admin GUI by double-clicking 'launch_admin.bat' in the installation directory." -Level "INFO"
} catch {
    Write-Log "Error during setup: $_" -Level "ERROR"
    Write-Log "Temp log file location: $tempLogFile" -Level "INFO"
    Write-Log "Installation log file location: $installLogFile" -Level "INFO"
    exit 1
} finally {
    Pop-Location
}

# Keep window open
Write-Log "`nPress any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") 
Write-Log "Installation completed successfully" -Level "SUCCESS"
Write-Log "Temp log file location: $tempLogFile" -Level "INFO"
Write-Log "Installation log file location: $installLogFile" -Level "INFO"