# build.ps1 - builds tools\mfc_golden\build\mfc_golden.exe
# Run from PowerShell (not from Bash). reference\mfc is compiled as is.

$ErrorActionPreference = 'Stop'

$here = $PSScriptRoot
$root = Resolve-Path (Join-Path $here '..\..')
$buildDir = Join-Path $here 'build'

# vswhere.exe is not on PATH
$vswhere = 'C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe'
if (-not (Test-Path $vswhere)) { throw "vswhere.exe not found: $vswhere" }
$vs = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vs) { throw 'Visual Studio with the C++ x64 tools was not found' }
$vcvars = Join-Path $vs 'VC\Auxiliary\Build\vcvars64.bat'
if (-not (Test-Path $vcvars)) { throw "vcvars64.bat not found: $vcvars" }

New-Item -ItemType Directory -Force $buildDir | Out-Null

$sources = @(
    (Join-Path $here 'golden_main.cpp'),
    (Join-Path $root 'reference\mfc\CanSim\LogAnalysis.cpp')
)
# /fp:precise (the default) is kept: no /fp:fast or /arch:AVX2 (research.md R-4)
$cl = @(
    'cl', '/nologo', '/std:c++17', '/EHsc', '/O2', '/utf-8', '/W4',
    "/I`"$here`"", "/I`"$(Join-Path $root 'reference\mfc\CanSim')`""
) + ($sources | ForEach-Object { "`"$_`"" }) + @(
    "/Fo`"$buildDir\\`"", "/Fe`"$(Join-Path $buildDir 'mfc_golden.exe')`""
)
$cl = $cl -join ' '

# vcvars64.bat calls vswhere.exe through PATH too
$env:PATH = "$(Split-Path $vswhere);$env:PATH"
# vcvars only sets the environment of its own cmd, so cl runs in the same cmd /c.
# Compiler messages on stderr must not stop the script; the exit code decides.
$ErrorActionPreference = 'Continue'
cmd /c "`"$vcvars`" >nul && $cl 2>&1"
$code = $LASTEXITCODE
$ErrorActionPreference = 'Stop'
if ($code -ne 0) { throw "build failed ($code)" }
Write-Host "built $(Join-Path $buildDir 'mfc_golden.exe')"
