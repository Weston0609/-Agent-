
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$src  = Join-Path $root "AI工程全景手册.docx"
$pdf  = Join-Path $PSScriptRoot "preview_a.pdf"
if (Test-Path $pdf) { Remove-Item $pdf -Force }

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
$doc = $word.Documents.Open($src, $false, $true)
try {
  $doc.ExportAsFixedFormat($pdf, 17)
  Write-Output "export-as-fixed OK"
} catch {
  Write-Output ("export failed: " + $_.Exception.Message)
  try {
    $doc.SaveAs2($pdf, 17)
    Write-Output "saveas2 OK"
  } catch {
    Write-Output ("saveas2 failed: " + $_.Exception.Message)
  }
}
$doc.Close($false)
try { $word.Quit() } catch {}
if (Test-Path $pdf) { Write-Output ("pdf bytes=" + (Get-Item $pdf).Length) } else { Write-Output "no pdf" }
