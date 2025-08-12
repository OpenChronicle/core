# OpenChronicle Architecture Guard - Hexagonal Boundaries
# Enforces clean layer separation in hexagonal architecture

Write-Output "Checking hexagonal architecture compliance..."

# Domain layer should not import from application/infrastructure
$DOMAIN_VIOLATIONS = Get-ChildItem -Path "src\openchronicle\domain\**\*.py" -Recurse -ErrorAction SilentlyContinue | Select-String -Pattern "from src\.openchronicle\.application|from src\.openchronicle\.infrastructure" -ErrorAction SilentlyContinue

if ($DOMAIN_VIOLATIONS) {
    Write-Output "DOMAIN LAYER VIOLATION: Domain importing from outer layers!"
    Write-Output "Hexagonal architecture requires domain independence:"
    Write-Output $DOMAIN_VIOLATIONS
    Write-Output ""
    Write-Output "Architecture layers (inside to outside):"
    Write-Output "  domain/ -> application/ -> infrastructure/ -> interfaces/"
    Write-Output "  Inner layers must NOT import from outer layers"
    exit 1
} else {
    Write-Output "Domain layer boundaries respected - hexagonal architecture maintained!"
}
