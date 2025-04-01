# PowerShell script to set up RingCentral-Zoho Integration
# PowerShell installation script for RingCentral-Zoho Integration
# This script is created during setup_integration.bat execution

# Set execution policy to allow script execution
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
Write-Host "RingCentral-Zoho Integration Installation"
Write-Host "========================================"

# Configuration
$repoUrl = "https://raw.githubusercontent.com/inimical023/rc_zoho/main"
$requiredPythonVersion = "3.8"
$installDir = Join-Path $env:USERPROFILE "RingCentralZoho"
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
            Write-Host "Python $pythonVersion found." -ForegroundColor Green
            return $true
        } else {
            Write-Host "Python $requiredPythonVersion or higher is required. Found version $pythonVersion" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "Python is not installed or not in PATH." -ForegroundColor Red
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
        Write-Host "Downloading $fileName..." -NoNewline
        Invoke-WebRequest -Uri $url -OutFile $outFile
        Write-Host "Done" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "Failed" -ForegroundColor Red
        Write-Host "Error downloading $fileName`: $_" -ForegroundColor Red
        return $false
    }
}

# Main installation process
Write-Host "RingCentral-Zoho Integration Setup" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan

# Check Python installation
if (-not (Test-PythonInstallation)) {
    Write-Host "Please install Python $requiredPythonVersion or higher and add it to PATH." -ForegroundColor Yellow
    Write-Host "Download Python from: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

# Create installation directory
Write-Host "`nCreating installation directory..." -NoNewline
try {
    New-Item -ItemType Directory -Force -Path $installDir | Out-Null
    Write-Host "Done" -ForegroundColor Green
} catch {
    Write-Host "Failed" -ForegroundColor Red
    Write-Host "Error creating directory: $_" -ForegroundColor Red
    exit 1
}

# Create required subdirectories
@('logs', 'data') | ForEach-Object {
    $dir = Join-Path $installDir $_
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

# Download all required files
Write-Host "`nDownloading required files..."
$success = $true
foreach ($file in $files) {
    if (-not (Download-File $file)) {
        $success = $false
        break
    }
}

if (-not $success) {
    Write-Host "`nSetup failed. Please check your internet connection and try again." -ForegroundColor Red
    exit 1
}

# Run setup_integration.bat
Write-Host "`nStarting integration setup..."
try {
    $setupFile = Join-Path $installDir "setup_integration.bat"
    Push-Location $installDir
    Start-Process -FilePath $setupFile -Wait -NoNewWindow
    Pop-Location
    
    Write-Host "`nSetup completed successfully!" -ForegroundColor Green
    Write-Host "Installation directory: $installDir" -ForegroundColor Cyan
    Write-Host "`nYou can now run the Unified Admin GUI by double-clicking 'launch_admin.bat' in the installation directory." -ForegroundColor Cyan
} catch {
    Write-Host "Error during setup: $_" -ForegroundColor Red
    exit 1
}

# Create desktop shortcut
try {
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\RingCentral-Zoho Admin.lnk")
    $Shortcut.TargetPath = Join-Path $installDir "launch_admin.bat"
    $Shortcut.WorkingDirectory = $installDir
    $Shortcut.Save()
    Write-Host "`nDesktop shortcut created successfully!" -ForegroundColor Green
} catch {
    Write-Host "Warning: Could not create desktop shortcut: $_" -ForegroundColor Yellow
}

# Keep window open
Write-Host "`nPress any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") 
Write-Host "Installation completed successfully"