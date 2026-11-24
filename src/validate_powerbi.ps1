param([Parameter(Mandatory=$true)][int]$Port)
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path $PSScriptRoot -Parent
$biBin = Split-Path (Get-Process PBIDesktop | Select-Object -First 1).Path
$clientDir = Join-Path $env:TEMP 'northstar-powerbi-client'
New-Item -ItemType Directory -Path $clientDir -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $biBin 'Microsoft.PowerBI.AdomdClient.dll') -Destination $clientDir -Force
Add-Type -Path (Join-Path $clientDir 'Microsoft.PowerBI.AdomdClient.dll')
$connection = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection("Data Source=localhost:$Port")
$connection.Open()
function Read-Dax([string]$Query) {
    $command = $connection.CreateCommand()
    $command.CommandText = $Query
    $reader = $command.ExecuteReader()
    $rows = @()
    while ($reader.Read()) {
        $row = [ordered]@{}
        for ($i=0; $i -lt $reader.FieldCount; $i++) {
            $value = $reader.GetValue($i)
            $row[$reader.GetName($i).Trim('[',']')] = $(if ($value -is [DBNull]) { $null } else { $value })
        }
        $rows += [pscustomobject]$row
    }
    $reader.Close()
    return $rows
}
try {
 $monthly = Read-Dax @'
EVALUATE SELECTCOLUMNS(SUMMARIZECOLUMNS(DimPeriod[Period],DimAgency[Agency],
 "Actual",[Actual obligations],"Plan",[Planned obligations],"Variance",[Plan minus actual],
 "YTDActual",[YTD actual at latest month],"YTDPlan",[YTD plan at latest month]),
 "Period",DimPeriod[Period],"Agency",DimAgency[Agency],"Actual",[Actual],"Plan",[Plan],"Variance",[Variance],"YTDActual",[YTDActual],"YTDPlan",[YTDPlan])
'@
 $overall = Read-Dax 'EVALUATE ROW("YTDActual",[YTD actual at latest month],"YTDPlan",[YTD plan at latest month],"Months",[Reported months])'
 $model=Get-Content -LiteralPath (Join-Path $ProjectRoot 'powerbi/native/NYC_Obligations.SemanticModel/model.bim') -Raw | ConvertFrom-Json
 $measureNames=@($model.model.tables | ForEach-Object {$_.measures} | Where-Object {$_} | ForEach-Object {$_.name})
 $pairs=@($measureNames | ForEach-Object {'"'+$_+'", ['+$_+']'})
 $all=Read-Dax ('EVALUATE ROW('+($pairs -join ',')+')')
 @{monthly=$monthly;overall=$overall;allMeasures=$all;measureCount=$measureNames.Count} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $ProjectRoot 'reports/powerbi_native_results.json') -Encoding utf8
 Write-Output "Native DAX executed for $($monthly.Count) agency/months and $($measureNames.Count) measures."
} finally {$connection.Close()}
