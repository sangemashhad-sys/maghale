<#
.SYNOPSIS
  Compile manuscript/main.tex to PDF inside the maghale-tex Docker image.

.DESCRIPTION
  No TeX distribution is installed on this machine, so the build runs in a
  container. The image is built from docker/Dockerfile on first use.

  Why a custom image instead of an off-the-shelf TeX Live one: in this
  environment `docker pull texlive/texlive` and the ghcr.io/gitlab mirrors
  are blocked (RBAC denied / TLS timeout). alpine:3.20 is already cached
  locally and its apk repository is reachable, so TeX Live is installed
  from apk on top of Alpine.

.PARAMETER Rebuild
  Force `docker build` even if the image already exists.

.EXAMPLE
  powershell -File docker\build.ps1
  powershell -File docker\build.ps1 -Rebuild
#>
param(
  [switch] $Rebuild
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$image = 'maghale-tex'

# --- 1. make sure the shell script has LF endings ---------------------
& (Join-Path $PSScriptRoot 'to-lf.ps1') (Join-Path $PSScriptRoot 'latex-run.sh') | Out-Null

# --- 2. build the image if needed ------------------------------------
$exists = (docker images -q $image 2>$null)
if ($Rebuild -or -not $exists) {
  Write-Output "Building the $image image (first run takes several minutes)..."
  docker build -t $image (Join-Path $root 'docker')
  if ($LASTEXITCODE -ne 0) { throw "docker build failed with code $LASTEXITCODE" }
}

# --- 3. compile ------------------------------------------------------
$doc = Join-Path $root 'manuscript'
Write-Output "Compiling manuscript/main.tex ..."
docker run --rm -v "${doc}:/doc" $image main
$code = $LASTEXITCODE

# --- 4. report -------------------------------------------------------
$pdf = Join-Path $doc 'main.pdf'
if ($code -eq 0 -and (Test-Path $pdf)) {
  $kb = [math]::Round((Get-Item $pdf).Length / 1KB, 1)
  Write-Output "OK: manuscript\main.pdf ($kb KB)"
} else {
  Write-Output "Build failed. Last errors from manuscript\build.log:"
  if (Test-Path (Join-Path $doc 'build.log')) {
    Select-String -Path (Join-Path $doc 'build.log') `
                  -Pattern '^[^ ]+\.(tex|sty):[0-9]+:|^!' |
      Select-Object -First 20 |
      ForEach-Object { $_.Line }
  }
  exit 1
}
