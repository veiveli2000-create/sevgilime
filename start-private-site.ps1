$ErrorActionPreference = "Stop"

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
$pythonPath = $null
if ($pythonCommand -and $pythonCommand.Source -notmatch "\\WindowsApps\\python\.exe$") {
  $pythonPath = $pythonCommand.Source
}

if (-not $pythonPath) {
  $pythonRoot = Join-Path $env:LOCALAPPDATA "Programs\Python"
  if (Test-Path $pythonRoot) {
    $pythonPath = Get-ChildItem $pythonRoot -Filter python.exe -Recurse -ErrorAction SilentlyContinue |
      Sort-Object FullName -Descending |
      Select-Object -First 1 -ExpandProperty FullName
  }
}

if (-not $pythonPath) {
  throw "Python 3 is required. Install it from python.org, then run this script again."
}

$cloudflaredCommand = Get-Command cloudflared -ErrorAction SilentlyContinue
$cloudflaredPath = $null
if ($cloudflaredCommand) {
  $cloudflaredPath = $cloudflaredCommand.Source
} else {
  $wingetPackages = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages"
  if (Test-Path $wingetPackages) {
    $cloudflaredPath = Get-ChildItem $wingetPackages -Filter cloudflared.exe -Recurse -ErrorAction SilentlyContinue |
      Select-Object -First 1 -ExpandProperty FullName
  }
}

if (-not $cloudflaredPath) {
  throw "Cloudflare Tunnel (cloudflared) is required. Install it, then run this script again."
}

$securePassword = Read-Host "Enter a unique password (at least 16 characters); share it with Esra separately" -AsSecureString
$passwordPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
$serverProcess = $null

try {
  $password = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($passwordPointer)
  if ($password.Length -lt 16) {
    throw "The password must contain at least 16 characters."
  }

  $env:ESRA_SITE_PASSWORD = $password
  $serverScript = Join-Path $PSScriptRoot "private_server.py"
  $serverProcess = Start-Process -FilePath $pythonPath -ArgumentList ('-u "' + $serverScript + '"') -PassThru -NoNewWindow
  Remove-Item Env:\ESRA_SITE_PASSWORD
  $password = $null

  $ready = $false
  for ($attempt = 0; $attempt -lt 15; $attempt++) {
    if ($serverProcess.HasExited) {
      throw "The local site server stopped unexpectedly."
    }

    try {
      $request = [System.Net.HttpWebRequest]::Create("http://127.0.0.1:8787/")
      $request.Timeout = 1000
      $request.GetResponse().Close()
    } catch [System.Net.WebException] {
      if ($_.Exception.Response -and [int]$_.Exception.Response.StatusCode -eq 401) {
        $ready = $true
        break
      }
    }

    Start-Sleep -Seconds 1
  }

  if (-not $ready) {
    throw "The password-protected local server did not become ready."
  }

  Write-Host "The site files remain on this computer. Press Ctrl+C to stop the server and tunnel."
  & $cloudflaredPath tunnel --url http://127.0.0.1:8787
} finally {
  if ($serverProcess -and -not $serverProcess.HasExited) {
    Stop-Process -Id $serverProcess.Id
  }

  Remove-Item Env:\ESRA_SITE_PASSWORD -ErrorAction SilentlyContinue
  [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordPointer)
}
