# Testfiler for vegbilder-rutiner 


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
| duplikattag.json.txt                | **IGNORER. Navnekollisjon er lov i json**. Taggen exif_dato forekommer 2 ganger. | 

### Testresultat for disse filene (kjørt 25.8.2020) 

```
ERROR: skjemafeil EKSTRA tagg UlovligTagg ekstratagg testdata/ekstratagg.json
ERROR: skjemafeil MANGLER tagg exif_speed exif_vegnr testdata/manglertagg.json
ERROR: Feil dataverdier/datatyper exif_roadident testdata/mangler_exif_roadident.json
ERROR: Feil dataverdier/datatyper exif_reflinkid testdata/mangler_reflinkid.json
ERROR: Feil dataverdier/datatyper exif_reflinkposisjon testdata/mangler_reflinkposisjon.json
ERROR: Feil dataverdier/datatyper exif_roadident, senterlinjeposisjon testdata/mangler_senterlinjeposisjon.json
ERROR: Feil dataverdier/datatyper exif_reflinkid, exif_reflinkposisjon, exif_roadident, senterlinjeposisjon testdata/mangler_vegnettilknytning.json
```
