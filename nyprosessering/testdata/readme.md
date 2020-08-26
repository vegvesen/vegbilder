# Testfiler for vegbilder-rutiner 

## Filer som inngår i test:

| Filnavn | Test | 
|-----|----|
| mangler_vegnetttilknytning.json                 | Mangler vegnetttilknytning exif_reflinkid, exif_reflinkposisjon, senterlinjeposisjon, exif_roadident  | 
| mangler_reflinkid.json                 | Mangler exif_reflinkid | 
| mangler_reflinkposisjon.json                 | Mangler exif_reflinkposisjon  | 
| mangler_vegnetttilknytning.json                 | Mangler vegnetttilknytning exif_reflinkid, exif_reflinkposisjon, senterlinjeposisjon, exif_roadident  | 
| mangler_senterlinjeposisjon.json                 | Mangler senterlinjeposisjon, exif_roadident  | 
| mangler_exif_roadident | Nullverdi for egenskapen exif_roadident |
| ekstratagg.json                 | Har ugyldige tagger: ekstratagg | 
| manglertagg.json                | Mangler tagger: exif_vegnr, exif_speed |

###  Kvalitetskontroll for disse filene (kjørt 26.8.2020) 

Kjørt denne koden: 
```
import logging 

from formatsjekk import kvalitetskontroll, finnfiltype
from flyttvegbilder_v54 import lesjsonfil
import duallog

duallog.duallogSetup( logdir='loggdir', logname='loggfil')

filer = finnfiltype( 'testdata/allefiler_flatt', '.json' )

for filnavn in filer:
    jsondata = lesjsonfil( filnavn)
    try:
        kvalitetskontroll( jsondata, filnavn)
    except AssertionError as myErr:
        logging.warning( myErr)

```

Så får du dette resultatet (per 26.8.2020) 

```
WARNING: skjemafeil EKSTRA tagg UlovligTagg ekstratagg testdata/allefiler_flatt/ekstratagg.json
WARNING: skjemafeil MANGLER tagg exif_vegnr exif_speed testdata/allefiler_flatt/manglertagg.json
WARNING: Feil dataverdier/datatyper exif_roadident testdata/allefiler_flatt/mangler_exif_roadident.json
WARNING: Feil dataverdier/datatyper exif_reflinkid testdata/allefiler_flatt/mangler_reflinkid.json
WARNING: Feil dataverdier/datatyper exif_reflinkposisjon testdata/allefiler_flatt/mangler_reflinkposisjon.json
WARNING: Feil dataverdier/datatyper exif_roadident, senterlinjeposisjon testdata/allefiler_flatt/mangler_senterlinjeposisjon.json
WARNING: Feil dataverdier/datatyper exif_reflinkid, exif_reflinkposisjon, exif_roadident, senterlinjeposisjon testdata/allefiler_flatt/mangler_vegnettilknytning.json
```

Merk at funksjonen `kvalitetskontroll` kaster en `AssertionError` for hvert avvik den finner. Disse feilene må fanges (try-except), samt deretter velger rett loggenivå (ERROR, WARNING, INFO, DEBUG) med `logging`-modulen.

# Mappestruktr 

For å teste `huggmappetre`-logikken (unngå å lese millionvis av filer  filene er så fordelt i et mappe-hierarki som ser slik ut: 

```
testdata
testdata/
├── readme.md                       <=== Denne fila du leser nå
├── allefiler_flatt                 <=== Filene omtalt over
│   ├── ekstratagg.json
│   ├── gyldigvegbilde.json
│   ├── mangler_exif_roadident.json
│   ├── mangler_reflinkid.json
│   ├── mangler_reflinkposisjon.json
│   ├── mangler_senterlinjeposisjon.json
│   ├── mangler_vegnettilknytning.json
│   ├── manglertagg.json
│   └── readme.md
├── undermappeA                     <=== Mappehierarki for å teste "huggmappetre" - logikken 
│   └── nivaa2
│       ├── nivaa3_mappeA
│       │   └── nivaa4
│       │       ├── gyldigvegbilde.json
│       │       ├── mangler_exif_roadident.json
│       │       ├── mangler_reflinkid.json
│       │       ├── mangler_reflinkposisjon.json
│       │       ├── mangler_senterlinjeposisjon.json
│       │       └── mangler_vegnettilknytning.json
│       └── nivaa3_mappeB
│           └── nivaa4
│               ├── gyldigvegbilde.json
│               ├── mangler_exif_roadident.json
│               ├── mangler_reflinkid.json
│               ├── mangler_reflinkposisjon.json
│               ├── mangler_senterlinjeposisjon.json
│               └── mangler_vegnettilknytning.json
└── undermappeB
    └── nivaa2
        └── nivaa3
            └── nivaa4
                ├── gyldigvegbilde.json
                ├── mangler_exif_roadident.json
                ├── mangler_reflinkid.json
                ├── mangler_reflinkposisjon.json
                ├── mangler_senterlinjeposisjon.json
                ├── mangler_vegnettilknytning.json
                └── readme.md

```