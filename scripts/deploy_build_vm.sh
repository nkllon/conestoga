#!/bin/bash
set -e

# Usage: ./scripts/deploy_build_vm.sh <PROJECT_ID> <BUCKET_NAME> [ZONE]

PROJECT_ID=$1
BUCKET_NAME=$2
ZONE=${3:-us-central1-a}

if [ -z "$PROJECT_ID" ] || [ -z "$BUCKET_NAME" ]; then
    echo "Usage: $0 <PROJECT_ID> <BUCKET_NAME> [ZONE]"
    exit 1
fi

echo "🚀 Preparing Windows Build Environment..."

# 1. Zip Source
echo "📦 Zipping source code..."
zip -r source.zip . -x "*.git*" "*.venv*" "dist*" "build*" "node_modules*" "__pycache__*" "*.DS_Store"

# 2. Upload to GCS
echo "☁️ Uploading source to gs://$BUCKET_NAME/source.zip..."
gsutil cp source.zip gs://$BUCKET_NAME/source.zip

# 3. Create Startup Script
# This runs as System on boot.
cat <<EOF > startup_wrapper.ps1
# Download Source
gsutil cp gs://$BUCKET_NAME/source.zip C:\source.zip
Expand-Archive -Path C:\source.zip -DestinationPath C:\conestoga

# Download Build Script (we could upload it separately, but we'll cat it here for simplicity if it were small,
# but since I have it as a file, let's copy it).
# Actually, the zip contains scripts/windows_build.ps1! So we can just run it.

cd C:\conestoga
.\scripts\windows_build.ps1
EOF

# 4. Deploy VM
INSTANCE_NAME="conestoga-builder-$(date +%s)"
echo "🖥️ Creating VM $INSTANCE_NAME in $PROJECT_ID..."

gcloud compute instances create $INSTANCE_NAME \
    --project=$PROJECT_ID \
    --zone=$ZONE \
    --machine-type=e2-standard-4 \
    --image-family=windows-2022 \
    --image-project=windows-cloud \
    --boot-disk-size=50GB \
    --boot-disk-type=pd-ssd \
    --scopes=cloud-platform \
    --metadata=gcs-bucket=$BUCKET_NAME \
    --metadata-from-file=sysprep-specialize-script-ps1=startup_wrapper.ps1 \
    --preemptible

echo "⏳ Build started. VM will shut down automatically upon completion."
echo "   Monitor with: gcloud compute instances get-serial-port-output $INSTANCE_NAME --zone=$ZONE"
echo "   Artifact will appear at: gs://$BUCKET_NAME/builds/windows/Conestoga.exe"
