"""
Leser filnavn og EXIF-header fra vegbilder og omsetter dette til metadata som skal inn en bildedatabase. 

Metadata-elementer vi fokuserer på: 
1. Geografisk posisjon til bildet (dvs kamera sin posisjon). 
1.1. Viktigst er senterlinje-koordinat utledet fra vegreferanse. 
1.2 Dette kan suppleres med posisjon fra EXIF - header (GPS-posisjon)
1.3 og GPS posisjon nedfelt på senterlinja
1.4 og (ideelt sett, en vakker dag) lager vi en ny kvalitetssikret senterlinje-posisjon 
    (fjerner lineært og 2. ordens offset på strekningen) 

2. Filnavn og UIID (unik ID) for bildet

3. Felt 

4. Retning med/mot metrering (utledet fra felt-informasjon) 

5. Filnavn og UIID til forrige og neste bilde på strekningen 

6. Dato, utledet fra flere kilder
6.1 dato fra fil/mappenavn
6.2 dato fra EXIF-header
6.3 datostempel fil 

7 Øvrige metadata 
7.1 Unik ID for noen av mappene (samlingene). Hensikten er at det blir enklere 
    å gruppere bildene i søk, kvalitetssikring m.m. 
7.1.1 ID felles for alle bilder i en undermappe på laveste nivå. 
     Denne grupperer alle bilder tatt på samme HP, i samme retning (felt), på samme tid
7.1.2 ID felles for alle bilder i nest laveste nivå på hierarkiget. 
     Denne grupperer alle bilder tatt på samme strekning (HP+strekningsnavn). 
7.2 To be written... 

Den aller første versjonen lager en geojson-samling med koordinat fra vegreferanse (punkt 1.1), og øvrige egenskapsverdier 
etter punkt 2-7. Denne geojson-samlingen blir så lest inn i geografisk database  med FME (postgis, oracle spatial). 
"""

import os 
import uuid
import xml.dom.minidom
import json 
import re 
from datetime import datetime
import fnmatch
import sys
import time
import logging

from PIL import Image # Må installeres, pakken heter PILLOW  
from PIL.ExifTags import TAGS, GPSTAGS
import requests # må installeres, rett fram
import xmltodict # Må installeres, rett fram 
import duallog


# import ipdb
def writeEXIFtoFile(imageFileName,pilImage=None,callersLogger=None):
    """
    Leser EXIF og skriver JSON-fil med metadata. Tilpasset firmaet "Signatur" sitt program 'sladd.pyc'.
    Denne rutinen må kjøres FØR bildet er sladdet, fordi relevant EXIF-informasjon da slettes.
    Hvis funksjonen fullfører uten feil returneres filnavnet til metadatafila ellers, None.
    Hvis 'callersLogger' ikke er None brukes denne instansen av "logger" til å logge evt feilmelding.
    Det er lagt inn en parameter 'pilImage' denne kan brukes til optimalisering når kallende funksjon (sladd) allerede
    har lest og kan legge ved det aktuelle PIL.Image objektet.
    """
    from pathlib import Path
    imageFileName = Path(imageFileName)
    try:
        metadata = lesexif( imageFileName) 
    except (AttributeError, TypeError, UnicodeDecodeError) as myErr:
        msg = '%s:\n\tlesexif routine failed for %s' % (myErr,imageFileName)
        print(msg)
        if callersLogger is not None:
            callersLogger.error(msg)
        return

    metadata['bildeuiid'] = str( uuid.uuid4() )
    jsonFileName = imageFileName.with_suffix('.json')
    with jsonFileName.open('w', encoding='utf-8') as fw:
        json.dump( metadata, fw, indent=4, ensure_ascii=False)

    return jsonFileName

def indekserbildemappe( datadir, overskrivGammalJson=False ): 
    """
    Finner alle mapper med vegbilder og omsetter til metadata 
    
    En mappe = en strekning med veg bilder/fylker/
    
    Mappestruktur = <FYLKESNR> / <ÅR> / <FYLKESNR>_<Vegkategori><vegstatus><vegnummer> / ... 
                    <HP>_<Strekningsnavn> / <FELT>_yyyy_mm_dd / (mappe med vegbilder) 
    
    Traverserer denne mappestrukturen og sjekker syntaks for hvert nivå. Kun undermapper der 
    navnet er ihht syntaks blir med videre. Underveis komponeres de metadata-elementen vi ønsker 
    oss, utledet fra filnavnet. Til sist leses mappen på laveste nivå, der bildene ligger, sortert 
    etter filnavn, dvs etter økende (felt 1, med metrering) eller synkende (felt 2, mot metrering) 
    meterverdier.
    """ 
    
    t0 = datetime.now()
    countNyeIndeksertebilder = 0
    countAlleredeIndeksert = 0 
    countOverskrevet = 0 
     
    # Finner alle mapper med jpg-bilder: 
    folders = set(folder for folder, subfolders, files in os.walk(datadir) for file_ in files if os.path.splitext(file_)[1] == '.jpg')
    
    for mappe in folders: 
        logging.info("Leter i mappe " + mappe) 
        templiste = []

        bildefiler = findfiles( 'fy*hp*m*.jpg', where=mappe) 
        meta_datafangst_uuid = str( uuid.uuid4() )
        
        # Finner feltinformasjon ut fra mappenavn F1_yyyy_mm_dd 
        feltnr = 1 # Default
        (rotmappe, feltmappe) = os.path.split( mappe) 
        feltmappebiter = feltmappe.split( '_') 
        meta_kjfelt = feltmappebiter[0]
        
        if len( feltmappebiter) != 4 or meta_kjfelt[0].upper() != 'F': 
            logging.warning( "QA-feil: Feil mappenavn, forventer F<feltnummer>_<år>_<mnd>_<dag> " + mappe) 
        try: 
            feltnr = int( re.sub( "\D", "", meta_kjfelt )) 
        except ValueError:
            logging.warning( 'QA-feil: Klarte ikke finne feiltinformasjon for mappe ' + mappe) 
        
        if feltnr % 2 == 0:
            meta_retning = 'MOT'
            bildefiler.sort( reverse=True)
        else: 
            meta_retning = 'MED'
            bildefiler.sort() 
       
        for etbilde in bildefiler: 
            
            # Henter relevante data fra EXIF-header 
            try: 
                metadata = lesexif( os.path.join( mappe, etbilde )) 
            except (AttributeError, TypeError, UnicodeDecodeError, OSError) as myErr: 
                logging.warning( ' '.join( [ 'QA-feil: Kan ikke lese EXIF-header fra bildefil', 
                                            os.path.join( mappe, etbilde), str(myErr) ] ) ) 
            
            else: 

                bildefilnavn =  os.path.join( mappe, etbilde) 
                
                # Legger viatech-xml'en sist
                imageproperties = metadata.pop( 'exif_imageproperties' ) 
                            
                # Unik ID for hvert bilde
                metadata['bildeuiid'] = str( uuid.uuid4() )
                
                
                # Legger viatech-xml'en sist
                metadata['exif_imageproperties' ] = imageproperties
 
                jsonfilnavn = os.path.splitext( bildefilnavn)[0]  +  '.json' 
                if (not os.path.isfile( jsonfilnavn)) or overskrivGammalJson:  
                    if os.path.isfile( jsonfilnavn):
                        countOverskrevet += 1
                    
                    with open( jsonfilnavn, 'w', encoding='utf-8') as f: 
                        json.dump( metadata, f, indent=4, ensure_ascii=False) 
                    countNyeIndeksertebilder += 1

                else: 
                    countAlleredeIndeksert += 1
    
    dt = datetime.now() - t0
    logging.info( ' '.join( [ "laget metadata for", str( countNyeIndeksertebilder) , "bilder på", str( dt.total_seconds()) , 'sekunder' ] ) ) 
    logging.info( ' '.join( [ "Beholdt", str( countAlleredeIndeksert) , "metadata for bilder som allered var prosessert" ] ) )
    logging.info( ' '.join( [ "Overskrev", str( countOverskrevet) , "json-filer med eldre metadata" ] ) )

    

def findfiles(which, where='.'):
    '''
    Returns list of filenames from `where` path matched by 'which'
    shell pattern. Matching is case-insensitive.
    
    https://gist.github.com/techtonik/5694830
    snippet is placed into public domain by
    anatoly techtonik <techtonik@gmail.com>
    http://stackoverflow.com/questions/8151300/ignore-case-in-glob-on-linux

    EXAMPLES: 
        findfiles('*.ogg')
        findfiles( '*.jpg', where='denne_mappen/undermappe') 
    '''

    # TODO: recursive param with walk() filtering
    rule = re.compile(fnmatch.translate(which), re.IGNORECASE)

    return [name for name in os.listdir(where) if rule.match(name)]



def fiskFraviatechXML(imagepropertiesxml): 
    """
    Leser relevante data fra viatech XML header. 
    """ 
    
    # with open( 'imageproperties.xml') as f: 
        # imagepropertiesxml  = f.readlines()

    ip = xmltodict.parse( imagepropertiesxml) 
    
    
    
    dLat = ip['ImageProperties']['GeoTag']['dLatitude']
    dLon = ip['ImageProperties']['GeoTag']['dLongitude']
    dAlt = ip['ImageProperties']['GeoTag']['dAltitude']
    
    try: 
        heading = ip['ImageProperties']['Heading'] 
    except KeyError:
        heading = None

    try: 
        speed    = ip['ImageProperties']['Speed']
    except KeyError:
        speed = None
    
    if speed == 'NaN': 
        speed = None
        
    if heading == 'NaN': 
        heading == None
    
    ewkt = ' '.join( [ 'srid=4326;POINT Z(', dLon, dLat, dAlt, ')' ] ) 
    
    tidsstempel = ip['ImageProperties']['@Date']
    kortdato = tidsstempel.split('T')[0] 
    exif_veg = ip['ImageProperties']['VegComValues']['VCRoad']
    
    # Pent formatterte mappenavn 
    mappenavn = re.sub( r'\\', '/', ip['ImageProperties']['ImageName'] )
    mapper = mappenavn.split('/') 
    
    if len( exif_veg) >= 3:
        exif_vegnr   = exif_veg[2:]
        exif_vegstat = exif_veg[1]
        exif_vegkat  = exif_veg[0]
    else: 
        exif_vegnr   = exif_veg
        exif_vegstat = None
        exif_vegkat  = None 
    
    lovlig_vegstatus = ["S", "H", "W", "A", "P", "E", "B", "U", "Q", "V", "X", "M", "T", "G" ]
    lovlig_vegkat = ["E", "R", "F", "K", "P", "S" ] 

    if exif_vegstat not in lovlig_vegstatus or exif_vegkat not in lovlig_vegkat: 
        # logging.info( ' '.join( [ 'VCRoad=', exif_veg, 'følger ikke KAT+STAT+vegnr syntaks:', mappenavn ] ) ) 
        print( 'VCRoad=', exif_veg, 'følger ikke KAT+STAT+vegnr syntaks:', mappenavn )
        
    
    retval =  { 
                'exif_tid' : tidsstempel,
                'exif_dato' : kortdato,
                'exif_speed' : speed, 
                'exif_heading' : heading, 
                'exif_gpsposisjon' : ewkt, 
                'exif_strekningsnavn' : ip['ImageProperties']['VegComValues']['VCArea'], 
                'exif_fylke'          : ip['ImageProperties']['VegComValues']['VCCountyNo'], 
                'exif_vegkat'        : exif_vegkat,
                'exif_vegstat'       : exif_vegstat,
                'exif_vegnr'         : exif_vegnr, 
                'exif_hp'            : ip['ImageProperties']['VegComValues']['VCHP'], 
                'exif_meter'            : ip['ImageProperties']['VegComValues']['VCMeter'], 
                'exif_feltkode'            : ip['ImageProperties']['VegComValues']['VCLane'], 
                'exif_mappenavn'    :  '/'.join( mapper[0:-1] ),
                'exif_filnavn'      : mapper[-1],
                'exif_strekningreferanse' : '/'.join( mapper[-4:-2]),
                'exif_imageproperties'    : imagepropertiesxml
          
                }
                
    return retval 
    

 
def lesexif( filnavn): 
    """
    Omsetter Exif-header til metadata for bruk i bildedatabase

    """
    exif = get_exif( filnavn) 
    
    labeled = get_labeled_exif( exif) 

    # Fisker ut XML'en som er stappet inn som ikke-standard exif element
    xmldata = pyntxml( labeled) 

    # Fisker ut mer data fra viatech xml
    viatekmeta = fiskFraviatechXML( xmldata) 
    
    ## Omsetter Exif GPSInfo => lat, lon desimalgrader, formatterer som EWKT
    ## Overflødig - bruker (lat,lon,z) fra viatech xml 
    # try: 
        # geotags = get_geotagging(exif)
    # except ValueError: 
        # ewkt = ''
        # print( 'kan ikke lese geotag', filnavn) 
    # else: 
        # (lat, lon) = get_coordinates( geotags) 
        # ewkt = 'srid=4326;POINT(' + str(lon) + ' ' + str(lat) + ')'    

    # Bildetittel - typisk etelleranna med viatech Systems 
    XPTitle = ''
    if 'XPTitle' in labeled.keys(): 
        XPTitle = labeled['XPTitle'].decode('utf16')
    
    viatekmeta['exif_xptitle'] = XPTitle 
                   
    return viatekmeta

#% -------------------------------------------------------
# 
# Hjelpefunksjoner for diverse exif-manipulering
#
# ---------------------------------------------------
def get_decimal_from_dms(dms, ref):
    """
    Konverterer EXIF-grader til desimalgrader

    Fra https://developer.here.com/blog/getting-started-with-geocoding-exif-image-metadata-in-python3
    """ 


    degrees = dms[0][0] / dms[0][1]
    minutes = dms[1][0] / dms[1][1] / 60.0
    seconds = dms[2][0] / dms[2][1] / 3600.0

    if ref in ['S', 'W']:
        degrees = -degrees
        minutes = -minutes
        seconds = -seconds

    return round(degrees + minutes + seconds, 6)

def get_coordinates(geotags):
    """
    Fisker koordinater ut av EXIF-taggene

    Fra https://developer.here.com/blog/getting-started-with-geocoding-exif-image-metadata-in-python3
    """

    lat = get_decimal_from_dms(geotags['GPSLatitude'], geotags['GPSLatitudeRef'])

    lon = get_decimal_from_dms(geotags['GPSLongitude'], geotags['GPSLongitudeRef'])

    return (lat,lon)
    
def pyntxml( exif_labelled): 
    """
    Fjerner litt rusk fra den XML'en som viatech legger i Exif-header. Obfuskerer fører og bilnr
    """
    
    try: 
        raw = exif_labelled[None]
    except KeyError: 
        return None
    else: 
        # fjerner '\ufeff' - tegnet aller først i teksten 
        xmlstr = raw.decode('utf8')[1:]
        plainxml = xml.dom.minidom.parseString(xmlstr)
        prettyxml = plainxml.toprettyxml()
        
        # Obfuskerer
        prettyxml = re.sub(r'Driver>.*<', 'Driver>FJERNET<', prettyxml)
        prettyxml = re.sub(r'CarID>.*<', 'CarID>FJERNET<', prettyxml)
        prettyxml = re.sub(r'Comment>.*<', 'Comment>FJERNET<', prettyxml)
        
        return prettyxml
        
    
    
def get_geotagging(exif):
    """
    Bedre håndtering av geotag i exif-header
    
    Fra https://developer.here.com/blog/getting-started-with-geocoding-exif-image-metadata-in-python3
    """
    if not exif:
        raise ValueError("No EXIF metadata found")

    geotagging = {}
    for (idx, tag) in TAGS.items():
        if tag == 'GPSInfo':
            if idx not in exif:
                raise ValueError("No EXIF geotagging found")

            for (key, val) in GPSTAGS.items():
                if key in exif[idx]:
                    geotagging[val] = exif[idx][key]

    return geotagging


def get_exif(filename):
    image = Image.open(filename)
    image.verify()
    return image._getexif()

def get_labeled_exif(exif):
    
    labeled = {}
    for (key, val) in exif.items():
        labeled[TAGS.get(key)] = val

    return labeled
    
if __name__ == '__main__':

    overskrivGammalJson = False
    datadir = None 
    logdir = 'log' 
    logname='lesexif_' 
    
    
    versjonsinfo = "Versjon 3.1 den 17. juni 2019 kl 22:37"

    print( versjonsinfo ) 
    if len( sys.argv) < 2: 
        print( "BRUK:\n")
        print( 'vegbilder_lesexif.exe "../eksempelbilder/"')
        print( 'vegbilder_lesexif.exe "../eksempelbilder/" overskriv\n') 
        print( '\t... eller ha oppsettdata i json-fil\n')
        print( 'vegbilder_lesexif.exe oppsettfil_lesexif.json') 
        print( 'vegbilder_lesexif.exe oppsettfil_lesexif.json overskriv\n') 
        print( 'Parameter #2 overskriv vil overskrive eventuelle metadata-elementer', 
                'som finnes fra før (bildemappe/bildefilnavn.json)\n' ) 
        time.sleep( 1.5) 
        
    else: 
        if len( sys.argv ) > 2 and 'overskriv' in sys.argv[2].lower(): 
            overskrivGammalJson = True
            print( "Beskjed om å overskrive gamle *.json-metadata funnet i argument", 
                sys.argv[2] ) 
            
        
        if '.json' in sys.argv[1][-5:].lower(): 
            print( 'vegbilder_lesexif: Leser oppsettfil fra', sys.argv[1] ) 
            with open( sys.argv[1]) as f: 
                oppsett = json.load( f) 
            
            if 'logdir' in oppsett.keys():
                logdir = oppsett['logdir']

            if 'logname' in oppsett.keys():
                logname = oppsett['logname']

            duallog.duallogSetup( logdir=logdir, logname=logname) 
            logging.info( versjonsinfo ) 
            
            logging.info( "Bruker oppsettfil " + sys.argv[1] ) 

            
            if 'datadir' in oppsett.keys(): 
                datadir = oppsett['datadir']

            if 'overskrivGammalJson' in oppsett.keys(): 
                tmp_overskriv = oppsett['overskrivGammalJson']
                if tmp_overskriv: 
                    logging.info( ' '.join( [ 'Beskjed om å overskrive gamle *.json metadata funnet i ', 
                        sys.argv[1] ] ) ) 
                
                if overskrivGammalJson and not tmp_overskriv: 
                    logging.warning( ' '.join( [ 'Konflikt mellom parametre på kommandolinje', 
                        '(overskriv gamle json-metadata) og oppsettfil', sys.argv[1], 
                        '(IKKE overskriv)' ] ) )
                    logging.warning( 'Stoler mest på kommandolinje, overskriver gamle *.json metadata')
                else: 
                    overskrivGammalJson = tmp_overskriv
                
        else: 
            datadir = sys.argv[1] 
            duallog.duallogSetup( logdir=logdir, logname=logname) 
            logging.info( versjonsinfo ) 
            
            
        if not datadir: 
            logging.error( 'Påkrevd parameter "datadir" ikke angitt, du må fortelle meg hvor vegbildene ligger') 
        else: 
            logging.info( 'Lager metadata for vegbilder i mappe ' + datadir ) 
            if overskrivGammalJson: 
                logging.info( 'Overskriver alle eldre metadata som måtte finnes fra før') 
                
            if not isinstance( datadir, list): 
                datadir = [ datadir ]   
  
            for idx, enmappe in enumerate( datadir ):
                logging.info( ' '.join( [ "Prosesserer mappe", str(idx+1), 'av', str(len(datadir)) ] ) ) 
                indekserbildemappe( enmappe, overskrivGammalJson=overskrivGammalJson) 

    print( versjonsinfo ) 

    # datadir = '../bilder/testdataRegS/'
    # datadir = '../bilder/litensample_regS/06/2018/06_Ev134/Hp422_Myntbrua_rkj_E134_X_fv__87/F1_2018_06_21'
