# RCM / RIFT-to-Windows log feasibility pilot (Windows PowerShell 5.1+ / PS7).
# Calls LuaPadModern's existing read-only Node watcher; does not duplicate its
# file-tail implementation or change game input/logging configuration.
[CmdletBinding()]
param(
    [string]$Nonce = ("RCM" + [DateTimeOffset]::UtcNow.ToString("yyyyMMddHHmmss")),
    [ValidateRange(1, 300)][int]$TimeoutSeconds = 120,
    [ValidateRange(25, 1000)][int]$PollMs = 100,
    [string]$LogPath,
    [switch]$Preview
)

$ErrorActionPreference = "Stop"
try {
    if ($Nonce -cnotmatch '^[A-Za-z0-9_-]{8,80}$') {
        throw "Nonce must be 8-80 ASCII letters, digits, underscore or hyphen."
    }
    $workspace = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
    $watcher = Join-Path $workspace "LuaPadModern\tools\rift-log-probe.cjs"
    if (-not (Test-Path -LiteralPath $watcher -PathType Leaf)) {
        throw "LuaPadModern watcher not found at $watcher. Nothing was started."
    }
    $node = Get-Command node.exe -ErrorAction Stop
    if ($LogPath) {
        $isAbsolute = ($LogPath -match '^[A-Za-z]:\\' -or
            $LogPath -match '^\\\\[^\\]+\\[^\\]+\\')
        if (-not $isAbsolute -or
            [System.IO.Path]::GetFileName($LogPath) -ine 'Log.txt') {
            throw "LogPath must be an absolute path whose filename is Log.txt."
        }
    }
    $argsList = @($watcher, '--nonce', $Nonce, '--timeout-ms',
        [string]($TimeoutSeconds * 1000), '--poll-ms', [string]$PollMs)
    if ($LogPath) { $argsList += @('--path', $LogPath) }
    [ordered]@{
        event              = $(if ($Preview) { 'preview' } else { 'watcher_starting' })
        host               = $env:COMPUTERNAME
        watcher            = $watcher
        watcherReadOnly    = $true
        gameInputSent      = $false
        loggingChanged     = $false
        transportVerified  = $false
        nonce              = $Nonce
        rcmEditorCommand   = ":logprobe $Nonce"
        timeoutSeconds     = $TimeoutSeconds
        pollMs             = $PollMs
        logPath            = $(if ($LogPath) { $LogPath } else { 'LuaPadModern default candidates' })
        instruction        = 'After the watcher starts, enter rcmEditorCommand in the loaded RCM editor. Enable /log manually only after confirming its existing state; /log is a toggle.'
        note               = 'The watcher also prints a LuaPad snippet. For this RCM test use :logprobe, not the LuaPad snippet. A console submission alone is NOT a log receipt.'
    } | ConvertTo-Json -Compress
    if ($Preview) { exit 0 }
    & $node.Source @argsList
    exit $LASTEXITCODE
}
catch {
    Write-Error ("RCM log probe did not start: " + $_.Exception.Message)
    exit 1
}
