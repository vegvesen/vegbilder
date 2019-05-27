# vegbilder

Lager metadata for vegbilder tatt med Viatech utstyr: Les EXIF-header, stedfest, filflytting m.m

# UFERDIG! Til uttesting

# Tre rutiner for håndtering av vegbilder og metadata om vegbilder

### Trinn 1: Lag metadata

Leser metadata fra EXIF-header og (littegrann) metadata fra filnavn og mappenavn til bildet. 
Hvert bilde får en unik id (UUID), samt referanse til UUID for forrige og neste bilde. 
(Ja, dette betyr at det er trivielt å hente neste og forrige bilde på strekningen). 

Metadata skrives til en json-fil med samme filnavn som bildet. 

### Trinn 2. Stedfest metadata 

Vi leser metadata fra steg 1. Ut fra vegreferanse-verdier og bildedato gjør vi oppslag 
på historisk vegrefeanse (per bildedato, med Visveginfo-tjenesten). Metadata utvides
med veglenkeID, veglenkeposisjon og koordinater for vegens senterlinje. Resultatet skrivest
tilbake til json-filen.

### Trinn 3. Oppdater vegreferanse-verdier og lag nye fil/mappenavn

*(kommer snart!)*

Statens vegvesen har (eldre) programvare som er avhengig av at mappe- og filnavn for 
vegbilder følger oppbyggingen av vegreferansen 
(år - fylke - vegkategori, status og nummer - hp - meter). 
Denne koden bruker bildets stedfesting på vegnett 
(veglenkeID og veglenkeposisjon) til å hente de 
vegrefeanse-verdiene som er gyldig 
i dag, oppretter ny mappestruktur i hht ny vegreferanse og kopierer bildefil og 
oppdaterte metadata dit. Orginale metadata er selvsagt med videre. 

# Database og tjenester med metadata

Metadata (alle json-filene) legges i en romlig (spatial) database 
(postgis, oracle spatial), og vi bygger kule tjenester 
oppå der igjen! I første omgang konsentrerer vi oss om å bygge _WFS 
(web feature services, dvs spørre- og søketjenester)_ og 
WMS _(Web map services, dvs ferdige kartlag)_. Metadata fra disse 
tjenestene inkluderer selvsagt lenke (url) til den webserveren vi har satt opp
for å servere
vegbildene direkte fra disk. 

Vi bruker FME for å synkronisere metadata-databasen med det som finnes på disk. 
FME støvsuger disk etter nye og gamle JSON-filer, og oppdaterer databasen
direkte. I tillegg skriver FME et tidsstempel i alle json-filene for når dette
metadata-elementet ble oppdatert. Nøkkelen ligger selvsagt i UUID som ble opprettet 
i steg 1, og som blir med videre gjennom steg 2 _(stedfesting)_ og steg 3 _(oppdatering
av vegreferanse, med tilhørende oppdatering av fil- og mappenavn)_.


# Filstruktur

Filstruktur er bygget opp rundt ønsket om at python-kode skal kompileres til kjørbare filer på windows. 
Ergo føyer vi oss etter filstrukturen til pyinstaller. 


```
vegbilder/                <- Dette repositoryet
|__README.md              <- Den fila du leser nå
|
|__ trinn1_lagmetadata/ 
   |__ vegbilder_lesexif.py           <- Program som skal kompileres
   |__ dist/
      |__ vegbilder_lesexif.exe      <- Kjørbar fil
      |__ vegbilder_lesexif.json     <- Eksempel, oppsettfil

|__Steg_2_mappe/ 
    |__ stedfestvegbilder.py
    |__ dist/ 
       |__ stedfestvegbilder.exe
       |__ oppsettfil_stedfest.json        
       
|__Steg_3_mappe (kommer snart) 
    |__ div python-kodes
    |__ dist/ 
       |__ *.exe 

|__testbilder/
   |__ 06/
      |__ 2018/
         |__ 06_Ev134/
            |__ Hp05_Damåsen/
               |__ F1_2018_06_21/
                   Fy06_Ev134_hp05_f1_m03173.jpg
                   Fy06_Ev134_hp05_f1_m03192.jpg
                   Fy06_Ev134_hp05_f1_m03212.jpg
                   Fy06_Ev134_hp05_f1_m03232.jpg
                   Fy06_Ev134_hp05_f1_m03252.jpg
                   Fy06_Ev134_hp05_f1_m03272.jpg
                   Fy06_Ev134_hp05_f1_m03292.jpg
                  

|__ test_pyinstaller/
   |__ test.py             <-  Program som skal kompileres
   |__ dist/
      |__ test.exe         <- Demo, kjørbar fil for windows
```

# Blir anonymiserte vegbilder tilgjengelig utenfor Statens vegvesen? 

Parallelt med metadata-aktiviteten beskrevet her pågår det også innfasing av 
et system som anonymiserer vegbildene, dvs sladder personer og kjøretøy fra bildet.
Vil vi publisere disse vegbildene til entreprenører som trenger dem, evt legge 
dem ut som helt åpne tjenester? 

**Svaret per 27.mai 2019 er: Aner ikke.** 

Åpen publisering er intensjonen til oss som lager systemet beskrevet her, 
men A) vi må først få det til å funke, B) kjøre en god beslutningsprosess 
ang publisering. 

