$ErrorActionPreference = 'Stop'

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$patchFile = Join-Path $projectRoot 'patches/ea31337-metaeditor-compat.patch'

$expected = @(
    @{ Path = 'third_party/EA31337'; Commit = '9b9bd38c4e49dd6916f4fe3936e50e97fca7a692' },
    @{ Path = 'third_party/EA31337/src/include/classes'; Commit = '35a2814b2543987e3dc33b6ede70e864160df3c1' },
    @{ Path = 'third_party/EA31337/src/strategies'; Commit = '3da76f4bd8d5e8a53a348c525486fd1430de82f2' },
    @{ Path = 'third_party/EA31337/src/strategies/Retracement'; Commit = '40eff0a36d1a0833ce566eaa7047ec98d68ba93b' }
)

foreach ($item in $expected) {
    $path = Join-Path $projectRoot $item.Path
    if (-not (Test-Path -LiteralPath (Join-Path $path '.git'))) {
        throw "EA31337 submodule belum tersedia: $($item.Path). Jalankan git submodule update --init --recursive."
    }

    $actual = (& git -C $path rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0 -or $actual -ne $item.Commit) {
        throw "Versi EA31337 tidak sesuai patch: $($item.Path) pada $actual. Patch dikunci ke $($item.Commit)."
    }
}

$previousPreference = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
$reverseOutput = & git -C $projectRoot apply --reverse --check $patchFile 2>&1
$reverseExitCode = $LASTEXITCODE
$ErrorActionPreference = $previousPreference
if ($reverseExitCode -eq 0) {
    Write-Output 'Patch EA31337 sudah diterapkan.'
    exit 0
}

$ErrorActionPreference = 'Continue'
$checkOutput = & git -C $projectRoot apply --check $patchFile 2>&1
$checkExitCode = $LASTEXITCODE
$ErrorActionPreference = $previousPreference
if ($checkExitCode -ne 0) {
    throw "Patch tidak cocok dengan source EA31337 yang ada; tidak ada file yang diubah. $($checkOutput -join [Environment]::NewLine)"
}

& git -C $projectRoot apply $patchFile
if ($LASTEXITCODE -ne 0) {
    throw 'Penerapan patch gagal.'
}

Write-Output 'Patch kompatibilitas MetaEditor sudah diterapkan.'
