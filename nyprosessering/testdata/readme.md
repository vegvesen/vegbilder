# Testfiler for vegbilder-rutiner 


| Filnavn | Test | 
|-----|----|
| mangler_vegnetttilknytning.json                 | Mangler vegnetttilknytning exif_reflinkid, exif_reflinkposisjon, senterlinjeposisjon, exif_roadident  | 
| mangler_senterlinjeposisjon.json                 | Mangler senterlinjeposisjon, exif_roadident  | 
| mangler_exif_roadident | Nullverdi for egenskapen exif_roadident |
| ekstratagg.json                 | Har ugyldige tagger: ekstratagg | 
| manglertagg.json                | Mangler tagger: exif_vegnr, exif_speed |
| duplikattag.json.txt                | **IGNORER. Navnekollisjon er lov i json**. Taggen exif_dato forekommer 2 ganger. | 


```
ERROR: skjemafeil EKSTRA tagg ekstratagg UlovligTagg testdata/ekstratagg.json
ERROR: skjemafeil MANGLER tagg exif_speed exif_vegnr testdata/manglertagg.json
ERROR: Feil dataverdier/datatyper exif_roadident testdata/null_exif_roadident.json
```
