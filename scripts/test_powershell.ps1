$directories = @(
    "models",
    "data",
    "logs",
    "cache",
    "frontend",
    "configs"
)

foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force
        Write-Host $dir
    } else {
        Write-Host $dir
    }
}