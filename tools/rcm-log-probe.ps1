# RCM / RIFT-to-Windows log feasibility pilot (Windows PowerShell 5.1+ / PS7).
# Calls RCM's configured-path chat observer, which reuses LuaPadModern's
# read-only file tailer. No game input or logging configuration changes.
[CmdletBinding()]
param(
    [string]$Nonce = ("RCM" + [DateTimeOffset]::UtcNow.ToString("yyyyMMddHHmmss")),
    [ValidateRange(1, 300)][int]$TimeoutSeconds = 120,
    [ValidateRange(25, 1000)][int]$PollMs = 100,
    [string]$LogPath,
    [ValidateRange(0, 30)][int]$SampleRawLines = 0,
    [switch]$RequireChatAfterMarker,
    [ValidatePattern('^[A-Za-z0-9_-]{8,80}$')][string]$RequireChatText,
    [switch]$PrepareImport,
    [ValidateSet('native','editor')][string]$InputMode = 'native',
    [switch]$Preview
)

$ErrorActionPreference = "Stop"
try {
    if ($Nonce -cnotmatch '^[A-Za-z0-9_-]{8,80}$') {
        throw "Nonce must be 8-80 ASCII letters, digits, underscore or hyphen."
    }
    if ($RequireChatText -and -not $RequireChatAfterMarker) {
        throw "RequireChatText requires RequireChatAfterMarker."
    }
    if ($PSBoundParameters.ContainsKey("InputMode") -and -not $PrepareImport) {
        throw "InputMode requires explicit PrepareImport."
    }
    $workspace = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
    $watcher = Join-Path $PSScriptRoot "rcm-chat-observer.cjs"
    $decoder = Join-Path $workspace "LuaPadModern\tools\rift-log-probe.cjs"
    if (-not (Test-Path -LiteralPath $watcher -PathType Leaf)) {
        throw "RCM chat observer not found at $watcher. Nothing was started."
    }
    if (-not (Test-Path -LiteralPath $decoder -PathType Leaf)) {
        throw "Required LuaPadModern read-only decoder not found at $decoder. Nothing was started."
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
    if ($SampleRawLines -gt 0) { $argsList += @('--sample-raw-lines', [string]$SampleRawLines) }
    if ($RequireChatAfterMarker) { $argsList += '--require-chat-after-marker' }
    if ($RequireChatText) { $argsList += @('--require-chat-text', $RequireChatText) }
    if ($PrepareImport) { $argsList += @('--prepare-import', '--input-mode', $InputMode) }
    [ordered]@{
        event              = $(if ($Preview) { 'preview' } else { 'watcher_starting' })
        host               = $env:COMPUTERNAME
        watcher            = $watcher
        decoderDependency  = $decoder
        watcherReadOnly    = $true
        gameInputSent      = $false
        loggingChanged     = $false
        transportVerified  = $false
        nonce              = $Nonce
        rcmEditorCommand   = ":logprobe $Nonce"
        timeoutSeconds     = $TimeoutSeconds
        pollMs             = $PollMs
        rawSampleLines     = $SampleRawLines
        requireChatAfterMarker = [bool]$RequireChatAfterMarker
        expectedChatTextRequired = [bool]$RequireChatText
        prepareImport      = [bool]$PrepareImport
        inputMode          = $(if ($PrepareImport) { $InputMode } else { 'not_requested' })
        logPath            = $(if ($LogPath) { $LogPath } else { 'resolved at runtime by RCM observer' })
        pathSelectionPolicy = $(if ($LogPath) { 'explicit LogPath' } else { 'Rift.cfg [Client] DocumentsDirectory first; LuaPad fallback only if missing/invalid' })
        instruction        = $(if ($RequireChatText) { 'Wait for started, enter rcmEditorCommand in RCM, then wait for chat_phase_armed. Only then send exactly the test text supplied via RequireChatText in original RIFT chat. Other chat lines will not complete this check. Check /log state first; it is a toggle.' } elseif ($RequireChatAfterMarker) { 'Wait for started, then enter rcmEditorCommand in RCM. ONLY after chat_phase_armed appears, send one NEW native player chat line; messages before this receipt do not count. First confirm /log state; it is a toggle.' } else { 'After started, enter rcmEditorCommand in the loaded RCM editor. Enable /log manually only after confirming its existing state; /log is a toggle.' })
        note               = $(if ($PrepareImport) { 'Preparing import commands is explicit opt-in and can expose encoded chat text. Generated commands require manual entry in RCM editor or native chat; no keyboard/game input is sent. Check started.pathSelection; a marker is not chat proof.' } else { 'RCM observer reuses the LuaPad decoder. Check started.pathSelection. The console marker alone is NOT a verified log receipt or social-chat capture. Raw-line samples can include private chat, so enable explicitly.' })
    } | ConvertTo-Json -Compress
    if ($Preview) { exit 0 }
    & $node.Source @argsList
    exit $LASTEXITCODE
}
catch {
    Write-Error ("RCM log probe did not start: " + $_.Exception.Message)
    exit 1
}
