# 全流程：构建 docx → 刷新目录域 → 导出 PDF → 渲染样张
# 注意：本机 Word.Application ProgID 实际由 WPS 提供，退出后必须清理残留进程，否则文件被锁。
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$docx = Join-Path $root "AI工程全景手册.docx"
$pdf  = Join-Path $PSScriptRoot "preview_a.pdf"
$py   = "E:\DSH\DSH Desktop\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"

function Clear-Office {
    Get-Process wps, wpp, et, WINWORD -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 900
    Get-ChildItem $root -Force -Filter "~`$*" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
}

Clear-Office
& $py (Join-Path $PSScriptRoot "build.py")
if ($LASTEXITCODE -ne 0) { throw "build.py failed" }
Start-Sleep -Seconds 2
Write-Output ("docx exists=" + (Test-Path $docx) + " size=" + (Get-Item $docx).Length)

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $null
    for ($i = 1; $i -le 5; $i++) {
        try { $doc = $word.Documents.Open($docx, $false, $false); break }
        catch { Write-Output ("open retry $i : " + $_.Exception.Message); Start-Sleep -Seconds 3 }
    }
    if ($null -eq $doc) { throw "cannot open docx" }
    $doc.Fields.Update() | Out-Null
    foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
    $doc.Repaginate()
    Write-Output ("pages=" + $doc.ComputeStatistics(2))
    $doc.Save()
    if (Test-Path $pdf) { Remove-Item $pdf -Force }
    $doc.ExportAsFixedFormat($pdf, 17)
    Write-Output ("pdf=" + (Get-Item $pdf).Length)
    $doc.Close($false)
} finally {
    try { $word.Quit() } catch {}
    Clear-Office
}
Write-Output "OK"
