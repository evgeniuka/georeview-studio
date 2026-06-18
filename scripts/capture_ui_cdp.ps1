param(
  [int]$Width = 1440,
  [int]$Height = 1100,
  [string]$FileName = "v083_landing_1440x1100.png",
  [switch]$Mobile
)

$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $PSScriptRoot
$Url = "http://127.0.0.1:8847/"
$OutDir = Join-Path $ProjectDir "ui_review"
$OutPath = Join-Path $OutDir $FileName
$DebugPort = 9332
$UserDataDir = Join-Path $OutDir "chrome_profile_v083_9332"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
New-Item -ItemType Directory -Force -Path $UserDataDir | Out-Null

$browserCandidates = @(
  "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
  "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
  "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
  "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }

if (-not $browserCandidates) {
  throw "Chrome or Edge executable was not found for CDP screenshot capture."
}

$browser = $browserCandidates[0]
$args = @(
  "--headless=new",
  "--remote-debugging-port=$DebugPort",
  "--user-data-dir=$UserDataDir",
  "--disable-gpu",
  "--no-first-run",
  "--no-default-browser-check",
  "about:blank"
)
$process = Start-Process -FilePath $browser -ArgumentList $args -WindowStyle Hidden -PassThru

try {
  $deadline = (Get-Date).AddSeconds(15)
  do {
    Start-Sleep -Milliseconds 300
    $tcp = Get-NetTCPConnection -LocalPort $DebugPort -ErrorAction SilentlyContinue
  } while (-not $tcp -and (Get-Date) -lt $deadline)
  if (-not $tcp) {
    throw "CDP port $DebugPort did not open."
  }

  $encodedUrl = [uri]::EscapeDataString($Url)
  $target = Invoke-RestMethod -Method Put -Uri "http://127.0.0.1:$DebugPort/json/new?$encodedUrl"
  $ws = [System.Net.WebSockets.ClientWebSocket]::new()
  $ws.ConnectAsync([Uri]$target.webSocketDebuggerUrl, [Threading.CancellationToken]::None).GetAwaiter().GetResult() | Out-Null
  $script:NextId = 1

  function Receive-CdpMessage {
    $buffer = New-Object byte[] 1048576
    $stream = [System.IO.MemoryStream]::new()
    do {
      $segment = [System.ArraySegment[byte]]::new($buffer)
      $result = $ws.ReceiveAsync($segment, [Threading.CancellationToken]::None).GetAwaiter().GetResult()
      if ($result.MessageType -eq [System.Net.WebSockets.WebSocketMessageType]::Close) {
        throw "CDP websocket closed"
      }
      $stream.Write($buffer, 0, $result.Count)
    } while (-not $result.EndOfMessage)
    $text = [Text.Encoding]::UTF8.GetString($stream.ToArray())
    return $text | ConvertFrom-Json
  }

  function Send-CdpCommand {
    param(
      [string]$Method,
      [hashtable]$Params = @{}
    )
    $id = $script:NextId
    $script:NextId += 1
    $payload = @{ id = $id; method = $Method; params = $Params } | ConvertTo-Json -Depth 50 -Compress
    $bytes = [Text.Encoding]::UTF8.GetBytes($payload)
    $segment = [System.ArraySegment[byte]]::new($bytes)
    $ws.SendAsync($segment, [System.Net.WebSockets.WebSocketMessageType]::Text, $true, [Threading.CancellationToken]::None).GetAwaiter().GetResult() | Out-Null
    while ($true) {
      $message = Receive-CdpMessage
      if ($message.id -eq $id) {
        return $message
      }
    }
  }

  Send-CdpCommand "Page.enable" | Out-Null
  Send-CdpCommand "Runtime.enable" | Out-Null
  Send-CdpCommand "Emulation.setDeviceMetricsOverride" @{
    width = $Width
    height = $Height
    deviceScaleFactor = 1
    mobile = [bool]$Mobile
  } | Out-Null
  Send-CdpCommand "Page.navigate" @{ url = $Url } | Out-Null

  $expression = @'
(() => {
  const text = (id) => document.getElementById(id)?.textContent?.trim() || "";
  const box = (selector) => {
    const el = document.querySelector(selector);
    if (!el) return null;
    const rect = el.getBoundingClientRect();
    return { top: rect.top, left: rect.left, width: rect.width, height: rect.height };
  };
  const controls = document.getElementById("controlPanel");
  const advancedVisible = controls
    ? [...controls.querySelectorAll(".advanced-control")].filter((el) => getComputedStyle(el).display !== "none").length
    : -1;
  const table = box("#reviewQueuePanel");
  const detail = box("#candidatePanel");
  return {
    ready: text("overviewGeneratorCount") !== "--" && document.querySelectorAll("#candidateRows tr").length > 0 && document.querySelectorAll("#map circle").length > 0 && document.querySelector(".review-callout"),
    generatorCount: text("overviewGeneratorCount"),
    crossingCount: text("overviewCrossingCount"),
    majorRoadCount: text("overviewMajorRoadCount"),
    validationStatus: text("overviewValidationStatus"),
    candidateRows: document.querySelectorAll("#candidateRows tr").length,
    selectedRows: document.querySelectorAll("#candidateRows tr.selected-row").length,
    detailCallout: Boolean(document.querySelector(".review-callout")),
    mapCircles: document.querySelectorAll("#map circle").length,
    advancedVisible,
    scrollOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
    viewport: { width: innerWidth, height: innerHeight },
    tableDetailAligned: table && detail ? Math.abs(table.top - detail.top) < 28 : false,
    status: text("status")
  };
})()
'@

  $resultValue = $null
  $deadline = (Get-Date).AddSeconds(35)
  do {
    Start-Sleep -Milliseconds 700
    $result = Send-CdpCommand "Runtime.evaluate" @{
      expression = $expression
      returnByValue = $true
    }
    $resultValue = $result.result.result.value
  } while ((Get-Date) -lt $deadline -and -not $resultValue.ready)

  $capture = Send-CdpCommand "Page.captureScreenshot" @{
    format = "png"
    fromSurface = $true
    captureBeyondViewport = $false
  }
  [IO.File]::WriteAllBytes($OutPath, [Convert]::FromBase64String($capture.result.data))
  $ws.CloseAsync([System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure, "done", [Threading.CancellationToken]::None).GetAwaiter().GetResult() | Out-Null
  try { Invoke-RestMethod -Uri "http://127.0.0.1:$DebugPort/json/close/$($target.id)" | Out-Null } catch {}

  [pscustomobject]@{
    ok = [bool]$resultValue.ready
    screenshot = $OutPath
    dom = $resultValue
    bytes = (Get-Item -LiteralPath $OutPath).Length
  } | ConvertTo-Json -Depth 20
}
finally {
  if ($process -and -not $process.HasExited) {
    Stop-Process -Id $process.Id -Force
  }
}
