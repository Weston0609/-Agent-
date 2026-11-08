$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$src    = "E:\，软件落地\AI工程全景手册.new.docx"
$outDir = "E:\，软件落地\_doc\preview"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
$doc = $word.Documents.Open($src, $false, $true)

$pages = @(4, 5, 6)
foreach ($n in $pages) {
    $s = $doc.GoTo(1, 1, $n).Start
    $e = $doc.GoTo(1, 1, ($n + 1)).Start
    $rng = $doc.Range($s, $e)
    $rng.CopyAsPicture()
    Start-Sleep -Milliseconds 1500
    $img = [System.Windows.Forms.Clipboard]::GetImage()
    if ($img) {
        $out = Join-Path $outDir ("p{0:D3}.png" -f $n)
        $img.Save($out, [System.Drawing.Imaging.ImageFormat]::Png)
        Write-Output ("saved {0} {1}x{2}" -f $out, $img.Width, $img.Height)
        $img.Dispose()
    } else {
        Write-Output ("page {0}: clipboard empty" -f $n)
    }
}

$doc.Close($false)
$word.Quit()
