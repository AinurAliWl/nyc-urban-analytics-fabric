#requires -Version 5.1
<#
.SYNOPSIS
Downloads the five OpenAQ PM2.5 JSON batches used by df_ingest_openaq.
.PARAMETER OutputRoot
The script creates an openaq_pm25 folder under this path. Upload its JSON files
to lh_bronze/Files/openaq_pm25.
.NOTES
Set OPENAQ_API_KEY in the environment or enter the key at the hidden prompt.
The original API responses are saved so Dataflow Gen2 can read their metadata.
#>
param(
    [string]$OutputRoot = (Join-Path ([Environment]::GetFolderPath('UserProfile')) 'nyc-air-quality')
)

$ErrorActionPreference = 'Stop'

$apiKey = $env:OPENAQ_API_KEY
if ([string]::IsNullOrWhiteSpace($apiKey)) {
    $secureKey = Read-Host 'OpenAQ API key' -AsSecureString
    try {
        $apiKey = [System.Net.NetworkCredential]::new('', $secureKey).Password
    }
    finally {
        $secureKey.Dispose()
    }
}
if ([string]::IsNullOrWhiteSpace($apiKey)) {
    throw 'Enter an OpenAQ API key or set OPENAQ_API_KEY.'
}

# Match the batch list in the Fabric Dataflow.
$batches = @(
    @{ SensorId = 673; Year = 2022 }
    @{ SensorId = 1102; Year = 2022 }
    @{ SensorId = 673; Year = 2024 }
    @{ SensorId = 1102; Year = 2024 }
    @{ SensorId = 1152; Year = 2024 }
)
$limit = 100
$headers = @{ 'X-API-Key' = $apiKey.Trim() }

$destination = New-Item -ItemType Directory -Path (Join-Path $OutputRoot 'openaq_pm25') -Force
$stagingPath = Join-Path $destination.FullName ('.stage-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $stagingPath | Out-Null
try {
    foreach ($batch in $batches) {
        $sensor = $batch.SensorId
        $year = $batch.Year
        $fileName = "openaq_pm25_${sensor}_${year}_jan_feb.json"
        $stageFile = Join-Path $stagingPath $fileName
        # March 1 covers the end of February. The Dataflow filters by local date.
        $uri = "https://api.openaq.org/v3/sensors/$sensor/days?date_from=$year-01-01&date_to=$year-03-01&limit=$limit&page=1"
        Invoke-WebRequest -UseBasicParsing -Uri $uri -Headers $headers -OutFile $stageFile -TimeoutSec 90
        $payload = Get-Content -LiteralPath $stageFile -Raw -Encoding UTF8 | ConvertFrom-Json
        $rows = @($payload.results)
        if ($null -eq $payload.results -or $rows.Count -eq 0 -or $rows.Count -ge $limit) {
            throw "Unexpected OpenAQ result size for sensor $sensor in $year."
        }
        foreach ($row in $rows) {
            if ($row.parameter.name -ne 'pm25' -or
                [string]::IsNullOrWhiteSpace($row.parameter.units) -or
                $null -eq $row.period.datetimeFrom.local) {
                throw "Unexpected OpenAQ daily result for sensor $sensor in $year."
            }
        }
        Write-Host ("{0} downloaded ({1} API rows before the Fabric date filter)." -f $fileName, $rows.Count)
    }

    Get-ChildItem -LiteralPath $stagingPath -File | Move-Item -Destination $destination.FullName -Force
    Write-Host ("OpenAQ JSON files are ready in {0}" -f $destination.FullName)
}
finally {
    Remove-Item -LiteralPath $stagingPath -Recurse -Force
}
