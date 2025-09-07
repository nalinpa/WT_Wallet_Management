# Final deployment script with correct dataset/table names and aggressive cache busting
param(
    [string]$ProjectId = "crypto-tracker-cloudrun",
    [string]$Region = "asia-southeast1",
    [string]$Dataset = "crypto_analysis", 
    [string]$Table = "smart_wallets"
)

Write-Host "🚀 Final deployment with aggressive cache clearing..." -ForegroundColor Green
Write-Host "Project: $ProjectId" -ForegroundColor Cyan
Write-Host "Dataset: $Dataset" -ForegroundColor Cyan
Write-Host "Table: $Table" -ForegroundColor Cyan

# 1. Aggressive Docker cleanup
Write-Host "🧹 Performing aggressive Docker cleanup..." -ForegroundColor Yellow
docker system prune -a --volumes -f 2>$null
docker builder prune -a -f 2>$null

# 2. Verify requirements.txt content
Write-Host "📋 Verifying requirements.txt..." -ForegroundColor Yellow
if (Test-Path "requirements.txt") {
    $reqContent = Get-Content "requirements.txt" -Raw
    Write-Host "Current requirements.txt content:" -ForegroundColor Cyan
    Write-Host $reqContent
    
    if ($reqContent -like "*motor*" -or $reqContent -like "*pymongo*") {
        Write-Host "❌ FOUND MongoDB dependencies in requirements.txt!" -ForegroundColor Red
        Write-Host "Please remove 'motor' and 'pymongo' lines from requirements.txt" -ForegroundColor Red
        exit 1
    } else {
        Write-Host "✅ No MongoDB dependencies found" -ForegroundColor Green
    }
} else {
    Write-Host "❌ requirements.txt not found!" -ForegroundColor Red
    exit 1
}

# 3. Create correct BigQuery table if needed
Write-Host "🗄️  Ensuring BigQuery table exists..." -ForegroundColor Yellow
$tableExists = bq show --table --project_id=$ProjectId $Dataset.$Table 2>$null
if (-not $tableExists) {
    Write-Host "Creating BigQuery table with correct schema..." -ForegroundColor Yellow
    # Use correct bq command-line schema format (no :REQUIRED suffix)
    $schema = "id:STRING,address:STRING,score:INTEGER,is_active:BOOLEAN,created_at:TIMESTAMP,last_updated:TIMESTAMP"
    bq mk --table --schema=$schema $ProjectId`:$Dataset.$Table
    Write-Host "✅ Table created: $Dataset.$Table" -ForegroundColor Green
} else {
    Write-Host "✅ Table already exists: $Dataset.$Table" -ForegroundColor Green
}

# 4. Create fresh build directory
Write-Host "📁 Creating fresh build context..." -ForegroundColor Yellow
$buildDir = "build_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
New-Item -ItemType Directory -Path $buildDir -Force | Out-Null

# Copy files to fresh directory
$filesToCopy = @("app", "requirements.txt", "Dockerfile", ".dockerignore")
foreach ($item in $filesToCopy) {
    if (Test-Path $item) {
        Copy-Item -Path $item -Destination $buildDir -Recurse -Force
        Write-Host "Copied: $item" -ForegroundColor Gray
    }
}

# 5. Add cache busting timestamp to requirements.txt in build directory
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$buildReqPath = Join-Path $buildDir "requirements.txt"
$reqContent = Get-Content $buildReqPath -Raw
"# Cache bust: $timestamp`n$reqContent" | Set-Content $buildReqPath

# 6. Build with unique tag from fresh directory
Set-Location $buildDir
$uniqueTag = "gcr.io/$ProjectId/wallet-api-bigquery:final-$(Get-Date -Format 'yyyyMMdd-HHmmss')"

Write-Host "🐳 Building with completely fresh context..." -ForegroundColor Yellow
Write-Host "Tag: $uniqueTag" -ForegroundColor Gray

docker build --no-cache --pull -t $uniqueTag .

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Build successful!" -ForegroundColor Green
    
    # Push image
    Write-Host "📤 Pushing image..." -ForegroundColor Yellow
    docker push $uniqueTag
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Push successful!" -ForegroundColor Green
        
        # Deploy to Cloud Run
        Write-Host "☁️  Deploying to Cloud Run..." -ForegroundColor Yellow
        Set-Location ..
        
        gcloud run deploy wallet-api-bigquery `
            --image $uniqueTag `
            --region $Region `
            --platform managed `
            --allow-unauthenticated `
            --port 8080 `
            --memory 2Gi `
            --cpu 2 `
            --timeout 600 `
            --service-account wallet-api-service@$ProjectId.iam.gserviceaccount.com `
            --set-env-vars "GOOGLE_CLOUD_PROJECT=$ProjectId,BIGQUERY_DATASET=$Dataset,BIGQUERY_TABLE=$Table,API_HOST=0.0.0.0,API_PORT=8080,DEBUG=False,ALLOWED_ORIGINS=*"
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "🎉 Deployment successful!" -ForegroundColor Green
            $serviceUrl = gcloud run services describe wallet-api-bigquery --region=$Region --format="value(status.url)"
            Write-Host "Service URL: $serviceUrl" -ForegroundColor Cyan
            Write-Host "Health check: $serviceUrl/health" -ForegroundColor Cyan
            Write-Host "API docs: $serviceUrl/docs" -ForegroundColor Cyan
            
            # Test the health endpoint
            Write-Host "🔍 Testing health endpoint..." -ForegroundColor Yellow
            try {
                $response = Invoke-RestMethod -Uri "$serviceUrl/health" -TimeoutSec 10
                Write-Host "✅ Health check passed: $($response | ConvertTo-Json)" -ForegroundColor Green
            } catch {
                Write-Host "⚠️  Health check failed: $($_.Exception.Message)" -ForegroundColor Yellow
                Write-Host "Check logs: gcloud logs read --service=wallet-api-bigquery --limit=50" -ForegroundColor Gray
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

# Cleanup
Set-Location ..
Remove-Item -Path $buildDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "`n📊 Deployment Summary:" -ForegroundColor Cyan
Write-Host "Dataset: $Dataset" -ForegroundColor White
Write-Host "Table: $Table" -ForegroundColor White
Write-Host "Image: $uniqueTag" -ForegroundColor White