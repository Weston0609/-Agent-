
$ErrorActionPreference = "Stop"
$src = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\AI工程全景手册.new.docx"))
$pdf = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "preview_a.pdf"))

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
$doc = $word.Documents.Open($src, $false, $false)
$doc.Fields.Update() | Out-Null
foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
$doc.Repaginate()
Write-Output ("pages=" + $doc.ComputeStatistics(2))

$find = $doc.Content.Find
$find.Text = "这本书写给三类人"
$find.Forward = $true
$find.Wrap = 0
if ($find.Execute()) { Write-Output ("preface page=" + $find.Parent.Information(3)) }

if (Test-Path $pdf) { Remove-Item $pdf -Force }
$doc.SaveAs([ref]$pdf, [ref]17)
$doc.Close($false)
try { $word.Quit() } catch {}
Write-Output "done"
