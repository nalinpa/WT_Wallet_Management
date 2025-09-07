# Debug BigQuery Deployment Script - Helps identify and fix deployment issues
param(
    [string]$ProjectId = "crypto-tracker-cloudrun",
    [string]$Region = "asia-southeast1",
    [string]$ServiceName = "wallet-api-bigquery"
)

Write-Host "🔍 Debugging BigQuery Deployment Issues..." -ForegroundColor Cyan

# Configuration
if (-not $ProjectId) {
    $ProjectId = Read-Host "Enter your Google Cloud Project ID"
}

Write-Host "Using Project: $ProjectId" -ForegroundColor Green
Write-Host "Using Region: $Region" -ForegroundColor Green
Write-Host "Using Service: $ServiceName" -ForegroundColor Green

# 1. Check gcloud authentication and project
Write-Host "`n1️⃣ Checking gcloud authentication..." -ForegroundColor Yellow
try {
    $currentAccount = gcloud config get-value account 2>$null
    $currentProject = gcloud config get-value project 2>$null
    
    Write-Host "✅ Authenticated as: $currentAccount" -ForegroundColor Green
    Write-Host "✅ Current project: $currentProject" -ForegroundColor Green
    
    if ($currentProject -ne $ProjectId) {
        Write-Host "⚠️  Setting project to $ProjectId..." -ForegroundColor Yellow
        gcloud config set project $ProjectId
    }
} catch {
    Write-Host "❌ Authentication issue. Run: gcloud auth login" -ForegroundColor Red
    exit 1
}

# 2. Check required APIs
Write-Host "`n2️⃣ Checking required APIs..." -ForegroundColor Yellow
$requiredApis = @(
    "cloudbuild.googleapis.com",
    "run.googleapis.com", 
    "containerregistry.googleapis.com",
    "bigquery.googleapis.com",
    "iam.googleapis.com"
)

foreach ($api in $requiredApis) {
    $apiStatus = gcloud services list --enabled --filter="name:$api" --format="value(name)" 2>$null
    if ($apiStatus) {
        Write-Host "✅ $api enabled" -ForegroundColor Green
    } else {
        Write-Host "❌ $api not enabled. Enabling..." -ForegroundColor Red
        gcloud services enable $api
    }
}

# 3. Check billing
Write-Host "`n3️⃣ Checking billing..." -ForegroundColor Yellow
$billingAccount = gcloud beta billing projects describe $ProjectId --format="value(billingAccountName)" 2>$null
if ($billingAccount) {
    Write-Host "✅ Billing is enabled" -ForegroundColor Green
} else {
    Write-Host "❌ Billing is not enabled! Enable it at: https://console.cloud.google.com/billing" -ForegroundColor Red
}

# 4. Check service account
Write-Host "`n4️⃣ Checking service account..." -ForegroundColor Yellow
$ServiceAccount = "wallet-api-service@$ProjectId.iam.gserviceaccount.com"
$saExists = gcloud iam service-accounts describe $ServiceAccount 2>$null

if ($saExists) {
    Write-Host "✅ Service account exists: $ServiceAccount" -ForegroundColor Green
    
    # Check IAM bindings
    Write-Host "Checking IAM permissions..." -ForegroundColor Yellow
    $iamPolicy = gcloud projects get-iam-policy $ProjectId --format=json | ConvertFrom-Json
    $saRoles = $iamPolicy.bindings | Where-Object { $_.members -contains "serviceAccount:$ServiceAccount" } | ForEach-Object { $_.role }
    
    $requiredRoles = @("roles/bigquery.dataEditor", "roles/bigquery.user")
    foreach ($role in $requiredRoles) {
        if ($saRoles -contains $role) {
            Write-Host "✅ Has role: $role" -ForegroundColor Green
        } else {
            Write-Host "❌ Missing role: $role. Adding..." -ForegroundColor Red
            gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$ServiceAccount" --role=$role
        }
    }
} else {
    Write-Host "❌ Service account doesn't exist. Creating..." -ForegroundColor Red
    gcloud iam service-accounts create wallet-api-service --display-name="Wallet API Service Account"
    gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$ServiceAccount" --role="roles/bigquery.dataEditor"
    gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$ServiceAccount" --role="roles/bigquery.user"
    Write-Host "✅ Service account created with permissions" -ForegroundColor Green
}

# 5. Check BigQuery dataset and table
Write-Host "`n5️⃣ Checking BigQuery setup..." -ForegroundColor Yellow
$Dataset = "wallet_db"
$Table = "wallets"

# Check if bq command is available
try {
    $bqVersion = bq version 2>$null
    Write-Host "✅ BigQuery CLI available" -ForegroundColor Green
} catch {
    Write-Host "⚠️  BigQuery CLI not found. Installing..." -ForegroundColor Yellow
    gcloud components install bq
}

# Check dataset
$datasetExists = bq show --dataset --project_id=$ProjectId $Dataset 2>$null
if ($datasetExists) {
    Write-Host "✅ Dataset exists: $Dataset" -ForegroundColor Green
} else {
    Write-Host "❌ Dataset missing. Creating..." -ForegroundColor Red
    bq mk --dataset --location=US $ProjectId`:$Dataset
    Write-Host "✅ Dataset created" -ForegroundColor Green
}

# Check table
$tableExists = bq show --table --project_id=$ProjectId $Dataset.$Table 2>$null
if ($tableExists) {
    Write-Host "✅ Table exists: $Table" -ForegroundColor Green
} else {
    Write-Host "❌ Table missing. Creating..." -ForegroundColor Red
    $schema = "id:STRING:REQUIRED,address:STRING:REQUIRED,score:INTEGER:REQUIRED,is_active:BOOLEAN:REQUIRED,created_at:TIMESTAMP:REQUIRED,last_updated:TIMESTAMP:REQUIRED"
    bq mk --table --schema=$schema $ProjectId`:$Dataset.$Table
    Write-Host "✅ Table created" -ForegroundColor Green
}

# 6. Check Cloud Build logs
Write-Host "`n6️⃣ Checking recent Cloud Build logs..." -ForegroundColor Yellow
$recentBuilds = gcloud builds list --limit=3 --format="table(id,status,createTime,logUrl)" 2>$null
if ($recentBuilds) {
    Write-Host "Recent builds:" -ForegroundColor Cyan
    Write-Host $recentBuilds
    
    $showLogs = Read-Host "Show logs for latest failed build? (y/n)"
    if ($showLogs -eq 'y' -or $showLogs -eq 'Y') {
        $latestBuild = gcloud builds list --limit=1 --format="value(id)" 2>$null
        if ($latestBuild) {
            Write-Host "`nShowing logs for build: $latestBuild" -ForegroundColor Cyan
            gcloud builds log $latestBuild
        }
    }
}

# 7. Check existing Cloud Run service
Write-Host "`n7️⃣ Checking existing Cloud Run service..." -ForegroundColor Yellow
$existingService = gcloud run services describe $ServiceName --region=$Region --format="value(metadata.name)" 2>$null
if ($existingService) {
    Write-Host "✅ Service '$ServiceName' already exists" -ForegroundColor Green
    $serviceUrl = gcloud run services describe $ServiceName --region=$Region --format="value(status.url)" 2>$null
    Write-Host "Current URL: $serviceUrl" -ForegroundColor Cyan
    
    # Check service account on existing service
    $currentSA = gcloud run services describe $ServiceName --region=$Region --format="value(spec.template.spec.serviceAccountName)" 2>$null
    if ($currentSA -eq $ServiceAccount) {
        Write-Host "✅ Service using correct service account" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Service using different service account: $currentSA" -ForegroundColor Yellow
    }
} else {
    Write-Host "ℹ️  Service '$ServiceName' does not exist (normal for first deployment)" -ForegroundColor Blue
}

# 8. Test simple deployment with corrected cloudbuild.yaml
Write-Host "`n8️⃣ Testing deployment with fixed configuration..." -ForegroundColor Yellow
$testDeploy = Read-Host "Would you like to try a simple deployment now? (y/n)"

if ($testDeploy -eq 'y' -or $testDeploy -eq 'Y') {
    Write-Host "🚀 Starting test deployment..." -ForegroundColor Green
    
    # Create a corrected cloudbuild.yaml
    $correctedCloudBuild = @"
steps:
  # Build the container image with no cache
  - name: 'gcr.io/cloud-builders/docker'
    args: [
      'build', '--no-cache',
      '-t', 'gcr.io/$PROJECT_ID/wallet-api-bigquery:`$BUILD_ID',
      '-t', 'gcr.io/$PROJECT_ID/wallet-api-bigquery:latest',
      '.'
    ]

  # Push the container image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/wallet-api-bigquery:`$BUILD_ID']

  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/wallet-api-bigquery:latest']

  # Deploy to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args: [
      'run', 'deploy', '$ServiceName',
      '--image', 'gcr.io/$PROJECT_ID/wallet-api-bigquery:latest',
      '--region', '$Region',
      '--platform', 'managed',
      '--allow-unauthenticated',
      '--port', '8080',
      '--memory', '2Gi',
      '--cpu', '2',
      '--min-instances', '1',
      '--max-instances', '10',
      '--service-account', '$ServiceAccount',
      '--set-env-vars', 'GOOGLE_CLOUD_PROJECT=$PROJECT_ID,BIGQUERY_DATASET=$Dataset,BIGQUERY_TABLE=$Table,API_HOST=0.0.0.0,API_PORT=8080,DEBUG=False,ALLOWED_ORIGINS=*'
    ]

substitutions:
  _REGION: '$Region'

options:
  logging: CLOUD_LOGGING_ONLY

images:
  - 'gcr.io/$PROJECT_ID/wallet-api-bigquery:`$BUILD_ID'
  - 'gcr.io/$PROJECT_ID/wallet-api-bigquery:latest'
"@

    # Save corrected cloudbuild.yaml
    $correctedCloudBuild | Out-File -FilePath "cloudbuild-fixed.yaml" -Encoding UTF8
    
    Write-Host "Created corrected cloudbuild-fixed.yaml" -ForegroundColor Green
    Write-Host "Starting Cloud Build..." -ForegroundColor Yellow
    
    gcloud builds submit --config cloudbuild-fixed.yaml .
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "🎉 Deployment successful!" -ForegroundColor Green
        $serviceUrl = gcloud run services describe $ServiceName --region=$Region --format="value(status.url)"
        Write-Host "Service URL: $serviceUrl" -ForegroundColor Cyan
        Write-Host "Test health: $serviceUrl/health" -ForegroundColor Cyan
    } else {
        Write-Host "❌ Deployment failed. Check the logs above." -ForegroundColor Red
    }
}

Write-Host "`n✅ Debug complete!" -ForegroundColor Green
Write-Host "`n💡 Common Cloud Build failure solutions:" -ForegroundColor Cyan
Write-Host "1. Service account permissions missing" -ForegroundColor White
Write-Host "2. BigQuery dataset/table doesn't exist" -ForegroundColor White  
Write-Host "3. Incorrect environment variable format" -ForegroundColor White
Write-Host "4. Region mismatch in cloudbuild.yaml" -ForegroundColor White
Write-Host "5. Service account name format error" -ForegroundColor White

Read-Host "`nPress Enter to exit"