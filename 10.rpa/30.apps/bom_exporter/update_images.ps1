$filePath = "BOM_EXPORTER_USER_MANUAL.md"
$content = Get-Content $filePath -Raw -Encoding UTF8

# Markdown 이미지를 HTML img 태그로 변환 (경계선 포함)
$pattern = '!\[([^\]]+)\]\((images/[^\)]+)\)'
$replacement = '<img src="$2" alt="$1" style="border: 1px solid #ccc; padding: 5px; margin: 10px 0;">'

$newContent = $content -replace $pattern, $replacement

# UTF8 BOM 없이 저장
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($filePath, $newContent, $utf8NoBom)

Write-Host "✓ 이미지 경계선 추가 완료" -ForegroundColor Green
