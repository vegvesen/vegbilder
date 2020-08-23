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

## Del 1: Finn JSON-filer 

| Funksjonsnavn | `Ikke avgjort` | 
|----|-----| 
| Argument | Mappenavn 
| | `huggmappetre` - parametre. 

Grei sak, bruk gammel kode, trolig helt uten endringer. Hvert enkelt filnavn brukes som argument til feilretting-prosessen 

## Del 2: Prosesser 


| Funksjonsnavn | `Ikke avgjort`|
|----|------|
|Argument| Filnavn på jsonfil    |

Gjenbruk biter av gammel kode. Behandler en og en JSON-fil. Kun evt endringer blir skrevet til fil (overskriver det som ligger fra før). 

Ferdig prosesserte data blir  brukt som argument til kvalitetskontrollen. 

## Del 3: Kvalitetskontroll

| Funksjonsnavn | `Ikke avgjort`|
|----|:------|
|Argument| dict med ferdig prosesserte data    |
|      | dict med fasit (leses fra fil, men trenger kun lese 1 gang...) |
|      | filnavn (for json-fil) |  



