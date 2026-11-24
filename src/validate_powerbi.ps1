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
EVALUATE SELECTCOLUMNS(
 SUMMARIZECOLUMNS(DimDate[YearMonth], DimBranch[Branch],
 "Revenue",[Revenue], "BudgetRevenue",[Budget Revenue], "Profit",[Operating Profit],
 "BudgetProfit",[Budget Profit], "Freight",[Freight], "Inventory",[Closing Inventory],
 "Orders",[Orders], "OnTime",[On-Time Orders], "Rate",[On-Time Delivery %]),
 "Month",DimDate[YearMonth], "Branch",DimBranch[Branch], "Revenue",[Revenue],
 "BudgetRevenue",[BudgetRevenue], "Profit",[Profit], "BudgetProfit",[BudgetProfit],
 "Freight",[Freight], "Inventory",[Inventory], "Orders",[Orders], "OnTime",[OnTime], "Rate",[Rate])
'@
    $annual = Read-Dax @'
EVALUATE SELECTCOLUMNS(
 SUMMARIZECOLUMNS(DimDate[Year], "Revenue",[Revenue], "Inventory",[Closing Inventory],
 "Prior",[Revenue Previous Year], "RevenueYTD",[Revenue YTD]),
 "Year",DimDate[Year],"Revenue",[Revenue],"Inventory",[Inventory],"Prior",[Prior],"RevenueYTD",[RevenueYTD])
'@
    $accounts = Read-Dax @'
EVALUATE SELECTCOLUMNS(
 SUMMARIZECOLUMNS(DimAccount[Account],DimAccount[Category],
 "Actual",[Actual Amount],"Budget",[Budget Amount],"Favorable",[Favorable Account Variance]),
 "Account",DimAccount[Account],"Category",DimAccount[Category],"Actual",[Actual],"Budget",[Budget],"Favorable",[Favorable])
'@
    $modelPath = Join-Path $ProjectRoot 'powerbi/native/Financial_Operational_Analytics.SemanticModel/model.bim'
    $model = Get-Content -LiteralPath $modelPath -Raw | ConvertFrom-Json
    $measureNames = @($model.model.tables | ForEach-Object { $_.measures } | Where-Object { $_ } | ForEach-Object { $_.name })
    $pairs = @($measureNames | ForEach-Object { '"' + $_ + '", [' + $_ + ']' })
    $allMeasures = Read-Dax ('EVALUATE ROW(' + ($pairs -join ',') + ')')
    $result = @{monthly=$monthly; annual=$annual; accounts=$accounts; allMeasures=$allMeasures; measureCount=$measureNames.Count}
    $result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $ProjectRoot 'reports/powerbi_native_results.json') -Encoding utf8
    Write-Output "Executed native DAX: $($monthly.Count) branch-months, $($annual.Count) years, $($accounts.Count) accounts, $($measureNames.Count) measures."
} finally { $connection.Close() }
