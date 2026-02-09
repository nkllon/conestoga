# Download Source
gsutil cp gs://conestoga-build-artifacts-gen-lang/source.zip C:\source.zip
Expand-Archive -Path C:\source.zip -DestinationPath C:\conestoga

# Download Build Script (we could upload it separately, but we'll cat it here for simplicity if it were small,
# but since I have it as a file, let's copy it).
# Actually, the zip contains scripts/windows_build.ps1! So we can just run it.

cd C:\conestoga
.\scripts\windows_build.ps1
