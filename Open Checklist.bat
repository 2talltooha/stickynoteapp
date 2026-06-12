@echo off
rem Double-click this file to launch the checklist widget with no console window.
rem %~dp0 = this .bat's own folder, so it works wherever you move the folder.
rem start "" = the .bat returns immediately and the console window closes.
rem pythonw  = Python with no console window.

start "" pythonw.exe "%~dp0checklist_widget.py"

rem Fallback if "pythonw.exe" isn't on PATH: use the py launcher in windowless mode.
if errorlevel 1 start "" py -w "%~dp0checklist_widget.py"
