# Test av kjørbare filer

Her tester vi ut kjørbare filer for windows (*.exe), samt hvordan disse kan brukes med 
kommandolinje- argumenter

### Alternativ 1: Angi filnavn for opppsettfil (*.json) 

```
cd dist
test.exe
test.exe testinput.json 
test.exe testinput.json TJOBING
```

(evt med ".\" foran filnavnene, typisk powershell) 

### Alternativ 2: Angi argumenter direkte på kommandolinjen

```
cd dist
test.exe
test.exe TJOBING
test.exe "../../lang/kronglete/sti/til/vegbildemappe" "sti/til/dit/resultatene/skal/ligge" 
``` 
 
### Kjøring av pyinstaller

Pyinstaller kjøres med kommando `pyinstaller --onefile <filnavn.py>` 