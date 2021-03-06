"""
Fikser metadata (json-filer) for vegbilder. Kan gå løs på mindre biter av digre kataloger (millioner av bilder)

Sjekk README.md for bruk 
"""

# Standard library 
import json
import logging
import os 
from pathlib import Path
from pydoc import locate
from datetime import datetime
import dateutil.parser
import requests 
import glob
from distutils.dir_util import copy_tree

import pdb

# Well known 3rd party libraries

# Custom libraries
import duallog
from flyttvegbilder_v54 import lesjsonfil, skrivjsonfil
from flyttvegbilder_v54 import findfiles, kopierfil

def sjekktagger( jsondata, filnavn ):
    """
    Sjekker om dictionary har alle påkrevde tagger 
    
    ARGUMENTS
        jsonmal - dictionary som vi sammenligner med
        
        jsondata - dictionary som skal kvalitetssjekkes
        
        filnavn - Filnavn til jsondata. Brukes til logging
    """
    

    # Sjekker at alle påkrevde tagger finnes, evt duplikater
    jsonmal = vegbildejsonmal()
    mal_keys = set( jsonmal )
    data_keys = set( jsondata )

    # Mangler vi noen tagger? 
    diff1 = mal_keys - data_keys
    assert len( diff1 ) == 0, ' '.join( ['skjemafeil MANGLER tagg',  *diff1, filnavn] )

    # Overflødige tagger? 
    diff2 = data_keys - mal_keys
    assert len( diff2 ) == 0, ' '.join( ['skjemafeil EKSTRA tagg',  *diff2, filnavn] )


def sjekk_alle_egenskaper( jsondata, kun_paakrevd=True ): 
    """
    Sjekker om alle (påkrevde) egenskapverdier har rett datatype 

    ARGUMENTS
        jsondata - data som skal sjekkes


    KEYWORDS
        kun_paakrevd=True (default) Sjekker kun obligatoriske verdier, dvs de som har verdien skalHa=True i 
        malen / skjemaet du får fra funksjonen vegbildejsonmal 

    RETURNS
        Tomt tekstfelt hvis alle sjekkene godtas, evt navnet på alle egenskapverdier som feiler
    """

    jsonmal = vegbildejsonmal()
    returnValue = ''
    feiler = []
    for taggnavn in jsonmal.keys(): 

        if not kun_paakrevd or jsonmal[taggnavn]['skalha']: 
            if not sjekkegenskapverdi( jsondata, taggnavn, jsonmal[taggnavn]['type']): 
                feiler.append( taggnavn)

    if len( feiler ) > 0: 
        returnValue = ', '.join( feiler )

    return returnValue

def filnavndata( filnavn ): 
    """
    Utleder dataverdier fra filnavn 

    ARGUMENTS
        filnavn : Tekst string. Kan være kun filnavn, eller komplett / relativt 
                  sti til fil. Takler både forward og backward slash. 

    KEYWORDS
        None 

    RETURNS
        Dictionary med medatdata avledet fra filnavn, eller None hvis feil 
    """
    # Takler både back- og forwardslash (og kombinasjoner av disse) 
    biter = filnavn.split('/')[-1].split('\\')[-1].split( '_' )
    mydict = {}
 
    try: 
        mydict['fylke']   = int( biter[0].lower().split('fy')[1] )
        mydict['vegkat']  = biter[1][0]
        mydict['vegstat'] = biter[1][1]
        mydict['vegnr']   = int( biter[1][2:])
        mydict['hp']      = int( biter[2].lower().split('hp')[1] )
        mydict['felt']    = int( biter[3].lower().split('f' )[1] )
        mydict['meter']   = int( biter[4].lower().split('.' )[0].split('m')[1] )

    except (IndexError, ValueError): 
        logging.warning( 'Ugyldig filnavn - klarte ikke utlede metadata: ' + filnavn )
        return None 
    else: 
        return mydict


def sjekkegenskapverdi( jsondata, taggnavn, taggtype ): 
    """
    Sjekker om en taggen har fornuftig verdi og datatype 

    ARGUMENTS
        jsondata - dictionary med de dataene vi skal sjekke

        taggnavn - egenskapverdi som skal sjekkes

        taggtype - Navn på  datatype som skal valideres ('int', 'str', 'float', ...)

    Ekstra valideringsregler (regex, numerisk verdi etc) kan føyes på som nye nøkkelord-parametre. 
    F.eks regex-setninger 
    
    https://stackoverflow.com/questions/11775460/lexical-cast-from-string-to-type
    """

    returnValue = False 

    # Taggen finnes og har noe annet enn None-verdi: 
    if taggnavn in jsondata and jsondata[taggnavn]: 

        datatype = locate( taggtype )
        rawdata = jsondata[taggnavn]

        # Prøver å konvertere til angitt datatype. Blir None om det feiler
        # Datoer er litt mer komplekst og har særbehandling 
        data = None 
        try: 
            if taggtype in [ 'date', 'datetime' ]: 
                data = dateutil.parser.parse( rawdata ) 
            else: 
                data = locate( taggtype)( rawdata ) 
        except ValueError: 
            pass

        # Vi skal ha ren tekst - og har tekst
        if taggtype == 'str' and isinstance( rawdata, str): 

            # Evt ekstra valideringsregler for tekst (regex?) føyes til her
            # Blir i så fall et nytt nøkkelord-parameter (evt flere) 
            returnValue = True 

        # Sjekker at vi ikke har flyttallverdi der vi skal ha heltall 
        # Float-verdier numerisk identisk med heltall godtas, dvs 1.0 == 1
        elif taggtype == 'int': 
            if (isinstance( rawdata, float) or isinstance( rawdata, int)) and rawdata == data: 
                returnValue = True 
            elif isinstance( rawdata, str) and data and float( rawdata) == data: 
                returnValue = True 
                
        # Gyldig dato? 
        elif taggtype in [ 'date', 'datetime' ] and isinstance( data, datetime): 
            returnValue = True
            
        # Alt mulig anna? Har iallfall den datatypen vi skal ha?
        elif isinstance( data, datatype): 
            returnValue = True 

    return returnValue 

def kvalitetskontroll( jsondata, filnavn, kun_paakrevd=True): 
    """
    Kvalitetskontroll av ferdige prosesserte data 

    ARGUMENTS
        jsonmal - dictionary som vi sammenligner med
        
        jsondata - dictionary som skal kvalitetssjekkes
        
        filnavn - Filnavn til jsondata. Brukes til logging

    
    KEYWORDS
        kun_paakrevd=True (default) Sjekker kun obligatoriske verdier, dvs de som har verdien skalHa=True i 
        malen / skjemaet du får fra funksjonen vegbildejsonmal 

    RETURNS
        Ingen returverdier, men assert vil kaste AssertionError når sjekkene feiler
    """
    sjekktagger( jsondata, filnavn)
    egenskapsjekk = sjekk_alle_egenskaper( jsondata, kun_paakrevd=kun_paakrevd)
    assert egenskapsjekk == '', ' '.join( ['Feil dataverdier/datatyper',  egenskapsjekk,  filnavn ] )
                            
def testing( testdata='testdata', tempdir='testdata_temp', 
                logdir='test_loggdir', logname='test_loggnavn', huggMappeTre=3 ):
    """
    Kjører gjennom testdata

    Kopierer mappen med testdata til en midlertidig katalog (som overskrives, hvis den finnes fra før). 
    Anvender deretter alle kvalitetssikrings / kvalitetsheving-rutiner på testdata. 
    """

    duallog.duallogSetup( logdir=logdir, logname=logname) 
    testfiler = finnfiltype(testdata, filetternavn='.json' )

    fremhev = ' ====> '
    logging.info( ' ')
    logging.info( fremhev + 'Forbereder test')
    logging.info( ' ')
    logging.info(  fremhev + 'Kopierer testdata-mappe fra ' + testdata + ' => ' + tempdir )

    copy_tree( testdata, tempdir )

    logging.info( ' ')
    logging.info( fremhev + 'Kvalitetskontroll, ikke prosesserte filer i ' + tempdir )
    logging.info(    '       Her kommer det masse WARNING-meldinger...\n')

    kopiertefiler = finnfiltype( tempdir,  '.json')
    for filnavn in kopiertefiler: 
        jsondata = lesjsonfil( filnavn, ventetid=1) 

        try: 
            kvalitetskontroll( jsondata, filnavn) 
        except AssertionError as myErr: 
            logging.warning( str( myErr) ) 

    logging.info( ' ')
    logging.info(  fremhev + 'Prosesserer flat filstruktur-mappe ' + tempdir + '/allefiler_flatt\n')

    prosessermappe( tempdir  + '/allefiler_flatt')

    logging.info( ' ')
    logging.info(  fremhev + 'Finner undermapper til ' + tempdir + str( huggMappeTre) + ' nivåeer ned, prosesserer hver enkelt undermappe\n')

    finnundermapper( tempdir, huggMappeTre=huggMappeTre) 

    logging.info( ' ')
    logging.info(  fremhev + 'Sluttkontroll prosesserte data i ' + tempdir + '...\n')


    for filnavn in kopiertefiler: 
        jsondata = lesjsonfil( filnavn, ventetid=1) 

        try: 
            kvalitetskontroll( jsondata, filnavn) 
        except AssertionError as myErr: 
            logging.warning( str( myErr) ) 


def vegbildejsonmal( ): 
    """Returnerer eksempel på gyldig JSON"""

    mal = {
            "exif_tid":                 { 'type' : 'datetime', 'skalha' : True, 'eksempel' :  "2020-06-02T09:42:46.3948628" },
            "exif_dato":                { 'type' : 'date', 'skalha' : True, 'eksempel' : "2020-06-02" },
            "exif_speed":               { 'type' : 'float', 'skalha' : False, 'eksempel' :  "0" },
            "exif_heading":             { 'type' : 'float', 'skalha' : False, 'eksempel' :  "302.295333221872"},
            "exif_gpsposisjon":         { 'type' : 'str', 'skalha' : True, 'eksempel' :  "srid=4326;POINT Z( 6.5663939242382572 61.214710343813685 48.856250803013438 )"},
            "exif_strekningsnavn":      { 'type' : 'str', 'skalha' : False, 'eksempel' :  "DRAGSVIK FK X55" },
            "exif_fylke":               { 'type' : 'str', 'skalha' : False, 'eksempel' :  "46"},
            "exif_vegkat":              { 'type' : 'str', 'skalha' : False, 'eksempel' :  "F"},
            "exif_vegstat":             { 'type' : 'str', 'skalha' : False, 'eksempel' :  "V" },
            "exif_vegnr":               { 'type' : 'str', 'skalha' : False, 'eksempel' :  "13" },
            "exif_hp":                  { 'type' : 'str', 'skalha' : False, 'eksempel' :  "TEKST med vegsystemreferanse" },
            "exif_strekning":           { 'type' : 'str', 'skalha' : False, 'eksempel' :  "1" },
            "exif_delstrekning":        { 'type' : 'str', 'skalha' : False, 'eksempel' :  "1" },
            "exif_ankerpunkt":          { 'type' : 'str', 'skalha' : False, 'eksempel' :  "" },
            "exif_kryssdel":            { 'type' : 'str', 'skalha' : False, 'eksempel' :  "" },
            "exif_sideanleggsdel":      { 'type' : 'str', 'skalha' : False, 'eksempel' :  "" },
            "exif_meter":               { 'type' : 'str', 'skalha' : False, 'eksempel' :  "14.344072423939158" },
            "exif_feltkode":            { 'type' : 'str', 'skalha' : False, 'eksempel' :  "1" },
            "exif_mappenavn":           { 'type' : 'str', 'skalha' : False, 'eksempel' :  "C:/DATA/ViaPPS/Measurements/20200602/2020_06_02/FV00013/S1/D1/F1_2020_06_02" },
            "exif_filnavn":             { 'type' : 'str', 'skalha' : False, 'eksempel' :  "FV00013_S1D1_m00014_f1.jpg" },
            "exif_strekningreferanse":  { 'type' : 'str', 'skalha' : False, 'eksempel' :  "S1/D1" },
            "exif_imageproperties":     { 'type' : 'str', 'skalha' : False, 'eksempel' :   "<?xml version=\"1.0\" ?>\n<ImageProperties Date=\"2020-06-02T09:42:46.3948628\" xmlns:xsd=\"http://www.w3.org/2001/XMLSchema\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">\n\t<ImageName>C:\\DATA\\ViaPPS\\Measurements\\20200602\\2020_06_02\\FV00013\\S1\\D1\\F1_2020_06_02\\FV00013_S1D1_m00014_f1.jpg</ImageName>\n\t<ImageSequenceNumber>1</ImageSequenceNumber>\n\t<Speed>0</Speed>\n\t<Distance>0</Distance>\n\t<AirTemperature>NaN</AirTemperature>\n\t<SurfaceTemperature>NaN</SurfaceTemperature>\n\t<Latitude>61°12'52.9572&quot;N</Latitude>\n\t<Longitude>06°33'59.0181&quot;E</Longitude>\n\t<Heading>302.295333221872</Heading>\n\t<Friction>NaN</Friction>\n\t<VegComValues>\n\t\t<VCCounty>Vestland</VCCounty>\n\t\t<VCArea>DRAGSVIK FK X55</VCArea>\n\t\t<VCCountyNo>46</VCCountyNo>\n\t\t<VCRoad>FV013</VCRoad>\n\t\t<VCHP>S1D1</VCHP>\n\t\t<VCLane>1</VCLane>\n\t\t<VCLaneName>1</VCLaneName>\n\t\t<VCLaneWithMetering>true</VCLaneWithMetering>\n\t\t<Distance>0</Distance>\n\t\t<VCMeter>14.344072423939158</VCMeter>\n\t</VegComValues>\n\t<MeasurementRectangle>\n\t\t<Location>\n\t\t\t<X>254</X>\n\t\t\t<Y>1272</Y>\n\t\t</Location>\n\t\t<Size>\n\t\t\t<Width>1620</Width>\n\t\t\t<Height>760</Height>\n\t\t</Size>\n\t\t<X>254</X>\n\t\t<Y>1272</Y>\n\t\t<Width>1620</Width>\n\t\t<Height>760</Height>\n\t</MeasurementRectangle>\n\t<BaseLinePosition>1306</BaseLinePosition>\n\t<BaseLineTickInterval>227</BaseLineTickInterval>\n\t<BaseLineTickOffset>0</BaseLineTickOffset>\n\t<TiltPoint>1341</TiltPoint>\n\t<Tilt>0</Tilt>\n\t<CameraPxWidth>2448</CameraPxWidth>\n\t<CameraPxHeight>2048</CameraPxHeight>\n\t<CameraHeight>1.7</CameraHeight>\n\t<BaselineDistance>10</BaselineDistance>\n\t<GeoTag>\n\t\t<dLatitude>61.214710343813685</dLatitude>\n\t\t<dLongitude>6.5663939242382572</dLongitude>\n\t\t<dAltitude>48.856250803013438</dAltitude>\n\t</GeoTag>\n\t<Surroundings>\n\t\t<EquipmentID>P14</EquipmentID>\n\t\t<Driver>FJERNET</Driver>\n\t\t<CarID>FJERNET</CarID>\n\t\t<Comment/>\n\t</Surroundings>\n\t<SoundFile/>\n\t<Note/>\n\t<Comment/>\n\t<Version>5.0</Version>\n\t<RecorderVersion>8.9.8.6</RecorderVersion>\n</ImageProperties>\n" },
            "exif_reflinkinfo":         { 'type' : 'str', 'skalha' : False, 'eksempel' :  "<?xml version=\"1.0\" ?>\n<AdditionalInfoNorway2 xmlns:xsd=\"http://www.w3.org/2001/XMLSchema\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">\n\t<ActivFileVersion>1</ActivFileVersion>\n\t<RoadInfo>\n\t\t<ReflinkId>384067</ReflinkId>\n\t\t<ReflinkPosition>0.027226146823267947</ReflinkPosition>\n\t\t<RoadIdent>FV13 S1D1 m14</RoadIdent>\n\t</RoadInfo>\n\t<GnssInfo>\n\t\t<Latitude>61.214710343813685</Latitude>\n\t\t<Longitude>6.5663939242382572</Longitude>\n\t\t<Altitude>48.856250803013438</Altitude>\n\t\t<Roll>0.29638936011912509</Roll>\n\t\t<Pitch>1.596333137040062</Pitch>\n\t\t<Heading>302.295333221872</Heading>\n\t\t<Speed>0</Speed>\n\t\t<GeoidalSeparation>45.455001831054688</GeoidalSeparation>\n\t\t<NorthRmsError>0.024499321356415749</NorthRmsError>\n\t\t<EastRmsError>0.02449687197804451</EastRmsError>\n\t\t<DownRmsError>0.023979824036359787</DownRmsError>\n\t\t<RollRmsError>0.015766566619277</RollRmsError>\n\t\t<PitchRmsError>0.015766566619277</PitchRmsError>\n\t\t<HeadingRmsError>0.034934956580400467</HeadingRmsError>\n\t</GnssInfo>\n</AdditionalInfoNorway2>\n" },
            "exif_reflinkid":           { 'type' : 'str', 'skalha' : True, 'eksempel' :  "384067" },
            "exif_reflinkposisjon":     { 'type' : 'str', 'skalha' : True, 'eksempel' :  "0.027226146823267947" },
            "exif_roadident":           { 'type' : 'str', 'skalha' : True, 'eksempel' :  "FV13 S1D1 m14" },
            "exif_roll":                { 'type' : 'str', 'skalha' : False, 'eksempel' :  "0.29638936011912509" },
            "exif_pitch":               { 'type' : 'str', 'skalha' : False, 'eksempel' :  "1.596333137040062" },
            "exif_geoidalseparation":   { 'type' : 'str', 'skalha' : False, 'eksempel' :  "45.455001831054688" },
            "exif_northrmserror":       { 'type' : 'str', 'skalha' : False, 'eksempel' :  "0.024499321356415749" },
            "exif_eastrmserror":        { 'type' : 'str', 'skalha' : False, 'eksempel' :  "0.02449687197804451" },
            "exif_downrmserror":        { 'type' : 'str', 'skalha' : False, 'eksempel' :  "0.023979824036359787" },
            "exif_rollrmserror":        { 'type' : 'str', 'skalha' : False, 'eksempel' :  "0.015766566619277" },
            "exif_pitchrmserror":       { 'type' : 'str', 'skalha' : False, 'eksempel' :  "0.015766566619277" },
            "exif_headingrmserror":     { 'type' : 'str', 'skalha' : False, 'eksempel' :  "0.034934956580400467" },
            "exif_xptitle":             { 'type' : 'str', 'skalha' : False, 'eksempel' :  "Bilde fra ViaPhoto Recorder" },
            "exif_kvalitet":            { 'type' : 'str', 'skalha' : False, 'eksempel' :  "2" },
            "bildeid":                  { 'type' : 'str', 'skalha' : True, 'eksempel' :  "2020-06-02T09.42.46.394862_FV00013_S1D1_m00014" },
            "senterlinjeposisjon":      { 'type' : 'str', 'skalha' : True, 'eksempel' :  "srid=4326;POINT Z( 6.5663939242382572 61.214710343813685 48.856250803013438 )" },
            "detekterte_objekter":      { 'type' : 'str', 'skalha' : False, 'eksempel' :  {} },
            "versjon":                  { 'type' : 'str', 'skalha' : False, 'eksempel' :  "P0.1_K20200616" },
            "mappenavn":                { 'type' : 'str', 'skalha' : False, 'eksempel' :  "Vegbilder/2020/FV00013/S1/D1/F1_2020_06_02" }
        }

    return mal 

def anropnvdbapi( kall, params={} ): 
    """
    Anroper NVDB api V3 

    ARGUMENTS: 
        kall - full URL, eller endepunkt relativ til serveradressen for 
                for NVDB api V3. (f.eks. /veg - endepunktet)

    KEYWORDS: 
        params = { } Dictionary med nøkkelord. For enkle oppslag er dette 
                     overflødig, du kan like greit angi dem i kallet, f.eks. 
                     veg?veglenkesekvens=0.111@972557

    RETURNS
        dictionary med resultater, evt None om det feiler 
    """
    base_url = 'https://nvdbapiles-v3.atlas.vegvesen.no'
    if 'http' not in kall: 
        if kall[0] != '/': 
            kall = '/' + kall 
        kall = base_url + kall 

    headers = { "X-Client" : "nvdbapi.py V3 fra Nvdb gjengen, vegdirektoratet", 
                 "X-Kontaktperson" : "jajens@vegvesen.no", 
                 'Accept': 'application/vnd.vegvesen.nvdb-v3-rev1+json' }

    if params: 
        r = requests.get( kall, params=params, headers=headers )
    else: 
        r = requests.get( kall, headers=headers)

    # print( r.url )

    data = None     
    if r.ok: 
        data = r.json()
        
    return data 

def prosesser_fiksfilnavn( mappenavn, loggfilnavn=None, dryrun=False ):
    """
    Finner og sjekker filnavn opp mot datainnhold for alle json-filer (metadata vegbilder) i angitt mappenavn 

    Søker gjennom alle undermapper og støvsuger etter navn på json-filer som så sendes 
    til funksjonen filks_sjekkfilnavn ( jsondata, filnavn  ) 

    ARGUMENTS: 
        mappenavn 

    KEYWORDS:
        loggfilnavn: None eller tekststreng. Hvis angitt logges filnavn på alle ikke-godkjente filer til dette filnavnet. 
        TODO: IKKE IMPLEMENTERT (ennå)

        dryrun: Boolsk, False (default) | True. Kjører analyseprosessen, men uten å gjøre reelle endringer i (meta)data på disk

    RETURNS:
    Nada 
    """
    logdir  = 'loggdir'
    logname = 'loggnavn'
    duallog.duallogSetup( logdir=logdir, logname=logname) 

    filer = finnfiltype(mappenavn, filetternavn='.json')
    logging.info( 'Klar til å sjekke/fikse filnavn for ' + str( len( filer )) + ' filer under ' + mappenavn  )
    antall_fiksa = 0
    for filnavn in filer: 
        jsondata = lesjsonfil( filnavn )
        (jsondata, filnavn, modified ) = fiks_sjekkfilnavn(jsondata, filnavn, dryrun=dryrun)
        if modified: 
            antall_fiksa += 1
            if not dryrun: 
                skrivjsonfil( filnavn, jsondata)

    oppdatert = 'Fant og fiksa filnavnfeil i '
    if dryrun: 
        oppdatert = 'Fant, men fiksa IKKE filnavnfeil i '

    if antall_fiksa > 0: 
        logging.info( oppdatert + str( antall_fiksa) + ' vegbilder i mappe ' + mappenavn )
    else: 
        logging.info( 'Fant ingen filnavnfeil i ' + mappenavn)        


def prosesser( filnavn, dryrun=False ): 
    """
    Retter opp datafeil og mangler i vegbilde-json

    OVerskriver gammal json-fil hvis nødvendig (dvs kun hvis det er gjort endringer)

    ARGUMENTS
        filnavn - fil- og mappenavn til json-fil med metadata for vegbildet

    KEYWORDS 
        dryrund = False Sett til True for å få detaljert utlisting av alle 
                  endringer som normalt ville blitt gjort (men uten at 
                  endringene faktisk gjennomføres. )


    RETURNS
        Antall filer som er endra- 0 eller 1.  
        
    TODO: 
        Sjekk at vi har veglenkeID og posisjon, hent dem hvis nødvendig. Gjenbruk i så fall data til å fikse exif_roadident og 
        senterlinjeposisjon 
    """

    logdir  = 'loggdir'
    logname = 'loggnavn'
    duallog.duallogSetup( logdir=logdir, logname=logname) 


    fiksa = 0 
    fiksa_filnavn = 0
    skrevet = 0
    jsondata = lesjsonfil( filnavn, ventetid=1)

    # Fikser ting 
    (jsondata, tmp)         = fiks_vegtilknytning( jsondata, filnavn, dryrun=dryrun)
    fiksa += tmp 
    (jsondata, tmp)         = fiks_senterlinjeposisjon( jsondata, filnavn, dryrun=dryrun)
    fiksa += tmp
    (jsondata, tmp)         = fiks_exif_roadident( jsondata, filnavn, dryrun=dryrun)
    fiksa += tmp
    # (jsondata, filnavn, tmp) = fiks_sjekkfilnavn( jsondata, filnavn, dryrun=dryrun) 
    # fiksa_filnavn += tmp

    if dryrun:
        if fiksa > 0: 
            logging.info( 'Dryrun-prosessering: behov for oppdatering av ' +  filnavn)
        else: 
            logging.info( 'Dryrun-prosessering: Ingen feil funnet i ' + filnavn )

    elif fiksa > 0: 
        if sjekkegenskapverdi( jsondata, 'exif_kvalitet', 'int') and int(jsondata['exif_kvalitet']) in [0, 1, 2]: 
            jsondata['exif_kvalitet'] = int( jsondata['exif_kvalitet']) +  0.5 
        elif sjekkegenskapverdi( jsondata, 'exif_kvalitet', 'float'): 
            logging.warning( "Pussig kvalitetsverdi - er fila prosessert før? exif_kvalitet=" + 
                            jsondata['exif_kvalitet'] + ' ' + filnavn)

        skrivjsonfil( filnavn, jsondata )
        logging.info( 'Prosessering - retta mangler: ' + jsondata['bildeid'] + ' ' + filnavn)
        skrevet = 1
    
    try: 
        kvalitetskontroll( jsondata, filnavn )
    except AssertionError as myErr: 
        logging.error( str( myErr) ) 

    if fiksa_filnavn > 0: 
        logging.warning( "Endret feil filnavn på " + str( fiksa_filnavn) + " vegbilder (.jpg, .json, .webp)")

    return skrevet

def fiks_sjekkfilnavn( jsondata, filnavn, dryrun=False):
    """
    Sjekker metadata-innhold mot filnavn. 

    Denne versjonen gjør to ting hvis det er mismatch mellom filnavn og metadata
          1) Logger feil til fil fil (til konsoll, eller  egen, dedikert fil TODO)
          2) Endrer exif_filnavn slik at det stememr med det reelle navnet 

    I en senere versjon kan vi vurdere å evt døper om bildefiler + metadata. Kanskje. 

    TODO: Logge feil direkte til fil? 

    ARGUMENTS
        jsondata:  dictionary, metadata lest fra jsonfil

        filnavn: Filnavn til json-fil med metadata 

    KEYWORDS
        dryrun: Boolsk, False (default), True. Hvis True så gjøres ingen reelle endringer i jsondata

    RETURNS 
        jsondata - dictionary med metadata lest fra filnavn, evt oppdatert med riktig filnavn hvis nødvendig
                    (og ikke dryrun)
        filnavn - uendret
        modified - boolsk, True hvis jsondata er oppdatert. 
    """ 

    modified = False 

    jpgfilnavn = os.path.splitext( os.path.split( filnavn )[1] )[0] + '.jpg'
    feil = [ ]

    # Utleder dataverdier fra reelt filnavn og jsondata-filnavn
    fndata = filnavndata( filnavn )
    jsdata = filnavndata( jsondata['exif_filnavn']) 

    # Sjekker om filnavn stemmer 
    if jsondata['exif_filnavn'].lower()  !=  jpgfilnavn.lower(): 
        feil.append( 'Endrer filnavn JSON-metadata' )
        modified = True 
        
        if not dryrun: 
            jsondata['exif_filnavn'] = jpgfilnavn
    
    # Sjekker dataverdier 
    feil_dataverdi = []
    if fndata and jsdata: 
        for tagg in ['fylke', 'vegkat', 'vegstat', 'vegnr', 'hp', 'meter']: 
            if str( fndata[tagg] ).lower() != str( jsdata[tagg]).lower(): 
                feil_dataverdi.append( tagg + ': ' + str( fndata[tagg]) + ' vs ' + str( jsdata[tagg]) )

        if len( feil_dataverdi ) > 0: 
            feil.append(  ', '.join( feil_dataverdi  )  )

    elif fndata: 
        feil.append( 'JSON-data filnavn har ugyldig syntaks: ' + os.path.split( json['exif_filnavn'])[1] )
    elif jsdata: 
        feil.append( 'Reelt filnavn har ugyldig syntaks')
    else:
        feil.append( 'Både JSON-data filnavn og reelt filnavn har ugyldig syntaks')

    if len( feil) > 0: 
        modified = True 
        # TODO: Logge filnavn til fil? 
        feil.append( filnavn )
        logging.info( 'Filnavn-feil: ' + ', '.join(  feil  )  )

    return (jsondata, filnavn, modified)

# def lagfilnavn( jsondata, filnavn): 
#     """
#     Lager nytt (og korrekt!) filnavn ut fra metadata, uten filetternavn (.json, .jpg)

#     ARGUMENTS
#         jsondata - dictionary med metadata
        
#         filnavn - string, eksisterende (gammelt) filnavn (for logging/feilsøking om det går galt)
#     KEYWORDS: 
#         None 

#     RETURNS: 
#         filnavn - tekststreng med nytt filnavn, eller None hvis det feiler
#     """ 
#     try: 
#         if jsondata['exif_vegkat'].upper() in ['E', 'R']: 
#             padding = 3
#         else: 
#             padding = 5
        
#         filnavn = 'Fy' + str(jsondata['exif_fylke']).zfill(2)                + '_' + \
#                     jsondata['exif_vegkat'].upper() + jsondata['exif_vegstat'].lower() + \
#                     str(jsondata['exif_vegnr']).zfill(padding)               + '_' + \
#                     'hp' + str( jsondata['exif_hp']).zfill(3)                + '_' + \
#                     'f'  + str( jsondata['exif_felt'])


#     except KeyError as e: 
#         logging.error(  str(e) + 'Klarte ikke lage nytt filnavn for fil: ' + filnavn )
#         return None 

#     else: 
#         return filnavn 



def fiks_exif_roadident( jsondata, filnavn, dryrun=False ):
    """
    Hvis den mangler - henter exif_roadident fra NVDB api V3 

    ARGUMENTS: 
        jsondata - dictionary med metadata for et vegbilde

    KEYWORDS 
        dryrun = False. Bruk dryrun=True for detaljert info om hvilke endringer som blir gjort 
                        i hvilke filer (men uten at endringene faktisk gjennomføres)

    RETURNS: 
        tuple with (jsondata, modified) hvor modified = 0 (uendret) eller 1 (endret)
        
        Skriver IKKE til disk, det gjør rutina som kaller denne funksjonen

    """

    modified = 0 
    if not sjekkegenskapverdi( jsondata, 'exif_roadident', 'str' ): 
        if sjekkegenskapverdi( jsondata, 'exif_reflinkid', 'int' ) and \
            sjekkegenskapverdi( jsondata, 'exif_reflinkposisjon', 'float'): 

            data = anropnvdbapi( 'veg?veglenkesekvens=' + jsondata['exif_reflinkposisjon'] + 
                                '@' + jsondata['exif_reflinkid'] )

            if data and 'vegsystemreferanse' in data and 'kortform' in data['vegsystemreferanse']: 
                jsondata['exif_roadident'] = data['vegsystemreferanse']['kortform']
                modified = 1 

                if dryrun: 
                    logging.info( 'Dryrun - fikser egenskapverdi exif_roadident i fil: ' + filnavn )

            else: 
                logging.error( 'fiks_exif_roadident: Mangelfulle data ved oppslag på veglenkeposisjon: ' + filnavn)
  
    return ( jsondata, modified)

def fiks_senterlinjeposisjon( jsondata, filnavn, dryrun=False ): 
    """
    Hvis den mangler - henter senterlinjeposisjon fra NVDB api V3 


    Hvis vi mangler data for senterlinjeposisjon så vil vi også sjekke exif_roadident og 
    evt rette den også.  Hensikten er at vi kun henter data fra NVDB api 1 gang, ikke flere. 

    ARGUMENTS: 
        jsondata - dictionary med metadata for et vegbilde

    KEYWORDS 
        dryrun = False. Bruk dryrun=True for detaljert info om hvilke endringer som blir gjort 
                        i hvilke filer (men uten at endringene faktisk gjennomføres)

    RETURNS: 
        tuple with (jsondata, modified) hvor modified = 0 (uendret) eller 1 (endret)
        
        Skriver IKKE til disk, det gjør rutina som kaller denne funksjonen

    """

    modified = 0 
    if not sjekkegenskapverdi( jsondata, 'senterlinjeposisjon', 'str' ): 
        if sjekkegenskapverdi( jsondata, 'exif_reflinkid', 'int' ) and \
            sjekkegenskapverdi( jsondata, 'exif_reflinkposisjon', 'float'): 

            data = anropnvdbapi( 'veg?veglenkesekvens=' + jsondata['exif_reflinkposisjon'] + 
                                '@' + jsondata['exif_reflinkid'] )

            if data and 'vegsystemreferanse' in data and 'kortform' in data['vegsystemreferanse']: 
                jsondata['senterlinjeposisjon'] = 'srid=5973;' + data['geometri']['wkt']
                modified = 1 

                if dryrun: 
                    logging.info( 'Dryrun - fikser egenskapverdi senterlinjeposisjon i fil: ' + filnavn )

                if not sjekkegenskapverdi( jsondata, 'exif_roadident', 'str'):
                    jsondata['exif_roadident'] = data['vegsystemreferanse']['kortform']
                    modified = 1 

                    if dryrun: 
                        logging.info( 'Dryrun - fikser egenskapverdi exif_roadident i fil: ' + filnavn )

            else: 
                logging.error( 'fiks_senterlinjeposisjon: Mangelfulle data ved oppslag på veglenkeposisjon: ' + filnavn)

    return ( jsondata, modified)    


def fiks_vegtilknytning( jsondata, filnavn, dryrun=False ): 
    """
    Hvis den mangler - henter ID og posisjon på lenkesekvens (ved oppslag på bildeposisjon)


    Hvis vi mangler data for vegtilknytning så sjekker vi også og evt oppdaterer data for 
    senterlinjeposisjon og exif_roadident. 
    Hensikten er at vi kun henter data fra NVDB api 1 gang, ikke flere. 

    ARGUMENTS: 
        jsondata - dictionary med metadata for et vegbilde

    KEYWORDS 
        dryrun = False. Bruk dryrun=True for detaljert info om hvilke endringer som blir gjort 
                        i hvilke filer (men uten at endringene faktisk gjennomføres)

    RETURNS: 
        tuple with (jsondata, modified) hvor modified = 0 (uendret) eller 1 (endret)
        
        Skriver IKKE til disk, det gjør rutina som kaller denne funksjonen

    """

    modified = 0 
    if not sjekkegenskapverdi( jsondata, 'exif_reflinkid', 'int' ) or not sjekkegenskapverdi( jsondata, 'exif_reflinkposisjon', 'float'): 
        if sjekkegenskapverdi( jsondata, 'exif_gpsposisjon', 'str' ): 

            pos = jsondata['exif_gpsposisjon'].split()

            data = anropnvdbapi( 'posisjon?lon=' + pos[2] + '&lat=' + pos[3] ) 
            if data: 
                data = data[0]

            if data and 'veglenkesekvens' in data and 'veglenkesekvensid' in data['veglenkesekvens'] and 'relativPosisjon' in data['veglenkesekvens']: 

                jsondata['exif_reflinkid'] = data['veglenkesekvens']['veglenkesekvensid']
                jsondata['exif_reflinkposisjon'] = data['veglenkesekvens']['relativPosisjon']
                modified = 1
                if dryrun and modified: 
                    logging.info( 'Dryrun - fikser vegtilknytning (exif_reflinkid, exif_reflinkposisjon, senterlinjeposisjon, exif_roadident) for ' + filnavn  )

                if not sjekkegenskapverdi( jsondata, 'senterlinjeposisjon', 'str' ): 
                    if 'geometri' in data and 'wkt' in data['geometri']: 
                        jsondata['senterlinjeposisjon'] = 'srid=5973;' + data['geometri']['wkt']
                    else: 
                        logging.error( 'fiks_vegtilknytning - mangler gyldige geometridata ved oppslag på bildets GPS-posisjon: ' + filnavn)

                if not sjekkegenskapverdi(  jsondata, 'exif_roadident', 'str'):
                    if 'vegsystemreferanse' in data and 'kortform' in data['vegsystemreferanse']: 
                        jsondata['exif_roadident'] = data['vegsystemreferanse']['kortform']
                    else: 
                        logging.error( 'fiks_vegtilknytning - mangler gyldig vegsystemreferanse ved oppslag på bildets GPS-posisjon: ' + filnavn )

            else: 
                logging.error( 'fiks_vegtilknytning - mangelfulle data ved oppslag på bildets GPS-posisjon: ' + filnavn)

        else: 
            logging.error( 'fiks_vegtilknytning: Mangler GPS posisjon i metadata: ' + filnavn )


            # if data and 

    # if not sjekkegenskapverdi( jsondata, 'senterlinjeposisjon', 'str' ): 
    #     if sjekkegenskapverdi( jsondata, 'exif_reflinkid', 'int' ) and \
    #         sjekkegenskapverdi( jsondata, 'exif_reflinkposisjon', 'float'): 

    #         data = anropnvdbapi( 'veg?veglenkesekvens=' + jsondata['exif_reflinkposisjon'] + 
    #                             '@' + jsondata['exif_reflinkid'] )

    #         if data and 'vegsystemreferanse' in data and 'kortform' in data['vegsystemreferanse']: 
    #             jsondata['senterlinjeposisjon'] = 'srid=5973;' + data['geometri']['wkt']
    #             modified = 1 

    #             if dryrun: 
    #                 logging.info( 'Dryrun - fikser egenskapverdi senterlinjeposisjon i fil: ' + filnavn )

    #             if not sjekkegenskapverdi( jsondata, 'exif_roadident', 'str'):
    #                 jsondata['exif_roadident'] = data['vegsystemreferanse']['kortform']
    #                 modified = 1 

    #                 if dryrun: 
    #                     logging.info( 'Dryrun - fikser egenskapverdi exif_roadident i fil: ' + filnavn )



    return ( jsondata, modified)    

def finnfiltype( mappenavn, filetternavn='.json' ):
    """
    finn alle filer med angitt fil-etternavn (default=.json) i en mappe (og evt undermapper)

    Returnerer liste med alle filer med dette etternavnet

    ARGUMENTS:
        mappenavn - katalogen vi skal lete i

    KEYWORDS: 
        filetternavn='.json' (default) Filetternavnet vi leter etter

    RETURNS: 
        Liste med sti (mappenavn + filnavn) til alle filer av denne typen 
    """

    filer = [ ]

    for root, dirs, files in os.walk(mappenavn):
        for f in files:
            if os.path.splitext(f)[1] == filetternavn:
                filer.append(  os.path.join(root, f) )
    
    return filer 

def prosessermappe( mappenavn, **kwargs ): 
    """
    Finner og prsoesserer alle json-filer (metadata vegbilder) i angitt mappenavn 

    Søker gjennom alle undermapper og støvsuger etter navn på json-filer som så sendes 
    til funksjonen prosesser( filnavn ) 

    ARGUMENTS: 
        mappenavn 

    KEYWORDS:
        Hva som helst - alle nøkkelord blir alle videresendt til funksjonen prosesser

    RETURNS:
        Nada 
    """

    logdir  = 'loggdir'
    logname = 'loggnavn'
    duallog.duallogSetup( logdir=logdir, logname=logname) 

    t0 = datetime.now() 

    filer = finnfiltype(mappenavn, filetternavn='.json')

    logging.info( 'Prosessermappe- klar til å prosessere ' + str( len(filer)) +  ' metadata-filer under ' + mappenavn)
    antall_fiksa = 0
    for filnavn in filer: 
        antall_fiksa += prosesser( filnavn, **kwargs)

    tidsbruk = datetime.now() - t0 
    logging.info( 'Prosessermappe - fiksa ' + str( antall_fiksa) + ' filer under ' + mappenavn + ' tidsbruk: ' + str( round( tidsbruk.total_seconds() ) ) + ' sekund'  )

def finnundermapper( mappenavn, typeprosess='posisjon', huggMappeTre=None, firstIterasjon=True, **kwargs):
    """
    Deler et (potensielt kjempedigert) mappetre i mindre underkataloger. 

    Hensikten er å unngå å prøve å finne millionvis av json-filer i en katalog. I stedet
    finner vi alle underkataloger (og evt underkataloger til dem igjen), inntil et nærmere angitt 
    nivå relativt under rot-mappa. 

    Parameteren huggMappeTre angir hvor mange nivåer av underkataloger vi skal dele opp med. 

    ARGUMENTS: 
        mappenavn - navn på katalogen vi skal støvsuge for metadata-filer (json)
    
    KEYWORDS: 
        huggMappeTre: None, 0 eller antall nivåer vi skal gå nedover 
                     før vi sender under(under)katalogen til prosessermappe( underkatalog)

        typeprosess: tekststreng, 'posisjon' | 'filnavn' | 'alle'. Hva slags type prosess som skal kjøres
                      på metadata. Aktuelle verdier: 
                      'posisjon' (default): Fikser opp i vegtilknytning, finner posisjon etc. 
                      'filnavn'  Sjekker filnavn, logger filnavn-feil og evt retter opp filnavnet i metadata. 

        firstiteration: Holder styr på om vi er første nivå i iterasjonen. Ikke tukle med denne! 
    
    RETURNS: 
        Nada 
    """
    logdir  = 'loggdir'
    logname = 'loggnavn'
    duallog.duallogSetup( logdir=logdir, logname=logname) 

    t0 = datetime.now() 

    if huggMappeTre: 
    
        logging.info( "finner undermapper til: " +  mappenavn ) 
        huggMappeTre = huggMappeTre - 1
        
        folders = [f for f in glob.glob(mappenavn + "/*/")]
        for undermappe in folders: 
            logging.info( "fant undermappe: " + undermappe) 
            finnundermapper( undermappe, huggMappeTre=huggMappeTre, firstIterasjon=False, **kwargs )

    else: 
        logging.info( "Starter proseessering av undermappe: " + mappenavn) 
    
        if typeprosess.lower() in [ 'posisjon', 'alle']: 
            prosessermappe( mappenavn, **kwargs)
        
        if typeprosess.lower() in ['filnavn', 'alle']:
            prosesser_fiksfilnavn( mappenavn, **kwargs)

    if firstIterasjon: 
        tidsbruk = datetime.now() - t0 
        logging.info( "Ferdig med å gå gjennom alle undermapper til " + mappenavn + ", tidsbruk " + str( round( tidsbruk.total_seconds() ) ) + ' sekund'  )


if __name__ == '__main__': 

    mappe = '/mnt/c/data/leveranser/vegbilder/test_filnavn'
    finnundermapper( mappe, huggMappeTre=2, dryrun=True)
    # prosessermappe( mappe) 

    # testing( )
    # prosessermappe( 'testmappetre', dryrun=True)
    # finnundermapper( 'testmappetre', huggMappeTre=2, dryrun=False)
   
    #     fiksa = prosesser( filnavn, dryrun=True)
