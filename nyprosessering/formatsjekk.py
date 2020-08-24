# Standard library 
import json
import logging
import os 
from pathlib import Path
from pydoc import locate
from datetime import datetime
import dateutil.parser

import pdb

# Well known 3rd party libraries

# Custom libraries
import duallog
from flyttvegbilder_v54 import lesjsonfil
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
    data_keys = set( )
    duplicate_keys = set( )
    for akey in jsondata.keys(): 
        if akey in data_keys: 
            duplicate_keys.add( akey)
        else: 
            data_keys.add( akey )

    # Har vi duplikater? 
    assert len( duplicate_keys ) == 0, ' '.join( ['skjemafeil DUBLETT',  *duplicate_keys, filnavn] )

    # Mangler vi noen tagger? 
    diff1 = mal_keys - data_keys
    assert len( diff1 ) == 0, ' '.join( ['skjemafeil MANGLER tagg',  *diff1, filnavn] )

    # Overflødige tagger? 
    diff2 = data_keys - mal_keys
    assert len( diff2 ) == 0, ' '.join( ['skjemafeil EKSTRA tagg',  *diff2, filnavn] )

def sjekktagg( jsondata, taggnavn, taggtype ): 
    """
    Sjekker om en taggen har fornuftig verdi og datatype 

    ARGUMENTS
        jsondata - dictionary med de dataene vi skal sjekke

        taggnavn - egenskapverdi som skal sjekkes

        taggtype - Navn på  datatype som skal valideres ('int', 'str', 'float', ...)

    Ekstra valideringsregler (regex, numerisk verdi etc) føyes på som nøkkelord-parametre
    
    https://stackoverflow.com/questions/11775460/lexical-cast-from-string-to-type
    """

    retval = False 

    # Finnes og har noe annet enn None-verdi: 
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
            retval = True 

        # Sjekker at vi ikke har flyttallverdi der vi skal ha heltall 
        # Float-verdier numerisk identisk med heltall godtas, dvs 1.0 == 1
        elif taggtype == 'int': 
            if (isinstance( rawdata, float) or isinstance( rawdata, int)) and rawdata == data: 
                retval = True 
            elif isinstance( rawdata, str) and int( rawdata) == data: 
                retval == True 
                
        # Gyldig dato? 
        elif taggtype in [ 'date', 'datetime' ] and isinstance( data, datetime): 
            retval = True
            
        # Alt mulig anna? Har iallfall den datatypen vi skal ha?
        elif isinstance( data, datatype): 
            retval = True 

    return retval 

def kvalitetskontroll( jsondata, filnavn): 
    """
    Kvalitetskontroll av ferdige prosesserte data 

    ARGUMENTS
        jsonmal - dictionary som vi sammenligner med
        
        jsondata - dictionary som skal kvalitetssjekkes
        
        filnavn - Filnavn til jsondata. Brukes til logging
    """
    sjekktagger( jsondata, filnavn)
                            
def testing( testdata='testdata', tempdir='testdata_temp', logdir='test_logdir', logname='test_loggnavn' ):
    """
    Kjører gjennom testdata

    Kopierer mappen med testdata til en midlertidig katalog (som overskrives, hvis den finnes fra før). 
    Anvender deretter alle kvalitetssikrings / kvalitetsheving-rutiner på testdata. 
    """

    duallog.duallogSetup( logdir=logdir, logname=logname) 
    testfiler = findfiles( '*', testdata )
    logging.info( 'Forbereder test\n========')

    Path(  tempdir ).mkdir( parents=True, exist_ok=True )
    for eifil in testfiler: 
        logging.info( 'Kopierer testfil: ' + eifil )
        (rot, filnavn) = os.path.split( eifil )
        kopierfil( eifil, tempdir + '/' + filnavn )

    kopiertefiler = findfiles( '*.json', tempdir)
    # Les mal for json-filer
    jsonmal = vegbildejsonmal( ) 

    for filnavn in kopiertefiler: 
        jsondata = lesjsonfil( filnavn, ventetid=15) 

        try: 
            kvalitetskontroll( jsonmal, jsondata, filnavn) 
        except AssertionError as myErr: 
            logging.error( str( myErr) ) 


def vegbildejsonmal( ): 
    """Returnerer eksempel på gyldig JSON"""

    mal = {
            "exif_tid":                 { 'type' : 'datetime', 'skalha' : True, 'eksempel' :  "2020-06-02T09:42:46.3948628" },
            "exif_dato":                { 'type' : 'date', 'skalha' : True, 'eksempel' : "2020-06-02" },
            "exif_speed":               { 'type' : 'float', 'skalha' : False, 'eksempel' :  "0" },
            "exif_heading":             { 'type' : 'float', 'skalha' : False, 'eksempel' :  "302.295333221872"},
            "exif_gpsposisjon":         { 'type' : 'str', 'skalha' : False, 'eksempel' :  "srid=4326;POINT Z( 6.5663939242382572 61.214710343813685 48.856250803013438 )"},
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
            "senterlinjeposisjon":      { 'type' : 'str', 'skalha' : False, 'eksempel' :  "srid=4326;POINT Z( 6.5663939242382572 61.214710343813685 48.856250803013438 )" },
            "detekterte_objekter":      { 'type' : 'str', 'skalha' : False, 'eksempel' :  {} },
            "versjon":                  { 'type' : 'str', 'skalha' : False, 'eksempel' :  "P0.1_K20200616" },
            "mappenavn":                { 'type' : 'str', 'skalha' : False, 'eksempel' :  "Vegbilder/2020/FV00013/S1/D1/F1_2020_06_02" }
        }

    return mal 
                            
if __name__ == '__main__': 

    logdir  = 'test_loggdir'
    logname = 'test_loggnavn'
    duallog.duallogSetup( logdir=logdir, logname=logname) 

    mappenavn = 'testdata/'
    jsonfiler = findfiles( '*.json', mappenavn) 
    for filnavn in jsonfiler: 
        jsondata = lesjsonfil( filnavn, ventetid=15) 
    
        try: 
            kvalitetskontroll( jsondata, filnavn) 
        except AssertionError as myErr: 
            logging.error( str( myErr) ) 
