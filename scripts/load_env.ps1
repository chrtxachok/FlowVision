# scripts/load_env.ps1
$envFile = Join-Path $PSScriptRoot "..\.env"

if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)\s*=\s*(.+)\s*$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            
            $value = $value.Trim('"').Trim("'")
            Set-Item -Path "Env:$key" -Value $value
            Write-Host "загружено: $key"
        }
    }
    Write-Host "`n переменные загружены из .env"
} else {
    Write-Warning "файл .env не найден: $envFile"
}
'@ | Out-File -FilePath "scripts/load_env.ps1" -Encoding utf8'