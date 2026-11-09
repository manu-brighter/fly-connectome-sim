#requires -Version 7.0
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string] $OutputDirectory,
    [Parameter(Mandatory)][string] $EvidenceDirectory,
    [Parameter(Mandatory)][ValidatePattern('^[a-f0-9]{64}$')][string] $ExpectedProtocolSha256,
    [ValidatePattern('^[a-f0-9]{64}$')][string] $ExpectedReadinessSha256,
    [Parameter(Mandatory)][ValidateSet('Prepare', 'Run')][string] $Mode
)

$ErrorActionPreference = 'Stop'
if (-not $IsWindows) { throw 'Market supervision requires Windows.' }
if ($Mode -eq 'Run' -and -not $ExpectedReadinessSha256) { throw 'Run requires ExpectedReadinessSha256.' }
$workspace = Split-Path -Parent $PSScriptRoot
$python = Join-Path $workspace '.venv/Scripts/python.exe'
$helper = Join-Path $PSScriptRoot 'live_buffer_supervision.py'
$ownerCreated = (Get-Process -Id $PID).StartTime.ToUniversalTime().ToFileTimeUtc()
$start = [System.Diagnostics.ProcessStartInfo]::new()
$start.FileName = $python
$start.WorkingDirectory = $workspace
$start.UseShellExecute = $false
$start.CreateNoWindow = $true
$start.RedirectStandardOutput = $true
$start.RedirectStandardError = $true
foreach ($argument in @($helper, '--mode', $Mode, '--output-directory', $OutputDirectory,
    '--evidence-directory', $EvidenceDirectory, '--expected-protocol-sha256', $ExpectedProtocolSha256,
    '--owner-pid', "$PID", '--owner-created', "$ownerCreated")) {
    $start.ArgumentList.Add($argument)
}
if ($ExpectedReadinessSha256) {
    $start.ArgumentList.Add('--expected-readiness-sha256')
    $start.ArgumentList.Add($ExpectedReadinessSha256)
}
$process = [System.Diagnostics.Process]::new()
$process.StartInfo = $start
$actualSupervisor = $null
try {
    if (-not $process.Start()) { throw 'Supervisor start failed.' }
    $stdout = $process.StandardOutput.ReadToEndAsync()
    $stderr = $process.StandardError.ReadToEndAsync()
    $readyPath = Join-Path $EvidenceDirectory 'supervisor-ready.json'
    while (-not $process.WaitForExit(100)) {
        if ($Mode -eq 'Run' -and -not $actualSupervisor -and (Test-Path -LiteralPath $readyPath)) {
            $readyText = [System.IO.File]::ReadAllText($readyPath)
            $ready = $readyText | ConvertFrom-Json
            $candidate = $null
            try {
                $candidate = [System.Diagnostics.Process]::GetProcessById($ready.pid)
                # Hold a candidate without granting cleanup authority over it.
                $null = $candidate.Handle
                $workerHome = ((Get-Content -LiteralPath (Join-Path $workspace '.venv/pyvenv.cfg')) |
                    Where-Object { $_ -like 'home = *' }) -replace '^home = ', ''
                $expectedExecutable = [System.IO.Path]::GetFullPath((Join-Path $workerHome 'python.exe'))
                if ($candidate.StartTime.ToUniversalTime().ToFileTimeUtc() -ne $ready.creation_time_100ns -or
                    $candidate.MainModule.FileName -ne $expectedExecutable -or
                    $ready.owner.pid -ne $PID -or $ready.owner.creation_time_100ns -ne $ownerCreated -or
                    $ready.protocol_sha256 -ne $ExpectedProtocolSha256 -or
                    $ready.readiness_sha256 -ne $ExpectedReadinessSha256) {
                    throw 'Actual supervisor PID/start/executable/owner/hash identity differs.'
                }
                # OS ancestry must reach the exact held launched process. Hold
                # each live ancestor and check birth ordering to reject PID reuse.
                $ancestor = $candidate
                $ancestors = [System.Collections.Generic.List[System.Diagnostics.Process]]::new()
                $seen = [System.Collections.Generic.HashSet[int]]::new()
                try {
                    while ($ancestor.Id -ne $process.Id) {
                        if ($ancestors.Count -ge 32 -or -not $seen.Add($ancestor.Id) -or $ancestor.HasExited) {
                            throw 'Actual supervisor OS ancestry is unavailable or cyclic.'
                        }
                        $entry = Get-CimInstance -ClassName Win32_Process -Filter "ProcessId = $($ancestor.Id)" -ErrorAction Stop
                        if (-not $entry -or $entry.ParentProcessId -le 0) {
                            throw 'Actual supervisor OS ancestry is unavailable.'
                        }
                        $parent = if ($entry.ParentProcessId -eq $process.Id) { $process } else {
                            $heldParent = [System.Diagnostics.Process]::GetProcessById($entry.ParentProcessId)
                            $null = $heldParent.Handle
                            $ancestors.Add($heldParent)
                            $heldParent
                        }
                        if ($parent.HasExited -or $ancestor.HasExited -or
                            $ancestor.StartTime.ToUniversalTime().ToFileTimeUtc() -lt $parent.StartTime.ToUniversalTime().ToFileTimeUtc()) {
                            throw 'Actual supervisor OS ancestry/start identity differs.'
                        }
                        $ancestor = $parent
                    }
                } finally {
                    foreach ($ancestorHandle in $ancestors) { $ancestorHandle.Dispose() }
                }
                $actualSupervisor = $candidate
                $candidate = $null
            } finally {
                # Invalid or unrelated candidates are never termination targets.
                if ($candidate) { $candidate.Dispose() }
            }
            $ackPath = Join-Path $EvidenceDirectory 'supervisor-ack.json'
            $temporaryAck = Join-Path $EvidenceDirectory ('.supervisor-ack.' + [guid]::NewGuid().ToString('N') + '.tmp')
            [System.IO.File]::WriteAllText($temporaryAck, $readyText, [System.Text.UTF8Encoding]::new($false))
            [System.IO.File]::Move($temporaryAck, $ackPath, $false)
        }
    }
    [Console]::Out.Write($stdout.GetAwaiter().GetResult())
    [Console]::Error.Write($stderr.GetAwaiter().GetResult())
    $exitCode = $process.ExitCode
} finally {
    # Signal while PS still lives; wait bounded for the actual helper to close
    # its job before forced termination. Abrupt PS death is watched independently.
    if ($process.Id -and -not $process.HasExited) {
        $cancelPath = Join-Path $EvidenceDirectory 'cancel.signal'
        $cancelFailed = $false
        if ($Mode -eq 'Run' -and (Test-Path -LiteralPath $cancelPath)) {
            $signal = $null
            $locked = $false
            try {
                # Never create or grow evidence during late frontend cleanup.
                # Share the helper's Windows byte-range lock and terminal state.
                $signal = [System.IO.FileStream]::new($cancelPath, [System.IO.FileMode]::Open,
                    [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::ReadWrite)
                if ($signal.Length -ne 1) { throw 'Invalid fixed-size cancellation signal.' }
                $lockWait = [System.Diagnostics.Stopwatch]::StartNew()
                while (-not $locked) {
                    try { $signal.Lock(0, 1); $locked = $true } catch [System.IO.IOException] {
                        if ($lockWait.ElapsedMilliseconds -ge 1000) { throw }
                        [System.Threading.Thread]::Sleep(10)
                    }
                }
                $state = $signal.ReadByte()
                if ($state -eq 48) {
                    $signal.Position = 0
                    $signal.WriteByte(49)
                    $signal.Flush($true)
                } elseif ($state -ne 49 -and $state -ne 50) {
                    throw 'Invalid cancellation signal state.'
                }
            } catch {
                $cancelFailed = $true
                [Console]::Error.WriteLine('Cancellation channel failed: ' + $_.Exception.Message)
            } finally {
                if ($locked) { $signal.Unlock(0, 1) }
                if ($signal) { $signal.Dispose() }
            }
        } elseif ($actualSupervisor) {
            $cancelFailed = $true
        }
        if ($actualSupervisor -and ($cancelFailed -or -not $actualSupervisor.WaitForExit(3000))) {
            $actualSupervisor.Kill()
            $null = $actualSupervisor.WaitForExit(1000)
        }
        if (-not $process.WaitForExit(1000)) {
            $process.Kill($true)
            $null = $process.WaitForExit(1000)
        }
    }
    if ($actualSupervisor) { $actualSupervisor.Dispose() }
    $process.Dispose()
}
exit $exitCode
