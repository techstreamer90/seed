# Create Desktop Shortcut for Canvas Window

$WshShell = New-Object -comObject WScript.Shell
$Desktop = [System.Environment]::GetFolderPath("Desktop")
$Shortcut = $WshShell.CreateShortcut("$Desktop\Canvas Window.lnk")
$Shortcut.TargetPath = "python.exe"
$Shortcut.Arguments = "src\ui\canvas_window.py"
$Shortcut.WorkingDirectory = "C:\seed"
$Shortcut.Description = "Seed Canvas Window - Input capture for the living world"
$Shortcut.Save()

Write-Host "Desktop shortcut created: $Desktop\Canvas Window.lnk"
