# Ny prosesseringskjede

Her kommer etter hvert ny prosesseringskjede, betydelig enklere enn før, og med en ny skjemadefinisjon. 

# Grunnskisse, logikk 

Lage streng validering, gyldige data på alle egenskapverdier! Så føyer vi til logikk for manglende data etter hvert som vi møter dem. 

Hente senterlinjeposisjon hvis det mangler. 

Skriv inn "exif_roadident" hvis den mangler. 


Gamle data: Jeg vil få data fra Daniels python-script, så skjema = identisk med det vi har for nye bilder. Trenger kun lage logikk 

exif_kvalitet: 
  * 0 = bare drit, har lest ut fra filnavn
  * 1 = har posisjon, men ikke så mye anna
  * 2 = har alt som vi håper å finne i. 
  
Lage logikk hvor jeg føyer på et desimaltall som angir hvor mye informasjon som jeg har føyd til, og hva som evt mangler. Færrest mulig kvalitetsvarianter! 


# Uavklarte spm, alfaversjon sluttkontroll

Har laget en alfaversjon som leser JSON-filer og sjekker om de har samme struktur som skjema. Denne siste kvalitetssjekken blir siste ledd i en prosesseringskjede _(to be written)_ som korrigerer for kjente feil og mangler, **dvs en form for sluttkontroll.**

  * [ ] Hva skjer når filene ikke går gjennom sluttkontroll? Logge som feil, eller katastrofalt crash?
  * [ ] Skal sluttkontrollen godta at filer kan ha  **flere elementer** enn det som er definert i skjema? Hvis nei - Logges som feil, som advarsel eller katastrofal stans? 

# Dataflyt spm

  * [x] Kan vi gjenbruke _huggmappetre_ - logikken og øvrig flbehandling-logikk fra den koden jeg skrev for gammel prosesseringskjede? **JA** 
  * [x] Er det ting vi absolutt IKKE bør gjenbruke fra gammel prosesseringskjede? **Tror ikke det, bare plukk det vi trenger?**
  
-----------------------------

# Forslag dataflyt 

Bygg opp koden rundt disse hoveddelene: 
1. **Finn** alle json-filer i en katalog (fullstendig mappe- og filnavn). Bruk `huggmappetre` for å unngå å lese millionvis av filer samtidig. 
1. **Prosesser** hver av disse filene. Hvis nødvendig og mulig: Fiks opp manglende data, og juster kvalitetsparameter. 
1. **Kvalitetskontroll** Grundig kvalitetskontroll  

## Rekkefølge 

Flere funksjoner som spiller sammen for å håndtere digre mappehierarkier, finne filer med metadata, fikse dem og påfølgende kvalitetskontroll. Filnavn og bildeID for alle endrede metadata-elementer blir logget. Vi har loggrotasjon ved 10mb (justerbart, gå inn i `duallogg.py`). 

 | funksjonsnavn | Hva | Argument og nøkkelord | 
|----|-----|----- |
| `finnundermappe` | Graver seg ned i (potensielt digert) mappehierarki og sender en og en undermappe  til funksjonen `prosessermappe` | mappenavn |
|                  |        | finnundermappe=HELTALL Angir antall undernivåer vi skal gå nedover før vi sender mappenavnet til `prosesermappe` | 
|                  |        | dryrun=False se `prosesser`-funksjon | 
| `prosessermappe` | Finner alle json-filer i angitt katalog (og underkatalog), og sender dem til funksjonen `prosesser` | mappenavn | 
|      |       | dryrun=False Se `prosesser`-funksjonen | 
| `prosesser` | Retter opp datafeil i bildemetadata (json) Ferdig prosesserte metadata sendes til `kvalitetskontroll` | filnavn |
|             |                                           | dryrund=False (default) Fikser feilene og lagrer til disk |
|             |                                           | dryrund=True gir mer detaljert utlisting av aktuelle endringer, men lar filene ligge i fred |
| `kvalitetskontroll` | Sjekker for kjente feil, som igjen utløser feilsituasjonen `AssertionError` som må håndteres med try-exept konstruksjon | dictionary med metadata | 



# Navngiving av funksjoner 

Funksjonen `kvalitetskontroll` bruker flere funksjoner, disse har  navn som starter med ordet "sjekk". 

Alle funksjoner som inngår i å fikse opp datamangler har navn som starter med "fiks". 

# Testdrevet utvikling 

Alle nye fiksdata-rutiner starter med at det lagres en JSON-fil i /testdata/ - mappen og en test som finner akkurat denne feilen (ny "sjekk" - funksjon, eller forbedre en av dem vi har?). 

# TODO 

  * [x] Logg alle filnavn som endres (evt også feilmeldinger?). 
  * [x] Pass på at loggfilene ikke blir for store. 
  * [x] Sjekk og feilretting: Exif_reflinkid og exif_reflinkposisjon, bruk bildets koordinater. _(Og da fikser du selvsagt også senterlinjeposisjon og exif_roadident)_
  * [x] Sjekk og feilretting: Senterlinjeposisjon _(og fiks evt exif_roadident)_ 
  * [x] Sjekk og feilretting: exif_roadident (tekststreng med vegsystemreferanse) 
  * [x] Lage overordnede rutiner som kjører mot angitt katalog (huggmappetre-logikk for å ta passe store biter av gangen..) 
  
 
# STATUS per 25.8.2020

Alle trinn er nå ferdig skrevet, spent på hvilke feil vi får når vi kjører på reelle data. 

Kjøring av programmet fra kommandolinje vil kjøre funksjonen "testing", som gjør følgende: 

1. Kjører kvalitetssjekk på mappen /testdata, dvs QA på data med kjente feil (sjekk [/testdata/readme.md](./testdata/readme.md)) 
2. Kopierer mappen /testdata => /testdata_temp og prosesserer denne 
3. Kjører kvalitetssjekk på mappen /testdata_temp, dvs QA på ferdig prosesserte data
 
Resultat av testkjøring 25.8.2020: 

```
INFO: Forbereder test
========
INFO: Kopierer testfil: testdata/ekstratagg.json
INFO: Kopierer testfil: testdata/gyldigvegbilde.json
INFO: Kopierer testfil: testdata/manglertagg.json
INFO: Kopierer testfil: testdata/mangler_exif_roadident.json
INFO: Kopierer testfil: testdata/mangler_reflinkid.json
INFO: Kopierer testfil: testdata/mangler_reflinkposisjon.json
INFO: Kopierer testfil: testdata/mangler_senterlinjeposisjon.json
INFO: Kopierer testfil: testdata/mangler_vegnettilknytning.json
INFO: Kopierer testfil: testdata/readme.md
INFO: ##############################

QA ubearbeidede data

ERROR: skjemafeil EKSTRA tagg UlovligTagg ekstratagg testdata/ekstratagg.json
ERROR: skjemafeil MANGLER tagg exif_speed exif_vegnr testdata/manglertagg.json
ERROR: Feil dataverdier/datatyper exif_roadident testdata/mangler_exif_roadident.json
ERROR: Feil dataverdier/datatyper exif_reflinkid testdata/mangler_reflinkid.json
ERROR: Feil dataverdier/datatyper exif_reflinkposisjon testdata/mangler_reflinkposisjon.json
ERROR: Feil dataverdier/datatyper exif_roadident, senterlinjeposisjon testdata/mangler_senterlinjeposisjon.json
ERROR: Feil dataverdier/datatyper exif_reflinkid, exif_reflinkposisjon, exif_roadident, senterlinjeposisjon testdata/mangler_vegnettilknytning.json
INFO: 
###########################

Prosessering...

INFO: Prosessering - retta mangler: testdata_temp/mangler_exif_roadident.json
INFO: Prosessering - retta mangler: testdata_temp/mangler_reflinkid.json
INFO: Prosessering - retta mangler: testdata_temp/mangler_reflinkposisjon.json
INFO: Prosessering - retta mangler: testdata_temp/mangler_senterlinjeposisjon.json
INFO: Prosessering - retta mangler: testdata_temp/mangler_vegnettilknytning.json
INFO: 
###########################

QA prosesserte data...

ERROR: skjemafeil EKSTRA tagg UlovligTagg ekstratagg testdata_temp/ekstratagg.json
ERROR: skjemafeil MANGLER tagg exif_speed exif_vegnr testdata_temp/manglertagg.json
```


