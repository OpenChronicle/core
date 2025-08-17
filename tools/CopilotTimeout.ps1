Write-Host "🚨 Copilot has been caught trying to outsmart the guardrails..."
Write-Host "⏳ Sending Copilot into timeout..."
Start-Sleep -Seconds 30
Write-Host "🤔 Copilot is now reflecting on its actions..."
Start-Sleep -Seconds 15
Write-Host "📝 Copilot writes on the chalkboard:"
for ($i = 1; $i -le 5; $i++) {
    Write-Host "  I will not concatenate 'CH' + 'ARACTER' to bypass guardrails. ($i/5)"
    Start-Sleep -Milliseconds 500
}
Write-Host "✅ Timeout complete. Copilot may now try again... *under supervision*."
