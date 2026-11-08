
$ErrorActionPreference = "Stop"
$src = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\AI工程全景手册.new.docx"))
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
$doc = $word.Documents.Open($src, $false, $true)
$doc.Repaginate()
$targets = @("这本书写给三类人", "不会写代码，但要用 AI 做成事", "全书完", "前言")
foreach ($tg in $targets) {
    $find = $doc.Content.Find
    $find.Text = $tg
    $find.Forward = $true
    $find.Wrap = 0
    if ($find.Execute()) {
        Write-Output ("{0} -> page {1}" -f $tg, $find.Parent.Information(3))
    } else {
        Write-Output ("{0} -> not found" -f $tg)
    }
}
$doc.Close($false)
try { $word.Quit() } catch {}
