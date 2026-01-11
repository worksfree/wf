$path = 'D:\drive_files\10.worksfree\10.rpa\50.data\vba\excel_save_as.vba'
$code = @'
' Module1 (표준 모듈)
Option Explicit

' 버튼에 연결해서 쓰는 매크로
Public Sub SaveSelfAndTimestampCopy()
    SaveWorkbookAndCopyWithTimestamp ThisWorkbook
End Sub

' 핵심 로직: 현재 통합문서를 저장하고, 동일한 이름 + 타임스탬프 접미어로 사본 저장
Public Sub SaveWorkbookAndCopyWithTimestamp(ByVal wb As Workbook)
    Dim prevEvents As Boolean: prevEvents = Application.EnableEvents
    Application.EnableEvents = False
    On Error GoTo CleanUp

    ' 1) 현재 파일 저장 (처음 저장 전이면 저장 위치 받음)
    If Len(wb.Path) = 0 Then
        Dim saveName As Variant
        Dim defName As String
        defName = "Workbook_" & Format(Now, "yyyymmdd_HHMMSS") & GetDefaultExtension(wb)
        saveName = Application.GetSaveAsFilename( _
            InitialFileName:=defName, _
            FileFilter:="Excel Files (*.xlsx;*.xlsm;*.xlsb;*.xls),*.xlsx;*.xlsm;*.xlsb;*.xls")
        If saveName = False Then GoTo CleanUp
        wb.SaveAs Filename:=CStr(saveName), FileFormat:=GuessFileFormatFromPath(CStr(saveName))
    Else
        wb.Save
    End If

    ' 2) 타임스탬프 사본 저장 (원본 이름 + _yyyymmdd_HHMMSS + 원래 확장자)
    Dim baseName As String, ext As String, newPath As String
    baseName = GetFileNameWithoutExt(wb.Name)
    ext = GetFileExt(wb.Name)
    newPath = wb.Path & Application.PathSeparator & _
              baseName & "_" & Format(Now, "yyyymmdd_HHMMSS") & "." & ext

    wb.SaveCopyAs newPath

CleanUp:
    Application.EnableEvents = prevEvents
End Sub

' 파일명에서 확장자 제거
Private Function GetFileNameWithoutExt(ByVal fileName As String) As String
    Dim p As Long: p = InStrRev(fileName, ".")
    If p > 0 Then
        GetFileNameWithoutExt = Left$(fileName, p - 1)
    Else
        GetFileNameWithoutExt = fileName
    End If
End Function

' 파일명에서 확장자만 추출 (없으면 xlsx 기본)
Private Function GetFileExt(ByVal fileName As String) As String
    Dim p As Long: p = InStrRev(fileName, ".")
    If p > 0 Then
        GetFileExt = Mid$(fileName, p + 1)
    Else
        GetFileExt = "xlsx"
    End If
End Function

' 저장 경로의 확장자에 맞춰 FileFormat 결정
Private Function GuessFileFormatFromPath(ByVal path As String) As XlFileFormat
    Dim ext As String: ext = LCase$(GetFileExt(path))
    Select Case ext
        Case "xlsm": GuessFileFormatFromPath = xlOpenXMLWorkbookMacroEnabled
        Case "xlsx": GuessFileFormatFromPath = xlOpenXMLWorkbook
        Case "xlsb": GuessFileFormatFromPath = xlExcel12
        Case "xls":  GuessFileFormatFromPath = xlExcel8
        Case Else:   GuessFileFormatFromPath = xlOpenXMLWorkbook
    End Select
End Function

' 현재 통합문서 형식을 바탕으로 기본 확장자 반환
Private Function GetDefaultExtension(wb As Workbook) As String
    Select Case wb.FileFormat
        Case xlOpenXMLWorkbookMacroEnabled: GetDefaultExtension = ".xlsm"
        Case xlExcel12:                     GetDefaultExtension = ".xlsb"
        Case xlExcel8:                      GetDefaultExtension = ".xls"
        Case Else:                          GetDefaultExtension = ".xlsx"
    End Select
End Function
'@
$dir = Split-Path -Path $path -Parent
New-Item -ItemType Directory -Force -Path $dir | Out-Null
Set-Content -Path $path -Value $code -Encoding UTF8