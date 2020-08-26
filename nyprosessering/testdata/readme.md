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

###  Kvalitetskontroll for disse filene (kjørt 25.8.2020) 

Kjørt denne koden: 
```


```


```
ERROR: skjemafeil EKSTRA tagg UlovligTagg ekstratagg ekstratagg.json
ERROR: skjemafeil MANGLER tagg exif_speed exif_vegnr manglertagg.json
ERROR: Feil dataverdier/datatyper exif_roadident mangler_exif_roadident.json
ERROR: Feil dataverdier/datatyper exif_reflinkid mangler_reflinkid.json
ERROR: Feil dataverdier/datatyper exif_reflinkposisjon mangler_reflinkposisjon.json
ERROR: Feil dataverdier/datatyper exif_roadident, senterlinjeposisjon mangler_senterlinjeposisjon.json
ERROR: Feil dataverdier/datatyper exif_reflinkid, exif_reflinkposisjon, exif_roadident, senterlinjeposisjon mangler_vegnettilknytning.json
```

Disse filene er så fordelt i et mappe-hierarki som ser slik ut: 

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