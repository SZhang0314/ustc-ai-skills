@echo off
REM Compile the bilingual collection. Run from the tex/ directory.
REM Requires: preamble.tex, collection.tex, figures/ all in this directory.
cd /d "%~dp0"
for /L %%i in (1,1,3) do (
  echo ===== XELATEX PASS %%i =====
  xelatex -interaction=nonstopmode collection.tex > nul 2>&1
)
echo DONE
