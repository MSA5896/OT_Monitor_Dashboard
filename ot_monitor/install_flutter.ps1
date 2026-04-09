# install_flutter.ps1
# Custom PowerShell script to reliably download and extract the Flutter SDK using pure .NET classes
# This bypasses the memory limits and alias issues of Invoke-WebRequest and Expand-Archive.

$ErrorActionPreference = "Stop"

$flutterVersion = "3.29.1"
$url = "https://storage.googleapis.com/flutter_infra_release/releases/stable/windows/flutter_windows_$flutterVersion-stable.zip"
$zipPath = "$HOME\flutter_sdk.zip"
$extractPath = "$HOME"

Write-Host "1. Downloading Flutter SDK $flutterVersion..." -ForegroundColor Cyan
try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $webClient = New-Object System.Net.WebClient
    $webClient.DownloadFile($url, $zipPath)
    Write-Host "✓ Download complete." -ForegroundColor Green
} catch {
    Write-Host "✗ Download failed: $_" -ForegroundColor Red
    exit 1
}

Write-Host "`n2. Extracting Flutter SDK (this may take a few minutes)..." -ForegroundColor Cyan
try {
    Add-Type -AssemblyName System.IO.Compression.FileSystem

    # If the flutter directory already exists, we should remove it first or extraction will fail
    $targetDir = Join-Path $extractPath "flutter"
    if (Test-Path $targetDir) {
        Write-Host "Removing existing flutter directory..." -ForegroundColor Yellow
        Remove-Item -Path $targetDir -Recurse -Force
    }

    [System.IO.Compression.ZipFile]::ExtractToDirectory($zipPath, $extractPath)
    Write-Host "✓ Extraction complete." -ForegroundColor Green
} catch {
    Write-Host "✗ Extraction failed: $_" -ForegroundColor Red
    exit 1
}

Write-Host "`n3. Adding Flutter to System PATH..." -ForegroundColor Cyan
try {
    $flutterBin = "$HOME\flutter\bin"
    
    # Check if it's already in the User PATH
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($userPath -notmatch [regex]::Escape($flutterBin)) {
        $newPath = $userPath + ";$flutterBin"
        [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
        Write-Host "✓ Added $flutterBin to User PATH." -ForegroundColor Green
    } else {
        Write-Host "✓ Flutter is already in the User PATH." -ForegroundColor Green
    }
} catch {
    Write-Host "✗ Failed to update PATH: $_" -ForegroundColor Red
}

Write-Host "`n4. Cleaning up zip file..." -ForegroundColor Cyan
Remove-Item -Path $zipPath -Force -ErrorAction SilentlyContinue

Write-Host "`n========================================================" -ForegroundColor Magenta
Write-Host "Flutter Installation Complete!" -ForegroundColor Green
Write-Host "IMPORTANT: You must CLOSE this PowerShell window and open a NEW ONE" -ForegroundColor Yellow
Write-Host "for the PATH changes to take effect, then run: flutter doctor" -ForegroundColor Yellow
Write-Host "========================================================" -ForegroundColor Magenta
