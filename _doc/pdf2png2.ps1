$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Runtime.WindowsRuntime

$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
  $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
  $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
})[0]
$asTaskAction = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
  $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
  $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncAction'
})[0]

function Await($op, $t) {
  $task = $asTaskGeneric.MakeGenericMethod($t).Invoke($null, @($op))
  $task.Wait(-1) | Out-Null
  $task.Result
}
function AwaitAction($op) {
  $task = $asTaskAction.Invoke($null, @($op))
  $task.Wait(-1) | Out-Null
}

$null = [Windows.Data.Pdf.PdfDocument, Windows.Data.Pdf, ContentType=WindowsRuntime]
$null = [Windows.Storage.Streams.InMemoryRandomAccessStream, Windows.Storage.Streams, ContentType=WindowsRuntime]
$null = [Windows.Storage.Streams.DataWriter, Windows.Storage.Streams, ContentType=WindowsRuntime]

$pdfPath = Join-Path $PSScriptRoot "preview_a.pdf"
$outDir  = Join-Path $PSScriptRoot "preview"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$bytes = [System.IO.File]::ReadAllBytes($pdfPath)
$stream = New-Object Windows.Storage.Streams.InMemoryRandomAccessStream
$writer = New-Object Windows.Storage.Streams.DataWriter($stream)
$writer.WriteBytes($bytes)
Await ($writer.StoreAsync()) ([uint32]) | Out-Null
Await ($writer.FlushAsync()) ([bool]) | Out-Null
$writer.DetachStream() | Out-Null
$stream.Seek(0)

$doc = Await ([Windows.Data.Pdf.PdfDocument]::LoadFromStreamAsync($stream)) ([Windows.Data.Pdf.PdfDocument])
Write-Output ("pagecount=" + $doc.PageCount)

foreach ($n in @(13, 14, 30, 52)) {
  $page = $doc.GetPage($n - 1)
  $s = New-Object Windows.Storage.Streams.InMemoryRandomAccessStream
  $opts = New-Object Windows.Data.Pdf.PdfPageRenderOptions
  $opts.DestinationWidth = [uint32]1500
  AwaitAction ($page.RenderToStreamAsync($s, $opts))
  $size = [uint32]$s.Size
  $reader = New-Object Windows.Storage.Streams.DataReader($s.GetInputStreamAt(0))
  Await ($reader.LoadAsync($size)) ([uint32]) | Out-Null
  $buf = New-Object byte[] $size
  $reader.ReadBytes($buf)
  $out = Join-Path $outDir ("p{0:D3}.png" -f $n)
  [System.IO.File]::WriteAllBytes($out, $buf)
  Write-Output ("saved $out " + $size)
  $reader.Dispose(); $s.Dispose(); $page.Dispose()
}
