# Testfiler for vegbilder-rutiner 


| Filnavn | Test | 
|-----|----|
FV00013_S1D1_m00014_f1.json     | |
RV00004_S1D1_m10918_f4K.json    | |
ekstratagg.json                 | Har ugyldige tagger: ekstratagg,  | 
manglertagg.json                | Mangler tagger: exif_vegnr, exif_speed | 
duplikattag.json                | Taggen exif_dato forekommer 2 ganger. **Navnekollisjon er lov i json**. Altså ikke feil (i Python), men første forekomst ignoreres.  
 