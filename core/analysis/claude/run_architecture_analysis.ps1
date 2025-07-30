# OpenChronicle Core Architecture Analysis Runner
# Automates the execution of architecture analysis commands
# Usage: .\run_architecture_analysis.ps1

param(
    [switch]$SkipComplexity,
    [switch]$SkipDependencies,
    [switch]$Verbose
)

Write-Host "🔍 OpenChronicle Core Architecture Analysis" -ForegroundColor Cyan
Write-Host "=" * 50

$coreDir = Join-Path $PSScriptRoot "..\.."
$outputDir = $PSScriptRoot

# Ensure we're in the right directory
Push-Location $coreDir

try {
    # 1. Basic Metrics Collection
    Write-Host "`n📊 Collecting Basic Metrics..." -ForegroundColor Yellow
    
    $metrics = Get-ChildItem "*.py" | ForEach-Object { 
        $content = Get-Content $_.FullName
        $lines = ($content | Measure-Object -Line).Lines
        $classes = ($content | Select-String "^class ").Count
        $methods = ($content | Select-String "^\s+def ").Count
        $async_methods = ($content | Select-String "^\s+async def ").Count
        $imports = ($content | Select-String "^(from|import)" | Where-Object { $_ -match "(core\.|utilities\.)" }).Count
        
        [PSCustomObject]@{
            File = $_.Name
            Lines = $lines
            Classes = $classes
            Methods = $methods
            AsyncMethods = $async_methods
            InternalImports = $imports
            MethodDensity = [math]::Round($methods / [math]::Max($lines, 1), 3)
        }
    }
    
    # Display summary table
    $metrics | Sort-Object Lines -Descending | Format-Table -AutoSize
    
    # Export to CSV for further analysis
    $metricsFile = Join-Path $outputDir "core_metrics_$(Get-Date -Format 'yyyyMMdd_HHmmss').csv"
    $metrics | Export-Csv -Path $metricsFile -NoTypeInformation
    Write-Host "📁 Metrics exported to: $metricsFile" -ForegroundColor Green

    # 2. Complexity Analysis (if not skipped)
    if (-not $SkipComplexity) {
        Write-Host "`n🧮 Running Complexity Analysis..." -ForegroundColor Yellow
        
        # Check if radon is available
        try {
            python -m radon --version 2>$null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✅ Radon found, generating complexity metrics..."
                
                # Cyclomatic complexity
                Write-Host "`nCyclomatic Complexity:" -ForegroundColor Cyan
                python -m radon cc . --total-average --show-complexity
                
                # Maintainability index
                Write-Host "`nMaintainability Index:" -ForegroundColor Cyan
                python -m radon mi . --show
                
                # Raw metrics
                Write-Host "`nRaw Metrics:" -ForegroundColor Cyan
                python -m radon raw . --summary
                
            } else {
                Write-Host "⚠️  Radon not found. Installing..." -ForegroundColor Yellow
                python -m pip install radon
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "✅ Radon installed successfully"
                    python -m radon cc . --total-average --show-complexity
                } else {
                    Write-Host "❌ Failed to install radon. Skipping complexity analysis." -ForegroundColor Red
                }
            }
        } catch {
            Write-Host "❌ Error running complexity analysis: $_" -ForegroundColor Red
        }
    }

    # 3. Dependency Analysis (if not skipped)
    if (-not $SkipDependencies) {
        Write-Host "`n🔗 Analyzing Dependencies..." -ForegroundColor Yellow
        
        $dependencyReport = @()
        
        Get-ChildItem "*.py" | ForEach-Object {
            $content = Get-Content $_.FullName
            $coreImports = $content | Select-String "^(from|import).*core\." | ForEach-Object { $_.Line.Trim() }
            $utilityImports = $content | Select-String "^(from|import).*utilities\." | ForEach-Object { $_.Line.Trim() }
            $externalImports = $content | Select-String "^(from|import)" | Where-Object { $_ -notmatch "(core\.|utilities\.)" } | ForEach-Object { $_.Line.Trim() }
            
            if ($Verbose -or $coreImports.Count -gt 5) {
                Write-Host "`n📁 $($_.Name):" -ForegroundColor White
                if ($coreImports) {
                    Write-Host "  Core imports ($($coreImports.Count)):" -ForegroundColor Cyan
                    $coreImports | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
                }
                if ($utilityImports) {
                    Write-Host "  Utility imports ($($utilityImports.Count)):" -ForegroundColor Magenta
                    $utilityImports | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
                }
            }
            
            $dependencyReport += [PSCustomObject]@{
                File = $_.Name
                CoreDeps = $coreImports.Count
                UtilityDeps = $utilityImports.Count
                ExternalDeps = $externalImports.Count
                TotalDeps = $coreImports.Count + $utilityImports.Count + $externalImports.Count
            }
        }
        
        # Summary table
        Write-Host "`n📊 Dependency Summary:" -ForegroundColor Yellow
        $dependencyReport | Sort-Object TotalDeps -Descending | Format-Table -AutoSize
        
        # High coupling warnings
        $highCoupling = $dependencyReport | Where-Object { $_.CoreDeps -gt 5 }
        if ($highCoupling) {
            Write-Host "`n⚠️  High Coupling Files (>5 core dependencies):" -ForegroundColor Red
            $highCoupling | ForEach-Object { Write-Host "  $($_.File): $($_.CoreDeps) core deps" -ForegroundColor Yellow }
        }
    }

    # 4. Pattern Detection
    Write-Host "`n🔍 Detecting Common Patterns..." -ForegroundColor Yellow
    
    $patterns = @{
        "Async Methods" = "^\s+async def"
        "Property Decorators" = "^\s+@property"
        "Class Definitions" = "^class"
        "Error Handling" = "(try:|except|finally:)"
        "Logging Calls" = "(log_system_event|logger\.|logging\.)"
        "Model Adapter Usage" = "(model_manager|ModelManager)"
        "Database Operations" = "(query|execute|fetch|commit)"
        "Memory Operations" = "(memory_manager|MemoryManager)"
    }
    
    foreach ($pattern in $patterns.GetEnumerator()) {
        $totalMatches = 0
        $fileMatches = @()
        
        Get-ChildItem "*.py" | ForEach-Object {
            $patternMatches = (Get-Content $_.FullName | Select-String $pattern.Value).Count
            if ($patternMatches -gt 0) {
                $totalMatches += $patternMatches
                $fileMatches += "$($_.Name): $patternMatches"
            }
        }
        
        if ($totalMatches -gt 0) {
            Write-Host "`n🔸 $($pattern.Key): $totalMatches total occurrences" -ForegroundColor Cyan
            if ($Verbose) {
                $fileMatches | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
            }
        }
    }

    # 5. Generate Analysis Summary
    Write-Host "`n📋 Analysis Summary:" -ForegroundColor Green
    Write-Host "=" * 30
    
    $totalLines = ($metrics | Measure-Object -Property Lines -Sum).Sum
    $totalClasses = ($metrics | Measure-Object -Property Classes -Sum).Sum
    $totalMethods = ($metrics | Measure-Object -Property Methods -Sum).Sum
    $avgMethodDensity = ($metrics | Measure-Object -Property MethodDensity -Average).Average
    
    Write-Host "📊 Total Lines of Code: $totalLines"
    Write-Host "🏗️  Total Classes: $totalClasses"
    Write-Host "⚙️  Total Methods: $totalMethods"
    Write-Host "📈 Average Method Density: $([math]::Round($avgMethodDensity, 3))"
    
    $largestFiles = $metrics | Sort-Object Lines -Descending | Select-Object -First 3
    Write-Host "`n🎯 Largest Files (refactor candidates):"
    $largestFiles | ForEach-Object { 
        Write-Host "  $($_.File): $($_.Lines) lines, $($_.Methods) methods" -ForegroundColor Yellow 
    }
    
    if (-not $SkipDependencies) {
        $highestCoupling = $dependencyReport | Sort-Object CoreDeps -Descending | Select-Object -First 3
        Write-Host "`n🔗 Highest Coupling:"
        $highestCoupling | ForEach-Object { 
            Write-Host "  $($_.File): $($_.CoreDeps) core dependencies" -ForegroundColor Magenta 
        }
    }

    Write-Host "`n✅ Analysis complete! Timestamp: $(Get-Date)" -ForegroundColor Green
    Write-Host "💡 Use this data to update the core analysis markdown files." -ForegroundColor Cyan

} catch {
    Write-Host "❌ Error during analysis: $_" -ForegroundColor Red
} finally {
    Pop-Location
}

Write-Host "`n🎯 Next Steps:" -ForegroundColor Yellow
Write-Host "1. Review the metrics and identify refactoring priorities"
Write-Host "2. Update core_method_inventory.md with current method signatures"
Write-Host "3. Update core_refactor_priority.md with complexity insights"
Write-Host "4. Consider creating architecture_health.md with these metrics"
