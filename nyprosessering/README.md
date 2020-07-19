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

  * [ ] Kan vi gjenbruke _huggmappetre_ - logikken og øvrig flbehandling-logikk fra den koden jeg skrev for gammel prosesseringskjede?
  * [ ] Er det ting vi absolutt IKKE bør gjenbruke fra gammel prosesseringskjede? 