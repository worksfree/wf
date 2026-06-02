# ================================================================
# create_early_adopters.ps1
# Creates 50 early-adopter accounts in Supabase
#   Email   : early101@worksfree.co.kr ~ early150@worksfree.co.kr
#   Password: WFearly!2026  (shared)
#   Role    : general
#   Credits : 999,999 cr   (treated as unlimited)
#
# Usage:
#   .\create_early_adopters.ps1 -ServiceRoleKey "eyJhbGci..."
#
# Service Role Key: Supabase Dashboard > Project Settings > API
#                   > "service_role" (secret key)
# ================================================================

param(
    [Parameter(Mandatory=$true)]
    [string]$ServiceRoleKey,
    [int]$StartNum = 101,
    [int]$EndNum   = 150
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding           = [System.Text.Encoding]::UTF8

$SUPABASE_URL = 'https://rkycwfpkzorfpcxfvaqt.supabase.co'
$SHARED_PW    = 'WFearly!2026'
$CREDIT_GRANT = 999999

$authHeaders = @{
    'Authorization' = "Bearer $ServiceRoleKey"
    'apikey'        = $ServiceRoleKey
    'Content-Type'  = 'application/json'
}
$restHeaders = @{
    'Authorization' = "Bearer $ServiceRoleKey"
    'apikey'        = $ServiceRoleKey
    'Content-Type'  = 'application/json'
    'Prefer'        = 'resolution=merge-duplicates'
}

$results    = [System.Collections.Generic.List[PSObject]]::new()
$total      = $EndNum - $StartNum + 1
$successCnt = 0
$failCnt    = 0

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host " WorksFree Early Adopter Account Creation" -ForegroundColor Cyan
Write-Host " Range: $StartNum ~ $EndNum  ($total accounts)" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

for ($i = $StartNum; $i -le $EndNum; $i++) {
    $email = "early${i}@worksfree.co.kr"
    $name  = "Early Adopter $i"
    $seq   = $i - $StartNum + 1

    Write-Host "[$seq/$total] $email ..." -NoNewline

    try {
        # -- 1. Create auth user ----------------------------------------
        $authBody = @{
            email         = $email
            password      = $SHARED_PW
            email_confirm = $true
            user_metadata = @{ full_name = $name }
        } | ConvertTo-Json -Compress -Depth 4

        $authResp = Invoke-RestMethod `
            -Uri     "$SUPABASE_URL/auth/v1/admin/users" `
            -Method  Post `
            -Headers $authHeaders `
            -Body    $authBody

        $userId = $authResp.id

        # -- 2. Upsert profiles row -------------------------------------
        $profileBody = @{
            id        = $userId
            email     = $email
            name      = $name
            role      = 'general'
            agreed_at = (Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ')
        } | ConvertTo-Json -Compress

        Invoke-RestMethod `
            -Uri     "$SUPABASE_URL/rest/v1/profiles" `
            -Method  Post `
            -Headers $restHeaders `
            -Body    $profileBody | Out-Null

        # -- 3. Grant credits (999,999 cr) ------------------------------
        $creditBody = @{
            user_id = $userId
            delta   = $CREDIT_GRANT
            reason  = 'admin_grant'
            note    = 'Early adopter unlimited credits'
            env     = 'portal'
        } | ConvertTo-Json -Compress

        $creditHeaders = $restHeaders.Clone()
        $creditHeaders['Prefer'] = ''
        Invoke-RestMethod `
            -Uri     "$SUPABASE_URL/rest/v1/credits" `
            -Method  Post `
            -Headers $creditHeaders `
            -Body    $creditBody | Out-Null

        $results.Add([PSCustomObject]@{
            num    = $i
            email  = $email
            id     = $userId
            status = 'OK'
            error  = ''
        })
        $successCnt++
        Write-Host " OK  ($userId)" -ForegroundColor Green

    } catch {
        $errMsg = $_.Exception.Message
        # Handle duplicate account gracefully
        if ($errMsg -match 'already' -or $errMsg -match '422') {
            $errMsg = 'SKIP - account already exists'
            Write-Host " SKIP ($errMsg)" -ForegroundColor Yellow
        } else {
            Write-Host " ERR: $errMsg" -ForegroundColor Red
            $failCnt++
        }
        $results.Add([PSCustomObject]@{
            num    = $i
            email  = $email
            id     = ''
            status = 'ERR'
            error  = $errMsg
        })
    }

    # Rate-limit pause every 10 accounts
    if (($seq % 10 -eq 0) -and ($i -ne $EndNum)) {
        Write-Host "  -- 10 done, pausing 1s..." -ForegroundColor DarkGray
        Start-Sleep -Milliseconds 1000
    }
}

# -- Save result CSV (UTF-8 BOM so Excel opens correctly) ---------------
$csvPath    = Join-Path $PSScriptRoot "early_adopters_result_$(Get-Date -Format 'yyyyMMdd_HHmm').csv"
$utf8bom    = New-Object System.Text.UTF8Encoding $true
$csvContent = "num,email,id,status,error`n"
$results | ForEach-Object {
    $csvContent += "$($_.num),`"$($_.email)`",`"$($_.id)`",$($_.status),`"$($_.error)`"`n"
}
[System.IO.File]::WriteAllText($csvPath, $csvContent, $utf8bom)

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host " Done: OK=$successCnt  ERR=$failCnt  Total=$total" -ForegroundColor Cyan
Write-Host " Result: $csvPath" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[ Login Info ]" -ForegroundColor Yellow
Write-Host "  Email   : early101@worksfree.co.kr ~ early150@worksfree.co.kr" -ForegroundColor White
Write-Host "  Password: $SHARED_PW" -ForegroundColor White
Write-Host "  Role    : general" -ForegroundColor White
Write-Host "  Credits : $CREDIT_GRANT cr per account" -ForegroundColor White
