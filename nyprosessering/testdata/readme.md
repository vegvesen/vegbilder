# Testfiler for vegbilder-rutiner 


| Filnavn | Test | 
|-----|----|
| ekstratagg.json                 | Har ugyldige tagger: ekstratagg | 
| manglertagg.json                | Mangler tagger: exif_vegnr, exif_speed |
| null_exif_roadident | Nullverdi for egenskapen exif_roadident 1 
| duplikattag.json.txt                | **IGNORER. Navnekollisjon er lov i json**. Taggen exif_dato forekommer 2 ganger. | 


```
ERROR: skjemafeil EKSTRA tagg ekstratagg UlovligTagg testdata/ekstratagg.json
ERROR: skjemafeil MANGLER tagg exif_speed exif_vegnr testdata/manglertagg.json
ERROR: Feil dataverdier/datatyper exif_roadident testdata/null_exif_roadident.json
```
