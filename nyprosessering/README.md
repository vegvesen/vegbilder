# Ny prosesseringskjede vegbilder

Vi har laget en ny prosesseringskjede for etterbehandling (kvalitetsheving) og kontroll av metadata for vegbilder. 

I `formatsjekk.py` har vi byggget funksjoner som spiller sammen for å håndtere digre mappehierarkier, finne filer med metadata, fikse dem og påfølgende kvalitetskontroll. Filnavn og bildeID for alle endrede metadata-elementer blir logget. Vi har loggrotasjon ved 10mb (justerbart, gå inn i `duallogg.py`). Der det var praktisk har vi gjenbrukt funksjoner fra den prosesseringskjeden vi hadde før (`flyttvegbilder_v54.py`). 

Koden har disse hoveddelene: 
1. **Finn** alle json-filer i en katalog (fullstendig mappe- og filnavn). Gjenbruk `huggmappetre`-logikken for å unngå å søke etter og holde på millionvis av filnavn samtidig. 
1. **Prosesser** hver av disse filene. Hvis nødvendig og mulig: Fiks opp manglende data, og juster kvalitetsparameter. 
1. **Kvalitetskontroll** Grundig kvalitetskontroll  

### De viktigste funksjonene: 

 | funksjonsnavn | Hva | Argument og nøkkelord | 
|----|-----|----- |
| `finnundermappe` | Graver seg ned i (potensielt digert) mappehierarki og sender en og en undermappe  til funksjonen `prosessermappe` | mappenavn |
|                  |        | finnundermappe=HELTALL Angir antall undernivåer vi skal gå nedover før vi sender mappenavnet til `prosesermappe` | 
|                  |        | dryrun=False se `prosesser`-funksjon | 
| `prosessermappe` | Finner alle json-filer i angitt katalog (og underkatalog), og sender dem til funksjonen `prosesser` | mappenavn | 
|      |       | dryrun=False Se `prosesser`-funksjonen | 
| `prosesser` | Retter opp datafeil i bildemetadata (json) Ferdig prosesserte metadata blir sjekket med funksjonen  `kvalitetskontroll`. Evt feil blir håndtert og logget.  | filnavn |
|             |                                           | dryrund=False (default) Fikser feilene og lagrer til disk |
|             |                                           | dryrund=True gir mer detaljert utlisting av aktuelle endringer, men lar filene ligge i fred |
| `kvalitetskontroll` | Sjekker for kjente feil, som igjen utløser feilsituasjonen `AssertionError` som må håndteres med try-exept konstruksjon (slik f.eks. funksjonene `prosesser` og `testing` gjør) | dictionary med metadata | 
| `testing` | Kopierer testdata til ny mappe og prosesserer denne. Tester både en enkelt katalog (`testdata/allefiler_flatt/`) og det å dele opp et mappehieraki i mindre biter ( funksjonen `finnundermappe`)


# Navngiving av funksjoner 

Funksjonen `kvalitetskontroll` bruker flere funksjoner, disse har  navn som starter med ordet "sjekk". 

Alle funksjoner som inngår i å fikse opp datamangler (dvs kalles av funksjonen `prosesser`) har navn som starter med "fiks". 

# Testdrevet utvikling 

Alle nye fiksdata-rutiner starter med at det lagres en eller flere JSON-fil(er) i /testdata/ - mappen og en test som finner akkurat denne feilen. Så lages det en feilrettingsfunksjon ("fiks*"). 

# TODO 

  * [x] Logg alle filnavn som endres (evt også feilmeldinger?). 
  * [x] Pass på at loggfilene ikke blir for store. 
  * [x] Sjekk og feilretting: Exif_reflinkid og exif_reflinkposisjon, bruk bildets koordinater. _(Og da fikser du selvsagt også senterlinjeposisjon og exif_roadident)_
  * [x] Sjekk og feilretting: Senterlinjeposisjon _(og fiks evt exif_roadident)_ 
  * [x] Sjekk og feilretting: exif_roadident (tekststreng med vegsystemreferanse) 
  * [x] Lage overordnede rutiner som kjører mot angitt katalog (huggmappetre-logikk for å ta passe store biter av gangen..) 
  * [ ] Juster kvalitetstagg `exif_kvalitet`
  
# Kvalitetsparameter exif_kvalitet

Taggen `exif_kvalitet`: 
  * 0 = bare drit, har lest ut fra filnavn
  * 1 = har posisjon, men ikke så mye anna
  * 2 = har alt som vi håper å finne i. 
  
Lage logikk hvor jeg føyer på et desimaltall som angir hvor mye informasjon som jeg har føyd til, og hva som evt mangler. Færrest mulig kvalitetsvarianter! 

# STATUS per 26.8.2020

Alle trinn er nå ferdig skrevet, spent på hvilke feil vi får når vi kjører på reelle data. 

Kjøring av programmet fra kommandolinje vil kjøre funksjonen "testing", som gjør følgende: 

1. Kjører kvalitetssjekk på mappen /testdata, dvs QA på data med kjente feil (sjekk [/testdata/readme.md](./testdata/readme.md)) 
2. Kopierer mappen /testdata => /testdata_temp og prosesserer denne 
    1. prosesser "flat" mappestruktur `prosesser( 'testdata_temp/allefiler_flatt')`
    1. Del opp mappestruktur i mindre biter (dsv finn undermapper) slik at du unngår å lete etter millionvis av .json-filer på diger katalog. `finnundermapper( 'testdata_temp')`
3. Kjører kvalitetssjekk på mappen /testdata_temp, dvs QA på ferdig prosesserte data
 
# Eksempel testkjøring

Kjøring av test gjøres med `python formatsjekk.py`, eksempel på resultat: 


```
2020-08-26 13:52:55,236 INFO    :  
2020-08-26 13:52:55,238 INFO    :  ====> Forbereder test
2020-08-26 13:52:55,239 INFO    :  
2020-08-26 13:52:55,239 INFO    :  ====> Kopierer testdata-mappe fra testdata => testdata_temp
2020-08-26 13:52:55,307 INFO    :  
2020-08-26 13:52:55,308 INFO    :  ====> Kvalitetskontroll, ikke prosesserte filer i testdata_temp
2020-08-26 13:52:55,308 INFO    :        Her kommer det masse WARNING-meldinger...

2020-08-26 13:52:55,311 WARNING : skjemafeil EKSTRA tagg ekstratagg UlovligTagg testdata_temp/allefiler_flatt/ekstratagg.json
2020-08-26 13:52:55,317 WARNING : skjemafeil MANGLER tagg exif_vegnr exif_speed testdata_temp/allefiler_flatt/manglertagg.json
2020-08-26 13:52:55,321 WARNING : Feil dataverdier/datatyper exif_roadident testdata_temp/allefiler_flatt/mangler_exif_roadident.json
2020-08-26 13:52:55,323 WARNING : Feil dataverdier/datatyper exif_reflinkid testdata_temp/allefiler_flatt/mangler_reflinkid.json
2020-08-26 13:52:55,326 WARNING : Feil dataverdier/datatyper exif_reflinkposisjon testdata_temp/allefiler_flatt/mangler_reflinkposisjon.json
2020-08-26 13:52:55,330 WARNING : Feil dataverdier/datatyper exif_roadident, senterlinjeposisjon testdata_temp/allefiler_flatt/mangler_senterlinjeposisjon.json
2020-08-26 13:52:55,332 WARNING : Feil dataverdier/datatyper exif_reflinkid, exif_reflinkposisjon, exif_roadident, senterlinjeposisjon testdata_temp/allefiler_flatt/mangler_vegnettilknytning.json
2020-08-26 13:52:55,336 WARNING : Feil dataverdier/datatyper exif_roadident testdata_temp/undermappeA/nivaa2/nivaa3/nivaa4/mangler_exif_roadident.json
2020-08-26 13:52:55,338 WARNING : Feil dataverdier/datatyper exif_reflinkid testdata_temp/undermappeA/nivaa2/nivaa3/nivaa4/mangler_reflinkid.json
2020-08-26 13:52:55,343 WARNING : Feil dataverdier/datatyper exif_reflinkposisjon testdata_temp/undermappeA/nivaa2/nivaa3/nivaa4/mangler_reflinkposisjon.json
2020-08-26 13:52:55,345 WARNING : Feil dataverdier/datatyper exif_roadident, senterlinjeposisjon testdata_temp/undermappeA/nivaa2/nivaa3/nivaa4/mangler_senterlinjeposisjon.json
2020-08-26 13:52:55,347 WARNING : Feil dataverdier/datatyper exif_reflinkid, exif_reflinkposisjon, exif_roadident, senterlinjeposisjon testdata_temp/undermappeA/nivaa2/nivaa3/nivaa4/mangler_vegnettilknytning.json
2020-08-26 13:52:55,353 WARNING : Feil dataverdier/datatyper exif_roadident testdata_temp/undermappeB/nivaa2/nivaa3/nivaa4/mangler_exif_roadident.json
2020-08-26 13:52:55,355 WARNING : Feil dataverdier/datatyper exif_reflinkid testdata_temp/undermappeB/nivaa2/nivaa3/nivaa4/mangler_reflinkid.json
2020-08-26 13:52:55,358 WARNING : Feil dataverdier/datatyper exif_reflinkposisjon testdata_temp/undermappeB/nivaa2/nivaa3/nivaa4/mangler_reflinkposisjon.json
2020-08-26 13:52:55,360 WARNING : Feil dataverdier/datatyper exif_roadident, senterlinjeposisjon testdata_temp/undermappeB/nivaa2/nivaa3/nivaa4/mangler_senterlinjeposisjon.json
2020-08-26 13:52:55,363 WARNING : Feil dataverdier/datatyper exif_reflinkid, exif_reflinkposisjon, exif_roadident, senterlinjeposisjon testdata_temp/undermappeB/nivaa2/nivaa3/nivaa4/mangler_vegnettilknytning.json
2020-08-26 13:52:55,364 INFO    :  
2020-08-26 13:52:55,365 INFO    :  ====> Prosesserer flat filstruktur-mappe testdata_temp/allefiler_flatt

2020-08-26 13:52:55,366 INFO    : Prosessermappe- klar til å prosessere 8 metadata-filer under testdata_temp/allefiler_flatt
2020-08-26 13:52:55,369 ERROR   : skjemafeil EKSTRA tagg ekstratagg UlovligTagg testdata_temp/allefiler_flatt/ekstratagg.json
2020-08-26 13:52:55,374 ERROR   : skjemafeil MANGLER tagg exif_vegnr exif_speed testdata_temp/allefiler_flatt/manglertagg.json
2020-08-26 13:52:55,575 INFO    : Prosessering - retta mangler: testdata_temp/allefiler_flatt/mangler_exif_roadident.json
2020-08-26 13:52:55,718 INFO    : Prosessering - retta mangler: testdata_temp/allefiler_flatt/mangler_reflinkid.json
2020-08-26 13:52:55,863 INFO    : Prosessering - retta mangler: testdata_temp/allefiler_flatt/mangler_reflinkposisjon.json
2020-08-26 13:52:56,011 INFO    : Prosessering - retta mangler: testdata_temp/allefiler_flatt/mangler_senterlinjeposisjon.json
2020-08-26 13:52:56,122 INFO    : Prosessering - retta mangler: testdata_temp/allefiler_flatt/mangler_vegnettilknytning.json
2020-08-26 13:52:56,125 INFO    : Prosessermappe - fiksa 5 filer under testdata_temp/allefiler_flatt
2020-08-26 13:52:56,125 INFO    :  
2020-08-26 13:52:56,126 INFO    :  ====> Finner undermapper til testdata_temp3 nivåeer ned, prosesserer hver enkelt undermappe

2020-08-26 13:52:56,127 INFO    : finner undermapper til: testdata_temp
2020-08-26 13:52:56,128 INFO    : fant undermappe: testdata_temp/allefiler_flatt/
2020-08-26 13:52:56,130 INFO    : finner undermapper til: testdata_temp/allefiler_flatt/
2020-08-26 13:52:56,131 INFO    : fant undermappe: testdata_temp/undermappeA/
2020-08-26 13:52:56,133 INFO    : finner undermapper til: testdata_temp/undermappeA/
2020-08-26 13:52:56,134 INFO    : fant undermappe: testdata_temp/undermappeA/nivaa2/
2020-08-26 13:52:56,135 INFO    : finner undermapper til: testdata_temp/undermappeA/nivaa2/
2020-08-26 13:52:56,136 INFO    : fant undermappe: testdata_temp/undermappeA/nivaa2/nivaa3/
2020-08-26 13:52:56,137 INFO    : Starter proseessering av undermappe: testdata_temp/undermappeA/nivaa2/nivaa3/
2020-08-26 13:52:56,138 INFO    : Prosessermappe- klar til å prosessere 6 metadata-filer under testdata_temp/undermappeA/nivaa2/nivaa3/
2020-08-26 13:52:56,293 INFO    : Prosessering - retta mangler: testdata_temp/undermappeA/nivaa2/nivaa3/nivaa4/mangler_exif_roadident.json
2020-08-26 13:52:56,440 INFO    : Prosessering - retta mangler: testdata_temp/undermappeA/nivaa2/nivaa3/nivaa4/mangler_reflinkid.json
2020-08-26 13:52:56,594 INFO    : Prosessering - retta mangler: testdata_temp/undermappeA/nivaa2/nivaa3/nivaa4/mangler_reflinkposisjon.json
2020-08-26 13:52:56,744 INFO    : Prosessering - retta mangler: testdata_temp/undermappeA/nivaa2/nivaa3/nivaa4/mangler_senterlinjeposisjon.json
2020-08-26 13:52:56,895 INFO    : Prosessering - retta mangler: testdata_temp/undermappeA/nivaa2/nivaa3/nivaa4/mangler_vegnettilknytning.json
2020-08-26 13:52:56,900 INFO    : Prosessermappe - fiksa 5 filer under testdata_temp/undermappeA/nivaa2/nivaa3/
2020-08-26 13:52:56,901 INFO    : fant undermappe: testdata_temp/undermappeB/
2020-08-26 13:52:56,903 INFO    : finner undermapper til: testdata_temp/undermappeB/
2020-08-26 13:52:56,905 INFO    : fant undermappe: testdata_temp/undermappeB/nivaa2/
2020-08-26 13:52:56,909 INFO    : finner undermapper til: testdata_temp/undermappeB/nivaa2/
2020-08-26 13:52:56,911 INFO    : fant undermappe: testdata_temp/undermappeB/nivaa2/nivaa3/
2020-08-26 13:52:56,912 INFO    : Starter proseessering av undermappe: testdata_temp/undermappeB/nivaa2/nivaa3/
2020-08-26 13:52:56,917 INFO    : Prosessermappe- klar til å prosessere 6 metadata-filer under testdata_temp/undermappeB/nivaa2/nivaa3/
2020-08-26 13:52:57,058 INFO    : Prosessering - retta mangler: testdata_temp/undermappeB/nivaa2/nivaa3/nivaa4/mangler_exif_roadident.json
2020-08-26 13:52:57,197 INFO    : Prosessering - retta mangler: testdata_temp/undermappeB/nivaa2/nivaa3/nivaa4/mangler_reflinkid.json
2020-08-26 13:52:57,345 INFO    : Prosessering - retta mangler: testdata_temp/undermappeB/nivaa2/nivaa3/nivaa4/mangler_reflinkposisjon.json
2020-08-26 13:52:57,509 INFO    : Prosessering - retta mangler: testdata_temp/undermappeB/nivaa2/nivaa3/nivaa4/mangler_senterlinjeposisjon.json
2020-08-26 13:52:57,666 INFO    : Prosessering - retta mangler: testdata_temp/undermappeB/nivaa2/nivaa3/nivaa4/mangler_vegnettilknytning.json
2020-08-26 13:52:57,674 INFO    : Prosessermappe - fiksa 5 filer under testdata_temp/undermappeB/nivaa2/nivaa3/
2020-08-26 13:52:57,674 INFO    :  
2020-08-26 13:52:57,676 INFO    :  ====> Sluttkontroll prosesserte data i testdata_temp...

2020-08-26 13:52:57,683 WARNING : skjemafeil EKSTRA tagg ekstratagg UlovligTagg testdata_temp/allefiler_flatt/ekstratagg.json
2020-08-26 13:52:57,692 WARNING : skjemafeil MANGLER tagg exif_vegnr exif_speed testdata_temp/allefiler_flatt/manglertagg.json
```


