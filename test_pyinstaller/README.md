# Test av kjørbare filer

Her tester vi ut kjørbare filer for windows (*.exe), samt hvordan disse kan brukes med 
kommandolinje- argumenter

### Alternativ 1: Angi filnavn for opppsettfil (*.json) 

```
cd dist
test.exe testinput.json 
```

(evt med "./" foran filnavnene, typisk powershell) 

### Alternativ 2: Angi argumenter direkte på kommandolinjen

```
test.exe tjobing
test.exe "Langt argument, typisk sti til mappe med vegbilder"
``` 
 
### Kjøring av pyinstaller

Pyinstaller kjøres med kommando `pyinstaller --onefile <filnavn.py>` 