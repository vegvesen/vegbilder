# Test av kjørbare filer

Her tester vi ut kjørbare filer for windows (*.exe), samt hvordan disse kan brukes med 
kommandolinje- argumenter

### Alternativ 1: Angi filnavn for opppsettfil (*.json) 

```
cd dist
.\test.exe .\testinput.json 
```


### Alternativ 2: Angi argumenter direkte på kommandolinjen

Dette har jeg ikke fått til å fungere på windows.

En mulighet skal være  [denne oppskriften](https://stackoverflow.com/questions/25984395/after-compiling-python-program-how-to-input-arguments
 som legger argumentene inn i en windows-snarvei, men dette fikk jeg ikke til.  
 
### Kjøring av pyinstaller

Pyinstaller kjøres med kommando `pyinstaller --onefile <filnavn.py>` 