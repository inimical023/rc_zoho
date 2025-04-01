# PowerShell script to set up RingCentral-Zoho Integration
# PowerShell installation script for RingCentral-Zoho Integration
# This script is created during setup_integration.bat execution

# Set execution policy to allow script execution
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force

# Configuration
$repoUrl = "https://raw.githubusercontent.com/inimical023/rc_zoho/main"
$requiredPythonVersion = "3.8"

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

Write-Log "Starting RingCentral-Zoho Integration Installation"
Write-Log "========================================"
Write-Log "Selected installation directory: $installDir"
Write-Log "Temp log file location: $tempLogFile"
Write-Log "Installation log file location: $installLogFile"

# Validate the installation directory
if (Test-Path $installDir) {
    Write-Log "`nWarning: Directory '$installDir' already exists." -Level "WARNING"
    Write-Log "Do you want to continue and potentially overwrite existing files? (Y/N)"
    $response = Read-Host
    if ($response -ne "Y") {
        Write-Log "Installation cancelled by user." -Level "WARNING"
        exit 1
    }
}

$files = @(
    "setup_integration.bat",
    "unified_admin.py",
    "setup_credentials.py",
    "secure_credentials.py",
    "requirements.txt",
    "launch_admin.bat",
    "accepted_calls.py",
    "missed_calls.py",
    "common.py",
    "README.md"
)

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

# Function to download a file
function Download-File {
    param (
        [string]$fileName
    )
    
    $url = "$repoUrl/$fileName"
    $outFile = Join-Path $installDir $fileName
    
    try {
        Write-Log "Downloading $fileName..." -NoNewline
        Invoke-WebRequest -Uri $url -OutFile $outFile
        Write-Log "Done" -Level "SUCCESS"
        return $true
    } catch {
        Write-Log "Failed" -Level "ERROR"
        Write-Log "Error downloading $fileName`: $_" -Level "ERROR"
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

# Download all required files
Write-Log "`nDownloading required files..."
$success = $true
foreach ($file in $files) {
    if (-not (Download-File $file)) {
        $success = $false
        break
    }
}

if (-not $success) {
    Write-Log "`nSetup failed. Please check your internet connection and try again." -Level "ERROR"
    Write-Log "Temp log file location: $tempLogFile" -Level "INFO"
    Write-Log "Installation log file location: $installLogFile" -Level "INFO"
    exit 1
}

# Run setup_integration.bat
Write-Log "`nStarting integration setup..."
try {
    $setupFile = Join-Path $installDir "setup_integration.bat"
    Push-Location $installDir
    Start-Process -FilePath $setupFile -Wait -NoNewWindow
    Pop-Location
    
    Write-Log "`nSetup completed successfully!" -Level "SUCCESS"
    Write-Log "Installation directory: $installDir" -Level "INFO"
    Write-Log "`nYou can now run the Unified Admin GUI by double-clicking 'launch_admin.bat' in the installation directory." -Level "INFO"
} catch {
    Write-Log "Error during setup: $_" -Level "ERROR"
    Write-Log "Temp log file location: $tempLogFile" -Level "INFO"
    Write-Log "Installation log file location: $installLogFile" -Level "INFO"
    exit 1
}

# Create desktop shortcut
try {
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\RingCentral-Zoho Admin.lnk")
    $Shortcut.TargetPath = Join-Path $installDir "launch_admin.bat"
    $Shortcut.WorkingDirectory = $installDir
    $Shortcut.Save()
    Write-Log "`nDesktop shortcut created successfully!" -Level "SUCCESS"
} catch {
    Write-Log "Warning: Could not create desktop shortcut: $_" -Level "WARNING"
}

# Keep window open
Write-Log "`nPress any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") 
Write-Log "Installation completed successfully" -Level "SUCCESS"
Write-Log "Temp log file location: $tempLogFile" -Level "INFO"
Write-Log "Installation log file location: $installLogFile" -Level "INFO"