# Wallet API Deployment Script for Google Cloud (PowerShell)
# Make sure you have gcloud CLI installed and authenticated

param(
    [string]$ProjectId = $env:PROJECT_ID,
    [string]$Region = "asia-southeast1",
    [string]$ServiceName = "wallet-api"
)

# Configuration
if (-not $ProjectId) {
    $ProjectId = Read-Host "Enter your Google Cloud Project ID"
}

$ImageName = "gcr.io/$ProjectId/$ServiceName"

Write-Host "🚀 Starting deployment of Wallet API to Google Cloud..." -ForegroundColor Green
Write-Host "Project ID: $ProjectId" -ForegroundColor Cyan
Write-Host "Region: $Region" -ForegroundColor Cyan
Write-Host "Service: $ServiceName" -ForegroundColor Cyan

# Check if gcloud is installed
try {
    $null = Get-Command gcloud -ErrorAction Stop
    Write-Host "✅ gcloud CLI found" -ForegroundColor Green
} catch {
    Write-Host "❌ gcloud CLI is not installed. Please install it first." -ForegroundColor Red
    Write-Host "Visit: https://cloud.google.com/sdk/docs/install" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if user is authenticated
$authCheck = gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>$null
if (-not $authCheck) {
    Write-Host "❌ Not authenticated with gcloud. Please run 'gcloud auth login'" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Set project
Write-Host "📋 Setting project..." -ForegroundColor Yellow
gcloud config set project $ProjectId

# Enable required APIs
Write-Host "🔧 Enabling required APIs..." -ForegroundColor Yellow
gcloud services enable cloudbuild.googleapis.com run.googleapis.com containerregistry.googleapis.com secretmanager.googleapis.com

# Create secret for MongoDB URL (if it doesn't exist)
Write-Host "🔐 Setting up secrets..." -ForegroundColor Yellow
$secretExists = gcloud secrets describe wallet-api-secrets 2>$null
if (-not $secretExists) {
    Write-Host "Creating new secret for MongoDB URL..." -ForegroundColor Yellow
    $MongoUrl = Read-Host "Please enter your MongoDB connection string" -AsSecureString
    $PlainMongoUrl = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($MongoUrl))
    $PlainMongoUrl | gcloud secrets create wallet-api-secrets --data-file=-
    Write-Host "✅ Secret created successfully" -ForegroundColor Green
} else {
    Write-Host "✅ Secret already exists" -ForegroundColor Green
}

# Function definitions
function Deploy-WithCloudBuild {
    Write-Host "🏗️  Building and deploying with Cloud Build..." -ForegroundColor Yellow
    gcloud builds submit --config cloudbuild.yaml --substitutions "_REGION=$Region" .
    Write-Host "✅ Deployment completed with Cloud Build!" -ForegroundColor Green
}

function Deploy-WithLocalBuild {
    Write-Host "🐳 Building Docker image locally..." -ForegroundColor Yellow
    
    # Build and push image
    docker build -t "${ImageName}:latest" .
    docker push "${ImageName}:latest"
    
    # Deploy to Cloud Run
    Write-Host "☁️  Deploying to Cloud Run..." -ForegroundColor Yellow
    gcloud run deploy $ServiceName `
        --image "${ImageName}:latest" `
        --region $Region `
        --platform managed `
        --allow-unauthenticated `
        --port 8080 `
        --memory 2Gi `
        --cpu 2 `
        --min-instances 1 `
        --max-instances 10 `
        --set-env-vars "DATABASE_NAME=wallet_db,COLLECTION_NAME=wallets,API_HOST=0.0.0.0,API_PORT=8080,DEBUG=False,ALLOWED_ORIGINS=*" `
        --update-secrets "MONGODB_URL=wallet-api-secrets:MONGODB_URL:latest"
    
    Write-Host "✅ Deployment completed with local build!" -ForegroundColor Green
}

function Deploy-ToAppEngine {
    Write-Host "🚀 Deploying to App Engine..." -ForegroundColor Yellow
    
    # Get MongoDB URL from secret and update app.yaml
    $MongoSecret = gcloud secrets versions access latest --secret="wallet-api-secrets"
    
    # Create temporary app.yaml with MongoDB URL
    (Get-Content app.yaml) -replace 'MONGODB_URL: ""', "MONGODB_URL: `"$MongoSecret`"" | Set-Content app-temp.yaml
    
    # Deploy
    gcloud app deploy app-temp.yaml --quiet
    
    # Cleanup
    Remove-Item app-temp.yaml
    
    Write-Host "✅ Deployment to App Engine completed!" -ForegroundColor Green
    return $true
}

# Choose deployment method
Write-Host ""
Write-Host "Choose deployment method:" -ForegroundColor Cyan
Write-Host "1) Cloud Build + Cloud Run (Recommended)" -ForegroundColor White
Write-Host "2) Local Build + Cloud Run" -ForegroundColor White  
Write-Host "3) App Engine" -ForegroundColor White

$choice = Read-Host "Enter choice (1-3)"
$isAppEngine = $false

switch ($choice) {
    "1" { 
        Deploy-WithCloudBuild 
    }
    "2" { 
        Deploy-WithLocalBuild 
    }
    "3" { 
        $isAppEngine = Deploy-ToAppEngine
    }
    default {
        Write-Host "❌ Invalid choice" -ForegroundColor Red
        exit 1
    }
}

# Get service URL and display results
Write-Host ""
if ($isAppEngine) {
    $AppUrl = gcloud app describe --format="value(defaultHostname)"
    Write-Host "🎉 Deployment successful!" -ForegroundColor Green
    Write-Host "App URL: https://$AppUrl" -ForegroundColor Cyan
    Write-Host "API Docs: https://$AppUrl/docs" -ForegroundColor Cyan
    Write-Host "Health Check: https://$AppUrl/health" -ForegroundColor Cyan
} else {
    $ServiceUrl = gcloud run services describe $ServiceName --region=$Region --format="value(status.url)"
    Write-Host "🎉 Deployment successful!" -ForegroundColor Green
    Write-Host "Service URL: $ServiceUrl" -ForegroundColor Cyan
    Write-Host "API Docs: $ServiceUrl/docs" -ForegroundColor Cyan
    Write-Host "Health Check: $ServiceUrl/health" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Yellow
Write-Host "1. Test your API endpoints" -ForegroundColor White
Write-Host "2. Set up monitoring in Cloud Console" -ForegroundColor White
Write-Host "3. Configure custom domain (optional)" -ForegroundColor White
Write-Host "4. Set up CI/CD with Cloud Build triggers (optional)" -ForegroundColor White

Read-Host "Press Enter to exit"