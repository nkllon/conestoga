$ErrorActionPreference = "Stop"

Write-Host "Starting Conestoga Windows Build..."
Write-Host "User: $env:USERNAME"
Write-Host "UserProfile: $env:USERPROFILE"

# 1. Install dependencies
Write-Host "Installing uv..."
try {
    # Install uv using the official script, but explicitly pointing to a writable location if needed
    # Standard install should work for LocalSystem but let's be explicit
    $env:UV_INSTALL_DIR = "C:\ProgramData\uv"
    New-Item -ItemType Directory -Force -Path $env:UV_INSTALL_DIR | Out-Null
    
    # Download and extract manually to avoid shell integration issues
    Invoke-WebRequest -Uri "https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip" -OutFile "uv.zip"
    Expand-Archive -Path "uv.zip" -DestinationPath $env:UV_INSTALL_DIR -Force
    
    # Find the executable (it might be in a subdir depending on zip structure)
    $uvExe = Get-ChildItem -Path $env:UV_INSTALL_DIR -Recurse -Filter "uv.exe" | Select-Object -First 1 -ExpandProperty FullName
    
    if (-not $uvExe) {
        throw "Could not find uv.exe after extraction"
    }
    
    Write-Host "uv installed at $uvExe"
} catch {
    Write-Error "Failed to install uv: $_"
    exit 1
}

# Helper to run uv
function Run-Uv {
    param([Parameter(ValueFromRemainingArguments=$true)]$Args)
    & $uvExe $Args
    if ($LASTEXITCODE -ne 0) { throw "uv command failed with code $LASTEXITCODE" }
}

# 2. Setup environment
Write-Host "Installing Python 3.12..."
Run-Uv python install 3.12

# 3. Build
Write-Host "Syncing dependencies..."
Set-Location C:\conestoga
Run-Uv sync --all-extras

Write-Host "Building executable..."
Run-Uv run pyinstaller --noconfirm --onefile --windowed --name "Conestoga" `
    --hidden-import="pygame" `
    --hidden-import="google.genai" `
    --hidden-import="dotenv" `
    src/conestoga/main.py

# 4. Upload Artifact
$bucket = (Invoke-RestMethod "http://metadata.google.internal/computeMetadata/v1/instance/attributes/gcs-bucket" -Headers @{"Metadata-Flavor"="Google"})
Write-Host "Uploading artifact to $bucket..."

# Use built-in gsutil if available (usually is on GCP images)
if (Get-Command gsutil -ErrorAction SilentlyContinue) {
    gsutil cp dist\Conestoga.exe "gs://$bucket/builds/windows/Conestoga.exe"
} else {
    Write-Host "gsutil not found. This is unexpected on GCP images. Trying python fallback..."
    # Ensure google-cloud-storage is installed (it should be from sync)
    $uploadScript = @"
import os
from google.cloud import storage

bucket_name = "$bucket"
source_file_name = "dist\\Conestoga.exe"
destination_blob_name = "builds/windows/Conestoga.exe"

print(f"Uploading {source_file_name} to {destination_blob_name} in {bucket_name}...")
storage_client = storage.Client()
bucket = storage_client.bucket(bucket_name)
blob = bucket.blob(destination_blob_name)

blob.upload_from_filename(source_file_name)
print("Upload complete.")
"@
    Set-Content upload.py $uploadScript
    Run-Uv run python upload.py
}

Write-Host "Build and Upload Complete!"

# 5. Shutdown
Stop-Computer -Force
