#requires -Version 5.1
<#
.SYNOPSIS
Prepares the two NYC EPA NO2 files used by df_ingest_epa_no2.
.PARAMETER OutputRoot
The script creates an epa_no2 folder under this path. Upload its CSV files
to lh_bronze/Files/epa_no2.
#>
param(
    [string]$OutputRoot = (Join-Path ([Environment]::GetFolderPath('UserProfile')) 'nyc-air-quality')
)

$ErrorActionPreference = 'Stop'

$years = @(2022, 2024)
# Bronx, Kings (Brooklyn), New York (Manhattan), Queens, and Richmond (Staten Island).
$nycCountyCodes = @('005', '047', '061', '081', '085')
$destination = New-Item -ItemType Directory -Path (Join-Path $OutputRoot 'epa_no2') -Force
$stagingPath = Join-Path $destination.FullName ('.stage-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $stagingPath | Out-Null

try {
    foreach ($year in $years) {
        $archiveName = "daily_42602_$year.zip"
        $archivePath = Join-Path $stagingPath $archiveName
        $yearPath = Join-Path $stagingPath "$year"
        Invoke-WebRequest -UseBasicParsing -Uri "https://aqs.epa.gov/aqsweb/airdata/$archiveName" -OutFile $archivePath -TimeoutSec 90
        Expand-Archive -LiteralPath $archivePath -DestinationPath $yearPath

        $sourceFile = Join-Path $yearPath "daily_42602_$year.csv"
        $rows = @(Import-Csv -LiteralPath $sourceFile -Encoding UTF8 | Where-Object {
            $_.'State Code' -eq '36' -and
            $_.'County Code' -in $nycCountyCodes -and
            $_.'Parameter Code' -eq '42602' -and
            $_.'Sample Duration' -eq '1 HOUR' -and
            $_.'Pollutant Standard' -eq 'NO2 1-hour 2010' -and
            $_.'Units of Measure' -eq 'Parts per billion' -and
            $_.'Event Type' -eq 'None' -and
            ($_.'Date Local' -like "$year-01-??" -or $_.'Date Local' -like "$year-02-??")
        })
        if ($rows.Count -eq 0) {
            throw "No matching EPA NO2 records for NYC in January-February $year."
        }

        $fileName = "epa_no2_nyc_${year}_jan_feb.csv"
        $stageFile = Join-Path $stagingPath $fileName
        $rows | Export-Csv -LiteralPath $stageFile -NoTypeInformation -Encoding UTF8
        Write-Host ("{0} prepared ({1} rows)." -f $fileName, $rows.Count)
    }

    Get-ChildItem -LiteralPath $stagingPath -File -Filter 'epa_no2_nyc_*.csv' |
        Move-Item -Destination $destination.FullName -Force
    Write-Host ("EPA CSV files are ready in {0}" -f $destination.FullName)
}
finally {
    Remove-Item -LiteralPath $stagingPath -Recurse -Force
}
