
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$src  = Join-Path $root "AI工程全景手册.docx"
$pdf  = Join-Path $PSScriptRoot "preview_a.pdf"

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
$doc = $word.Documents.Open($src, $false, $false)
$doc.Fields.Update() | Out-Null
foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
$doc.Repaginate()
Write-Output ("pages=" + $doc.ComputeStatistics(2))
$doc.Save()
Write-Output "saved-docx"
if (Test-Path $pdf) { Remove-Item $pdf -Force }
$doc.SaveAs([ref]$pdf, [ref]17)
Write-Output "saved-pdf"
$doc.Close($false)
try { $word.Quit() } catch {}
Write-Output "done"
