# One line from nothing to ready, Windows PowerShell:
#
#   irm https://raw.githubusercontent.com/yuvi-ex/munich-mobility-agents/main/get.ps1 | iex
#
# Clones the repo and calls install.py (one implementation for every platform).
# NOTE: this file must not carry a UTF-8 BOM; it is executed through irm | iex.
$ErrorActionPreference = "Stop"
$Repo = if ($env:MUNICH_AGENTS_REPO) { $env:MUNICH_AGENTS_REPO } else { "https://github.com/yuvi-ex/munich-mobility-agents" }
$Dest = if ($env:MUNICH_AGENTS_DIR)  { $env:MUNICH_AGENTS_DIR }  else { Join-Path $HOME "munich-mobility-agents" }

$Py = $null
foreach ($candidate in @("python3", "python", "py")) {
    $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
    if (-not $cmd) { continue }
    try {
        $major = & $cmd.Source -c "import sys; print(sys.version_info[0])" 2>$null
        if ("$major".Trim() -eq "3") { $Py = $cmd.Source; break }
    } catch { }
}
if (-not $Py) { throw "Python 3 is required but no working interpreter was found on PATH (tried python3, python, py). The Microsoft Store stub does not count." }
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw "git is required but was not found on PATH." }

if (Test-Path (Join-Path $Dest ".git")) {
    Write-Host -NoNewline "Updating $(Split-Path $Dest -Leaf) ... "
    git -C $Dest pull --quiet --ff-only 2>$null | Out-Null
    Write-Host "done"
} else {
    Write-Host -NoNewline "Cloning $(Split-Path $Dest -Leaf) ... "
    git clone --quiet $Repo $Dest
    Write-Host "done"
}
& $Py (Join-Path $Dest "install.py") @args
exit $LASTEXITCODE
