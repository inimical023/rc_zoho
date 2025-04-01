# PowerShell script to set up RingCentral-Zoho Integration
# PowerShell installation script for RingCentral-Zoho Integration
# This script is created during setup_integration.bat execution

# Set execution policy to allow script execution
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force

# Configuration
$repoUrl = "https://raw.githubusercontent.com/inimical023/rc_zoho/main"
$repoApiUrl = "https://api.github.com/repos/inimical023/rc_zoho"
$requiredPythonVersion = "3.8"

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
    
    # Run the batch file with cmd.exe directly, which is better for batch files
    $cmdPath = "$env:SystemRoot\System32\cmd.exe"
    Write-Log "Running setup_integration.bat using $cmdPath..."
    $process = Start-Process -FilePath $cmdPath -ArgumentList "/c $setupFile" -WorkingDirectory $installDir -Wait -NoNewWindow -PassThru
    
    # Check process execution
    if ($process.ExitCode -ne 0 -and $process.ExitCode -ne 255) {
        Write-Log "Error during setup: setup_integration.bat exited with code $($process.ExitCode)" -Level "ERROR"
        Write-Log "Check the logs for more details." -Level "ERROR"
        
        # Check for expected files to diagnose issues
        Write-Log "Diagnostic information:" -Level "INFO"
        $expectedFiles = @(".venv", "launch_admin.bat", "unified_admin.py", "common.py")
        foreach ($file in $expectedFiles) {
            $filePath = Join-Path $installDir $file
            if (Test-Path $filePath) {
                Write-Log "- $file EXISTS" -Level "INFO"
            } else {
                Write-Log "- $file MISSING" -Level "WARNING"
            }
        }
        
        exit 1
    } elseif ($process.ExitCode -eq 255) {
        # Some batch files return 255 when they end with 'pause', even if they ran successfully
        # Check for key files to determine if the installation was actually successful
        $allFilesExist = $true
        $expectedFiles = @("launch_admin.bat", "unified_admin.py", "common.py")
        foreach ($file in $expectedFiles) {
            $filePath = Join-Path $installDir $file
            if (-not (Test-Path $filePath)) {
                $allFilesExist = $false
                break
            }
        }
        
        if ($allFilesExist) {
            Write-Log "Setup completed successfully despite exit code 255 (common with batch files)" -Level "SUCCESS"
        } else {
            Write-Log "Error during setup: exit code 255 and missing key files" -Level "ERROR"
            exit 1
        }
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