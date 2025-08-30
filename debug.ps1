# Debug Deployment Script - Helps identify and fix deployment issues
param(
    [string]$ProjectId = $env:PROJECT_ID,
    [string]$Region = "asia-southeast1"
)

Write-Host "🔍 Debugging Google Cloud Deployment Issues..." -ForegroundColor Cyan

# Configuration
if (-not $ProjectId) {
    $ProjectId = Read-Host "Enter your Google Cloud Project ID"
}

Write-Host "Using Project: $ProjectId" -ForegroundColor Green
Write-Host "Using Region: $Region" -ForegroundColor Green

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
    "secretmanager.googleapis.com"
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

# 4. Check Docker
Write-Host "`n4️⃣ Checking Docker..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version 2>$null
    Write-Host "✅ Docker installed: $dockerVersion" -ForegroundColor Green
    
    # Check if Docker is running
    $dockerInfo = docker info 2>$null
    if ($dockerInfo) {
        Write-Host "✅ Docker is running" -ForegroundColor Green
    } else {
        Write-Host "❌ Docker is not running. Start Docker Desktop!" -ForegroundColor Red
    }
    
    # Configure Docker for GCR
    Write-Host "🔧 Configuring Docker for Google Container Registry..." -ForegroundColor Yellow
    gcloud auth configure-docker --quiet
    Write-Host "✅ Docker configured for GCR" -ForegroundColor Green
    
} catch {
    Write-Host "❌ Docker not found. Install Docker Desktop!" -ForegroundColor Red
}

# 5. Check secrets
Write-Host "`n5️⃣ Checking secrets..." -ForegroundColor Yellow
$secretExists = gcloud secrets describe wallet-api-secrets 2>$null
if ($secretExists) {
    Write-Host "✅ MongoDB secret exists" -ForegroundColor Green
    
    # Test secret access
    try {
        $secretValue = gcloud secrets versions access latest --secret="wallet-api-secrets" 2>$null
        if ($secretValue -like "mongodb*") {
            Write-Host "✅ Secret contains valid MongoDB URL" -ForegroundColor Green
        } else {
            Write-Host "⚠️  Secret exists but might not be a valid MongoDB URL" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "❌ Cannot access secret. Check IAM permissions." -ForegroundColor Red
    }
} else {
    Write-Host "❌ MongoDB secret not found. Creating..." -ForegroundColor Red
    $MongoUrl = Read-Host "Enter your MongoDB connection string" -AsSecureString
    $PlainMongoUrl = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($MongoUrl))
    $PlainMongoUrl | gcloud secrets create wallet-api-secrets --data-file=-
    Write-Host "✅ Secret created" -ForegroundColor Green
}

# 6. Check existing Cloud Run service
Write-Host "`n6️⃣ Checking existing Cloud Run service..." -ForegroundColor Yellow
$existingService = gcloud run services describe wallet-api --region=$Region --format="value(metadata.name)" 2>$null
if ($existingService) {
    Write-Host "✅ Service 'wallet-api' already exists" -ForegroundColor Green
    $serviceUrl = gcloud run services describe wallet-api --region=$Region --format="value(status.url)" 2>$null
    Write-Host "Current URL: $serviceUrl" -ForegroundColor Cyan
} else {
    Write-Host "ℹ️  Service 'wallet-api' does not exist (this is normal for first deployment)" -ForegroundColor Blue
}

# 7. Check project files
Write-Host "`n7️⃣ Checking project files..." -ForegroundColor Yellow
$requiredFiles = @("Dockerfile", "requirements.txt", "app/main.py")
$missingFiles = @()

foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Host "✅ $file found" -ForegroundColor Green
    } else {
        Write-Host "❌ $file missing" -ForegroundColor Red
        $missingFiles += $file
    }
}

if ($missingFiles.Count -gt 0) {
    Write-Host "❌ Missing required files. Make sure you're in the correct directory!" -ForegroundColor Red
    exit 1
}

# 8. Test a simple deployment
Write-Host "`n8️⃣ Testing simple deployment..." -ForegroundColor Yellow
$deployChoice = Read-Host "Would you like to try a simple deployment now? (y/n)"

if ($deployChoice -eq 'y' -or $deployChoice -eq 'Y') {
    Write-Host "🚀 Starting simple deployment..." -ForegroundColor Green
    
    # Build image locally
    Write-Host "Building Docker image..." -ForegroundColor Yellow
    $imageName = "gcr.io/$ProjectId/wallet-api:debug"
    docker build -t $imageName . 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Docker build successful" -ForegroundColor Green
        
        # Push image
        Write-Host "Pushing image to GCR..." -ForegroundColor Yellow
        docker push $imageName 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Image push successful" -ForegroundColor Green
            
            # Deploy to Cloud Run
            Write-Host "Deploying to Cloud Run..." -ForegroundColor Yellow
            gcloud run deploy wallet-api-debug `
                --image $imageName `
                --region $Region `
                --platform managed `
                --allow-unauthenticated `
                --port 8080 `
                --memory 1Gi `
                --set-env-vars "DATABASE_NAME=wallet_db,COLLECTION_NAME=wallets,API_HOST=0.0.0.0,API_PORT=8080" `
                --update-secrets "MONGODB_URL=wallet-api-secrets:MONGODB_URL:latest"
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "🎉 Debug deployment successful!" -ForegroundColor Green
                $debugUrl = gcloud run services describe wallet-api-debug --region=$Region --format="value(status.url)"
                Write-Host "Debug service URL: $debugUrl" -ForegroundColor Cyan
                Write-Host "Test health: $debugUrl/health" -ForegroundColor Cyan
                
                # Clean up debug service
                $cleanup = Read-Host "Delete debug service? (y/n)"
                if ($cleanup -eq 'y' -or $cleanup -eq 'Y') {
                    gcloud run services delete wallet-api-debug --region=$Region --quiet
                    Write-Host "✅ Debug service cleaned up" -ForegroundColor Green
                }
            } else {
                Write-Host "❌ Cloud Run deployment failed" -ForegroundColor Red
            }
        } else {
            Write-Host "❌ Image push failed" -ForegroundColor Red
        }
    } else {
        Write-Host "❌ Docker build failed" -ForegroundColor Red
    }
}

# 9. Show Cloud Build logs if available
Write-Host "`n9️⃣ Checking recent Cloud Build logs..." -ForegroundColor Yellow
$recentBuilds = gcloud builds list --limit=3 --format="table(id,status,createTime)" 2>$null
if ($recentBuilds) {
    Write-Host "Recent builds:" -ForegroundColor Cyan
    Write-Host $recentBuilds
    
    $showLogs = Read-Host "Show logs for latest build? (y/n)"
    if ($showLogs -eq 'y' -or $showLogs -eq 'Y') {
        $latestBuild = gcloud builds list --limit=1 --format="value(id)" 2>$null
        if ($latestBuild) {
            gcloud builds log $latestBuild
        }
    }
}

Write-Host "`n✅ Debug complete!" -ForegroundColor Green
Write-Host "`n💡 Common solutions:" -ForegroundColor Cyan
Write-Host "1. Make sure Docker Desktop is running" -ForegroundColor White
Write-Host "2. Enable billing on your Google Cloud project" -ForegroundColor White  
Write-Host "3. Ensure all required APIs are enabled" -ForegroundColor White
Write-Host "4. Check that your MongoDB connection string is correct" -ForegroundColor White
Write-Host "5. Try the simple deployment option above" -ForegroundColor White

Read-Host "`nPress Enter to exit"