$ErrorActionPreference = "Stop"
$src = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\AI工程全景手册.new.docx"))

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
$doc = $word.Documents.Open($src, $false, $true)
$doc.Repaginate()

$targets = @("这本书写给三类人", "第 1 章", "先把地基打穿", "全书完")
$i = 0
foreach ($p in $doc.Paragraphs) {
    $i++
    $t = $p.Range.Text.Trim()
    if ($t.Length -eq 0) { continue }
    foreach ($tg in $targets) {
        if ($t.Contains($tg)) {
            Write-Output ("[{0}] page={1} :: {2}" -f $i, $p.Range.Information(3), $t.Substring(0, [Math]::Min(40, $t.Length)))
        }
    }
}
$doc.Close($false)
try { $word.Quit() } catch {}
