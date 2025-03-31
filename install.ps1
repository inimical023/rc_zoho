# PowerShell script to download and execute setup_integration.bat from GitHub

# Set execution policy to allow script execution
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force

# GitHub repository URL
$repoUrl = "https://raw.githubusercontent.com/inimical023/rc_zoho/main"

# Create a temporary directory
$tempDir = Join-Path $env:TEMP "rc_zoho_setup"
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null

# Download setup_integration.bat
$setupFile = Join-Path $tempDir "setup_integration.bat"
Write-Host "Downloading setup script..."
Invoke-WebRequest -Uri "$repoUrl/setup_integration.bat" -OutFile $setupFile

# Verify download
if (Test-Path $setupFile) {
    Write-Host "Setup script downloaded successfully."
    
    # Execute the batch file
    Write-Host "Starting setup process..."
    Start-Process -FilePath $setupFile -Wait -NoNewWindow
    
    # Clean up
    Remove-Item -Path $tempDir -Recurse -Force
    Write-Host "Setup completed successfully!"
} else {
    Write-Host "Failed to download setup script."
    exit 1
} 