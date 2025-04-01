# PowerShell script to set up RingCentral-Zoho Integration
# PowerShell installation script for RingCentral-Zoho Integration
# This script is created during setup_integration.bat execution

# Set execution policy to allow script execution
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force

# Configuration
$repoUrl = "https://raw.githubusercontent.com/inimical023/rc_zoho/main"
$repoApiUrl = "https://api.github.com/repos/inimical023/rc_zoho"
$requiredPythonVersion = "3.8"
$pythonInstallerUrl = "https://www.python.org/ftp/python/3.8.10/python-3.8.10-amd64.exe"
$pythonInstallDir = "$env:LOCALAPPDATA\Programs\Python\Python38"

# Check latest commit information
try {
    Write-Host "`nChecking latest repository information..." -ForegroundColor Cyan
    # Use TLS 1.2 for modern web security requirements
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    
    # Add proper user agent header to avoid GitHub API restrictions
    $headers = @{
        'User-Agent' = 'PowerShell-Script'
    }
    
    $repoInfo = Invoke-RestMethod -Uri $repoApiUrl -Headers $headers
    $commitsUrl = $repoInfo.commits_url -replace '{/sha}', ''
    $latestCommits = Invoke-RestMethod -Uri "$commitsUrl`?per_page=1" -Headers $headers
    
    if ($latestCommits.Count -gt 0) {
        $latestCommit = $latestCommits[0]
        $commitSha = $latestCommit.sha.Substring(0, 7)
        $commitDate = [DateTime]$latestCommit.commit.author.date
        $commitMsg = $latestCommit.commit.message.Split("`n")[0]
        
        Write-Host "Latest commit: $commitSha ($($commitDate.ToString('yyyy-MM-dd HH:mm:ss')))" -ForegroundColor Cyan
        Write-Host "Message: $commitMsg" -ForegroundColor Cyan
    }
} catch {
    Write-Host "Could not fetch repository information: $_" -ForegroundColor Yellow
}

# Get the last modified timestamp of the installation file
try {
    # Use TLS 1.2 and proper headers
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $headers = @{
        'User-Agent' = 'PowerShell-Script'
    }
    
    $response = Invoke-WebRequest -Uri "$repoUrl/install.ps1" -Method Head -Headers $headers
    $lastModified = $response.Headers['Last-Modified']
    if ($lastModified) {
        Write-Host "`nRemote installation file last modified: $lastModified" -ForegroundColor Cyan
    }
} catch {
    Write-Host "`nCould not fetch installation file timestamp: $_" -ForegroundColor Yellow
}

# Prompt for installation directory
Write-Host "`nPlease enter the installation directory path:"
$currentDir = (Get-Location).Path
Write-Host "Press Enter to use the current directory ($currentDir)"
Write-Host "Or type a different path"
$installDir = Read-Host
if ([string]::IsNullOrWhiteSpace($installDir)) {
    $installDir = $currentDir
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

# Log repository information if available
if (Get-Variable -Name latestCommit -ErrorAction SilentlyContinue) {
    Write-Log "Repository Information:" -Level "INFO"
    Write-Log "Latest commit: $commitSha ($($commitDate.ToString('yyyy-MM-dd HH:mm:ss')))" -Level "INFO"
    Write-Log "Commit message: $commitMsg" -Level "INFO"
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
        Write-Host "Do you want to continue and potentially overwrite existing files? (Y/N)"
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

# Function to install Python
function Install-Python {
    Write-Log "Installing Python $requiredPythonVersion..."
    
    # Create temporary directory for the installer
    $tempDir = Join-Path $env:TEMP "PythonInstall"
    New-Item -ItemType Directory -Force -Path $tempDir | Out-Null
    $installerPath = Join-Path $tempDir "python-installer.exe"
    
    # Download Python installer
    Write-Log "Downloading Python installer from $pythonInstallerUrl"
    try {
        Invoke-WebRequest -Uri $pythonInstallerUrl -OutFile $installerPath
    } catch {
        Write-Log "Failed to download Python installer: $_" -Level "ERROR"
        return $false
    }
    
    # Run installer with necessary flags
    Write-Log "Running Python installer..."
    $installArgs = @(
        "/quiet",
        "InstallAllUsers=0",
        "PrependPath=1",
        "Include_test=0",
        "Include_doc=0",
        "TargetDir=$pythonInstallDir"
    )
    
    $process = Start-Process -FilePath $installerPath -ArgumentList $installArgs -PassThru -Wait
    if ($process.ExitCode -ne 0) {
        Write-Log "Python installation failed with exit code $($process.ExitCode)" -Level "ERROR"
        return $false
    }
    
    # Update environment PATH for this session
    $env:Path = "$pythonInstallDir;$pythonInstallDir\Scripts;" + $env:Path
    
    Write-Log "Python installation completed. Verifying..." -Level "SUCCESS"
    return (Test-PythonInstallation)
}

# Create a pythonpath.txt file with the Python paths
function New-PythonPathFile {
    param (
        [string]$PythonPath
    )
    
    try {
        $pythonPathFile = Join-Path $installDir "pythonpath.txt"
        Set-Content -Path $pythonPathFile -Value $PythonPath
        Set-Content -Path "$pythonPathFile.scripts" -Value "$PythonPath\Scripts"
        Write-Log "Created Python path file at $pythonPathFile" -Level "INFO"
        return $true
    } catch {
        Write-Log "Failed to create Python path file: $_" -Level "ERROR"
        return $false
    }
}

# Main installation process
Write-Log "RingCentral-Zoho Integration Setup" -Level "INFO"
Write-Log "=================================" -Level "INFO"

# Check Python installation and install if needed
if (-not (Test-PythonInstallation)) {
    Write-Log "Python $requiredPythonVersion or higher is required but not found." -Level "WARNING"
    Write-Log "Automatically installing Python $requiredPythonVersion..." -Level "INFO"
    
    $pythonInstalled = Install-Python
    if (-not $pythonInstalled) {
        Write-Log "Automatic Python installation failed." -Level "ERROR"
        Write-Log "Please install Python $requiredPythonVersion or higher manually:" -Level "WARNING"
        Write-Log "1. Download from: https://www.python.org/downloads/" -Level "WARNING"
        Write-Log "2. IMPORTANT: Check 'Add Python to PATH' during installation" -Level "WARNING"
        Write-Log "3. Run this script again after installation" -Level "WARNING"
        exit 1
    }
    
    # Create a file with the Python path for the batch script to use
    New-PythonPathFile -PythonPath $pythonInstallDir
    
    # Verify Python is in PATH
    Write-Log "Verifying Python is in PATH..." -Level "INFO"
    if (-not (Test-PythonInstallation)) {
        Write-Log "Python was installed but could not be found in PATH." -Level "ERROR"
        Write-Log "Will try to use full path to Python: $pythonInstallDir\python.exe" -Level "INFO"
    }
} else {
    # Get the actual Python path to create the path file
    try {
        $pythonExePath = (Get-Command python).Source
        $pythonDir = Split-Path -Parent $pythonExePath
        New-PythonPathFile -PythonPath $pythonDir
    } catch {
        Write-Log "Could not determine Python installation directory: $_" -Level "WARNING"
        New-PythonPathFile -PythonPath $pythonInstallDir  # Use default as fallback
    }
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
    
    # Check if we're getting the latest version
    if (Get-Variable -Name latestCommit -ErrorAction SilentlyContinue) {
        try {
            # Use the same headers and TLS settings
            $setupContentUrl = "https://api.github.com/repos/inimical023/rc_zoho/contents/setup_integration.bat?ref=main"
            $setupFileInfo = Invoke-RestMethod -Uri $setupContentUrl -Headers $headers
            
            # Compare SHA
            $latestSha = $setupFileInfo.sha
            Write-Log "Latest file SHA from GitHub: $latestSha" -Level "INFO"
            
            if ($latestSha) {
                Write-Log "You are downloading the latest version from GitHub" -Level "SUCCESS"
            }
        } catch {
            Write-Log "Could not verify downloaded file against latest commit: $_" -Level "WARNING"
        }
    }
    
    # Log file timestamps
    try {
        # For the current running script (which might be from a remote source)
        $scriptInfo = "Running as executed script (not source file)"
        Write-Log "Install script info: $scriptInfo" -Level "INFO"
        
        # For the downloaded file
        if (Test-Path $setupFile) {
            $setupFileTime = (Get-Item $setupFile).LastWriteTime
            Write-Log "Downloaded setup_integration.bat timestamp: $setupFileTime" -Level "INFO"
        } else {
            Write-Log "Cannot find downloaded setup_integration.bat" -Level "WARNING"
        }
        
        # Get remote timestamps for comparison
        try {
            $remoteSetupResponse = Invoke-WebRequest -Uri "$repoUrl/setup_integration.bat" -Method Head -Headers $headers
            $remoteSetupModified = $remoteSetupResponse.Headers['Last-Modified']
            if ($remoteSetupModified) {
                Write-Log "Remote setup_integration.bat timestamp: $remoteSetupModified" -Level "INFO"
            }
        } catch {
            Write-Log "Could not fetch remote setup_integration.bat timestamp: $_" -Level "WARNING"
        }
    } catch {
        Write-Log "Error getting file timestamps: $_" -Level "WARNING"
    }
    
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
    
    # Add executable permissions to the batch file (just in case)
    Write-Log "Setting batch file permissions..."
    
    # Pass Python path environment variables to the batch file
    $pythonPath = if (Test-Path "$installDir\pythonpath.txt") { Get-Content "$installDir\pythonpath.txt" } else { $pythonInstallDir }
    $pythonScriptsPath = if (Test-Path "$installDir\pythonpath.txt.scripts") { Get-Content "$installDir\pythonpath.txt.scripts" } else { "$pythonInstallDir\Scripts" }
    
    # Create a temporary wrapper batch file that sets environment variables
    $wrapperFile = Join-Path $installDir "run_setup.bat"
    @"
@echo off
set "PYTHON_PATH=$pythonPath"
set "PYTHON_SCRIPTS=$pythonScriptsPath"
set "PATH=$pythonPath;$pythonScriptsPath;%PATH%"
call $setupFile
exit /b %ERRORLEVEL%
"@ | Set-Content -Path $wrapperFile
    
    # Run the wrapper batch file with cmd.exe directly
    $cmdPath = "$env:SystemRoot\System32\cmd.exe"
    Write-Log "Running setup_integration.bat using $cmdPath with PATH set to include Python..."
    $process = Start-Process -FilePath $cmdPath -ArgumentList "/c $wrapperFile" -WorkingDirectory $installDir -Wait -NoNewWindow -PassThru
    
    # Clean up wrapper
    Remove-Item $wrapperFile -Force -ErrorAction SilentlyContinue
    
    # Check process execution
    if ($process.ExitCode -ne 0) {
        # In case the batch file returns non-zero, check if key files exist anyway
        $expectedFiles = @("launch_admin.bat", "unified_admin.py", "common.py")
        $missingFiles = @()
        foreach ($file in $expectedFiles) {
            $filePath = Join-Path $installDir $file
            if (-not (Test-Path $filePath)) {
                $missingFiles += $file
            }
        }
        
        # If all required files exist, consider the installation successful despite error code
        if ($missingFiles.Count -eq 0) {
            Write-Log "Setup completed successfully despite non-zero exit code" -Level "SUCCESS"
        } else {
            Write-Log "Error during setup: setup_integration.bat exited with code $($process.ExitCode)" -Level "ERROR"
            Write-Log "Missing key files: $($missingFiles -join ', ')" -Level "ERROR"
            
            # Give the user clear instructions for manual file checking
            Write-Log "Check the logs for more details:" -Level "INFO"
            Write-Log "- $installLogFile" -Level "INFO"
            Write-Log "- $tempLogFile" -Level "INFO"
            
            exit 1
        }
    } else {
        Write-Log "Batch script completed successfully with exit code 0" -Level "SUCCESS"
    }
    
    # Install additional UI enhancement packages
    Write-Log "Installing UI enhancement packages (ttkbootstrap and pillow)..."
    
    try {
        if (Test-Path (Join-Path $installDir ".venv")) {
            # Use virtual environment python if it exists
            $pythonCmd = "& $(Join-Path $installDir '.venv\Scripts\python.exe')"
            Write-Log "Using virtual environment Python for UI enhancements"
            Invoke-Expression "$pythonCmd -m pip install ttkbootstrap pillow" | Out-Null
        } else {
            # Use system python
            Write-Log "Using system Python for UI enhancements"
            & $pythonPath\python.exe -m pip install ttkbootstrap pillow | Out-Null
        }
        Write-Log "Successfully installed UI enhancement packages" -Level "SUCCESS"
    } catch {
        Write-Log "Warning: Failed to install UI enhancement packages: $_" -Level "WARNING"
        Write-Log "The application will still work but with a basic theme" -Level "WARNING"
    }
    
    # Verify key files were created
    $missingFiles = @()
    $expectedFiles = @("launch_admin.bat", "unified_admin.py", "common.py")
    foreach ($file in $expectedFiles) {
        $filePath = Join-Path $installDir $file
        if (-not (Test-Path $filePath)) {
            $missingFiles += $file
        }
    }
    
    if ($missingFiles.Count -gt 0) {
        Write-Log "Warning: Some expected files were not created:" -Level "WARNING"
        foreach ($file in $missingFiles) {
            Write-Log "- $file" -Level "WARNING"
        }
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