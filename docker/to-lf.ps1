<#
.SYNOPSIS
  Rewrite text files in place with LF line endings and no BOM.

.DESCRIPTION
  Shell scripts that are mounted into a Linux container must use LF endings;
  a CRLF file makes /bin/sh fail with errors such as
  "set: illegal option -". The editor tool writes CRLF on Windows, so every
  .sh file under this project has to pass through this script once.

.EXAMPLE
  powershell -File docker\to-lf.ps1 docker\probe-pkgs.sh docker\build-pdf.sh
#>
param(
  [Parameter(Mandatory = $true, ValueFromRemainingArguments = $true)]
  [string[]] $Path
)

$enc = New-Object System.Text.UTF8Encoding $false   # UTF-8, no BOM

foreach ($p in $Path) {
  $full = (Resolve-Path -LiteralPath $p).ProviderPath
  $text = [System.IO.File]::ReadAllText($full)
  $text = $text -replace "`r`n", "`n"
  [System.IO.File]::WriteAllText($full, $text, $enc)
  Write-Output "LF: $full"
}
