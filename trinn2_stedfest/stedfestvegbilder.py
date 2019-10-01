"""
Stefester vegbilder; en liten json-fil med metadata finner vi gyldig vegreferanse da bildet ble tatt
Denne fila blir så oppdatert med vegreferanse-informasjon, veglenkeposisjon og koordinat for senterlinje 
hentet fra Visveginfo-tjensten. 
""" 

import os 
import uuid
import fnmatch 
import re
import glob
import json
from datetime import datetime
import sys
import time
import logging
from xml.parsers.expat import ExpatError


import requests
import xmltodict # Må installeres, rett fram 
import duallog 

def utledMappenavn( mappe ):
    mapper = mappe.split('/') 
    return '/'.join( mapper[-5:-1]) 


def recursive_findfiles(which, where='.'):
    '''
    Returns list of filenames from `where` path matched by 'which'
    shell pattern. Matching is case-insensitive.
    
    https://gist.github.com/techtonik/5694830
    snippet is placed into public domain by
    anatoly techtonik <techtonik@gmail.com>
    http://stackoverflow.com/questions/8151300/ignore-case-in-glob-on-linux

    blandet med eks herfra 
    https://www.bogotobogo.com/python/python_traversing_directory_tree_recursively_os_walk.php 
    EXAMPLES: 
        findfiles('*.ogg')
        findfiles( '*.jpg', where='denne_mappen/undermappe') 
        
        
    '''

    # TODO: recursive param with walk() filtering
    
    
    rule = re.compile(fnmatch.translate(which), re.IGNORECASE)
    
    filnavn = []
    for root, d_names, f_names in os.walk(where): 
        for name in f_names:
            if rule.match(name):
                filnavn.append( os.path.join( root, name) )
               

    # return [name for name in os.listdir(where) if rule.match(name)]
    return filnavn


def anropvisveginfo( url, params, filnavn, proxies='', ventetid=15): 
    """
    Anroper visveginfo og har en del feilhåndtering-logikk. Prøver på ny etter en pause ved nettverksfeil eller overbelastning
    """ 
    
    logging.debug( ' '.join( [ 'Skal anrope visveginfo:', url, str(params), filnavn ] ) )  
    count = 0
    sovetid = 0 
    anropeMer = True 
    while count < 4 and anropeMer: 
        count += 1
        r = requests.get( url, params=params, proxies=proxies) 
        logging.debug( r.url + ' status kode: ' + str( r.status_code ))
        svartekst = r.text
        
        # Tom returverdi = veglenkeposisjon finnes ikke. 
        # XML-dokument med <RoadReference ... = godkjent
        # Alt anna = feilmelding fra server (Unavailable etc...) 
        if 'RoadReference' in svartekst or len( svartekst) == 0: 
            anropeMer = False 
        
        if count > 1 and anropeMer: 
            sovetid = sovetid + count * ventetid
            logging.warning( ' '.join( [ "Visvegionfo-kall FEILET", url, str(params),  filnavn, 'Svar fra Visveginfo:' ] ) )
            logging.warning( svartekst)  
            logging.info( ' '.join( [ "prøver igjen om", str( sovetid), "sekunder" ] ) ) 
            time.sleep( sovetid) 

    return svartekst



def visveginfo_vegreferanseoppslag( metadata, proxies=None, filnavn=''): 
    """
    Mottar et metadata-element, fisker ut det som trengs for å gjøre oppslag på vegreferanse,
    oppdaterer metadata-elementet og sender det tilbake. 
    """ 
    
    fylke = str(metadata['exif_fylke']).zfill(2) 
    kommune = '00' 
    vegnr = str( metadata['exif_vegnr']).zfill(5)
    hp = str(metadata['exif_hp']).zfill(3)
    meter = str(round( float( metadata['exif_meter'] ))).zfill(5) 
    
    vegref = fylke + kommune + metadata['exif_vegkat'] + metadata['exif_vegstat'] + \
            vegnr + hp + meter 
            
    params = { 'roadReference' : vegref, 'ViewDate' : metadata['exif_dato'], 'topologyLevel' : 'Overview' } 
    
    url = 'http://visveginfo-static.opentns.org/RoadInfoService3d/GetRoadReferenceForReference' 

    tekstrespons = anropvisveginfo( url, params, filnavn, proxies=proxies ) 
    try: 
        vvidata = xmltodict.parse( tekstrespons )
    except ExpatError as e: 
        logging.warning( ' '.join( [ 'XML parsing av visveginfo-resultat feiler', 
                        filnavn, str(e), tekstrespons ] ) )

    

    
    # Putter viatech XML sist... 
    exif_imageproperties = metadata.pop( 'exif_imageproperties') 

    if 'ArrayOfRoadReference' in vvidata.keys() and 'RoadReference' in vvidata['ArrayOfRoadReference'].keys(): 

        vvi = vvidata['ArrayOfRoadReference']['RoadReference']

        metadata['senterlinjeposisjon'] = 'srid=25833;POINT Z( ' + \
                                        str( round( float( vvi['RoadNetPosition']['X']), 3)) + ' ' + \
                                        str( round( float( vvi['RoadNetPosition']['Y']), 3))  + ' ' + \
                                        str( round( float( vvi['RoadNetPosition']['Z']), 3)) + ' )'
                      
                      
        metadata['veglenkeid']  = int( vvi['ReflinkOID'] )
        metadata['veglenkepos'] = round( float( vvi['Measure']), 8)
        metadata['feltoversikt']    =  vvi['LaneCode']
        metadata['feltoversikt_perbildedato']     =  vvi['LaneCode']
        metadata['lenkeretning'] =  round( float( vvi['RoadnetHeading']), 3)
        metadata['lenkeretning_perbildedato'] =  round( float( vvi['RoadnetHeading']), 3)
        # metadata['visveginfoparams'] =  params 
        # metadata['visveginfosuksess'] =  True 
        metadata['stedfestet'] = 'JA'
        
        # Legger på vegreferanse-informasjon slik at bildet blir søkbart. 
        metadata['fylke']        = int( vvi['County'] )
        metadata['kommune']      = int( vvi['Municipality'] ) 
        metadata['vegkat']       = vvi['RoadCategory'] 
        metadata['vegstat']      = vvi['RoadStatus']
        metadata['vegnr']        = int( vvi['RoadNumber'] ) 
        metadata['hp']           = int( vvi['RoadNumberSegment'] ) 
        metadata['meter']        = int( vvi['RoadNumberSegmentDistance']) 

        metadata['vegreferansedato'] = params['ViewDate'] 
        
        metadata['feltkode'] = metadata['exif_feltkode']
        if 'filnavn' not in metadata.keys(): 
            metadata['filnavn'] = re.sub( '.jpg', '', metadata['exif_filnavn'] ) 
            metadata['filnavn'] = re.sub( '.JPG', '', metadata['filnavn'] ) 

        metadata['retningsnudd'] = 'ikkesnudd'
        metadata['strekningsreferanse'] = metadata['exif_strekningreferanse']
            
    else: 
        logging.warning( ' '.join( [ 'Ugyldig vegreferanse', vegref, 'for dato', params['ViewDate'], filnavn ] ) ) 
        # metadata['visveginfoparams'] = params
        # metadata['visveginfosuksess'] =  False 
        metadata['stedfestet'] = 'Ugyldig'
       
    metadata['stedfestingdato'] = datetime.today().strftime('%Y-%m-%d')
    metadata['exif_imageproperties'] = exif_imageproperties

    return metadata


def lesjsonfil( filnavn, ventetid=15): 
    """
    Åpner og leser JSON-fil. Tolererer nettverksfeil og tar en pause før vi prøver på ny (inntil 4 ganger
    """ 
    
    meta = None 
    count = 0
    sovetid = 0 
    anropeMer = True 
    maxTries = 4
    while count < maxTries and anropeMer: 
        count += 1
    
        try: 
            with open( filnavn ) as f: 
                meta = json.load(f)    
            
        except UnicodeDecodeError as myErr: 
            logging.warning( ' '.join( [  "Tegnsett-problem, prøver å fikse:", fname, str(myErr) ] ) ) 
        
            try: 
                with open( fname, encoding='latin-1') as f: 
                    text = f.read()
                    textUtf8 = text.encode('utf-8') 
                    meta = json.loads( textUtf8) 
            except UnicodeDecodeError as myErr2:
                logging.warning( ' '.join( [  "Gir opp å fikse tegnsett-problem:", fname, str(myErr2) ] ) ) 
                meta = None
                anropeMer = False
        
        except OSError as myErr: 
            sovetid = sovetid + count * ventetid
            
            if count < maxTries: 
                logging.error( "Lesing av JSON-fil feilet, " + filnavn + " prøver på ny om " + str( sovetid) + " sekunder" ) 
                time.sleep( sovetid) 
            else: 
                logging.error( "Lesing av JSON-fil FEILET " + filnavn + ", gir opp og går videre"   ) 
                logging.error( str( myErr) ) 
                meta = None

 
        else: 
            anropeMer = False
        
     

    return meta 

def skrivjsonfil( filnavn, data, ventetid=15): 
    """
    Skriver dict til json-fil. Tolererer nettverksfeil og tar en pause før vi prøver på ny (inntil 4 ganger)
    """ 
    
    count = 0
    sovetid = 0 
    anropeMer = True 
    maxTries = 4
    while count < maxTries and anropeMer: 
        count += 1

        try: 
            with open( filnavn, 'w', encoding='utf-8') as fw: 
                json.dump( data, fw, ensure_ascii=False, indent=4) 
        except OSError as myErr: 
            sovetid = sovetid + count * ventetid
            
            if count < maxTries: 
                logging.error( "Skriving til fil FEILET " + filnavn + " prøver på ny om " + str( sovetid) + " sekunder" ) 
                time.sleep( sovetid) 
            else: 
                logging.error( "Skriving til fil FEILET " + filnavn + ", gir opp og går videre"  ) 
                logging.error( str(myErr)) 
 
        else: 
            anropeMer = False


def stedfest_jsonfiler( mappe='../bilder/regS_orginalEv134', overskrivStedfesting=False, proxies=None ):
    t0 = datetime.now()
    jsonfiler = recursive_findfiles( 'fy*hp*m*.json', where=mappe) 
    count = 0
    count_suksess = 0 
    count_fatalt = 0 
 
    for (nummer, filnavn) in enumerate(jsonfiler): 
        meta = lesjsonfil( filnavn) 

        if meta: 
            # Stedfester kun dem som ikke er stedfestet fra før: 
            if overskrivStedfesting or (not 'stedfestet' in meta.keys() or       \
                                    ('stedfestet' in meta.keys()                 \
                                        and isinstance( meta['stedfestet'], str) \
                                        and meta['stedfestet'].upper() != 'JA' )): 
                count += 1
                try: 
                    meta = visveginfo_vegreferanseoppslag( meta, proxies=proxies, filnavn=filnavn) 
                except Exception:
                    count_fatalt += 1
                    logging.error( "Fatal feil i visveginfo_referanseoppslag for fil: " + filnavn )
                    logging.exception("Stack trace for fatal feil:")
                else: 
                
                    if meta['stedfestet'] == 'JA' : 
                        count_suksess += 1
                    
                    skrivjsonfil( filnavn, meta) 
                    
            if nummer == 10 or nummer == 100 or nummer % 500 == 0: 
                dt = datetime.now() - t0 
                logging.info( ' '.join( [ 'Stedfester bilde', str( nummer+1), 'av', 
                                        str( len(jsonfiler)), str( dt.total_seconds()) , 'sekunder' ] ) )


 
    dt = datetime.now() - t0
    logging.info( ' '.join( [ 'Prøvde å stedfeste', str( count) , 'av', str( len(jsonfiler)), 
                                'vegbilder på', str( dt.total_seconds()), 'sekunder' ] ) ) 
                                
    diff = len(jsonfiler) - count
    if diff > 0: 
        logging.info( 'Hoppet over ' + str( diff) + ' av ' + str( len( jsonfiler) ) + ' vegbilder' ) 

    diff = count - count_suksess
    if diff > 0: 
        logging.warning( 'Stedfesting FEILET for ' + str( diff) + ' av ' + str( len( jsonfiler) ) + ' vegbilder' ) 
        
    if count_fatalt > 0: 
        logging.error( 'Stedfesting FEILET med ukjent feilsituasjon for ' + str( count_fatalt) + ' vegbilder' ) 

def sorter_mappe_per_meter(datadir, overskrivStedfesting=False): 
    # Finner alle mapper med json-filer, sorterer bildene med forrige-neste logikk
    # 
    # folders = set(folder for folder, subfolders, files in os.walk(datadir) for file_ in files if os.path.splitext(file_)[1] == '.')
    folders = set(folder for folder, subfolders, files in os.walk(datadir) for file_ in files if re.search( "fy[0-9]{1,2}.*hp.*m[0-9]{1,6}.json", file_, re.IGNORECASE)  )

    for mappe in folders: 
        logging.info( "Leter i mappe " +  mappe) 

        templiste = []
        meta_datafangst_uuid = str( uuid.uuid4() )

        jsonfiler = findfiles( 'fy*hp*m*.json', where=mappe) 

        # Finner feltinformasjon ut fra mappenavn F1_yyyy_mm_dd 
        feltnr = 1 # Default
        (rotmappe, feltmappe) = os.path.split( mappe) 
        feltmappebiter = feltmappe.split( '_') 
        meta_kjfelt = feltmappebiter[0]
        
        if len( feltmappebiter) != 4 or meta_kjfelt[0].upper() != 'F': 
            logging.warning( "QA-feil: Feil mappenavn, forventer F<feltnummer>_<år>_<mnd>_<dag> " +  mappe) 
        try: 
            feltnr = int( re.sub( "\D", "", meta_kjfelt )) 
        except ValueError:
            logging.warning( 'QA-feil: Klarte ikke finne feiltinformasjon for mappe ' + mappe) 
        
        if feltnr % 2 == 0:
            meta_retning = 'MOT'
            jsonfiler.sort( reverse=True)
        else: 
            meta_retning = 'MED'
            jsonfiler.sort() 
            
        for eijsonfil in jsonfiler: 
            
            fname = os.path.join( mappe, eijsonfil) 
            lest_OK = False 
            try: 
                with open( fname) as f: 
                    metadata = json.load( f) 
            except UnicodeDecodeError as myErr: 
                logging.warning( ' '.join( [  "Tegnsett-problem, prøver å fikse:", fname, str(myErr) ] ) )  
                
                try: 
                    with open( fname, encoding='latin-1') as f: 
                        text = f.read()
                    textUtf8 = text.encode('utf-8') 
                    metadata = json.loads( textUtf8) 
                except UnicodeDecodeError as myErr2:
                    logging.warning( ' '.join( [  "Gir opp å fikse tegnsett-problem:", fname, str(myErr2) ] ) ) 
                else: 
                    lest_OK = True
                
                
            except OSError as myErr: 
                logging.warning( ' '.join( [  "Kan ikke lese inn JSON-fil", fname, str(myErr) ] ) ) 
            else: 
                lest_OK = True
            
            if lest_OK: 
            
               # Legger viatech-xml'en sist
                imageproperties = metadata.pop( 'exif_imageproperties' ) 
                
                metadata['temp_filnavn'] =  fname

                
                # Retning og feltkode
                metadata['retning'] = meta_retning
                metadata['filnavn_feltkode'] = meta_kjfelt
              
                
                # Utleder riktig mappenavn 
                metadata['mappenavn'] = utledMappenavn( mappe) 
            
                # Unik ID for hvert bilde, og felles ID for alle bilder i samme mappe
                metadata['datafangstuuid'] = meta_datafangst_uuid
                if not 'bildeuiid' in metadata.keys() or not metadata['bildeuiid']: 
                    metadata['bildeuiid'] = str( uuid.uuid4() ) 
                metadata['forrige_uuid'] = None
                metadata['neste_uuid'] = None
                
                
                # Legger til et par tagger for administrering av metadata
                metadata['stedfestet'] = 'NEI'
                metadata['indeksert_i_db'] = None

                # Legger viatech-xml'en sist
                metadata['exif_imageproperties' ] = imageproperties
                
                # Føyer på den korte listen
                templiste.append(  metadata) 

            else: 
                logging.warning( 'Måtte hoppe over ' + fname) 

         # Lenkar sammen den lenkede listen 
        for ii in range( 0, len(templiste)): 
            
            # Forrige element i listen
            if ii > 0 and ii < len(templiste): 
                templiste[ii]['forrige_uuid']    = templiste[ii-1]['bildeuiid']
            
            # Neste element     
            if ii < len(templiste)-1: 
                templiste[ii]['neste_uuid']    = templiste[ii+1]['bildeuiid']

        # Skriver json-fil med metadata til fil
        for jsonfil in templiste:

            filnavn = jsonfil.pop( 'temp_filnavn' ) 
                
            with open( filnavn, 'w', encoding='utf-8') as f: 
                json.dump( jsonfil, f, indent=4, ensure_ascii=False) 

 
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
    
    
def formatvegref( fylke, kommune, vegkat, vegstat, vegnummer, hp, meter): 
    """
    Formatterer en vegreferanse-streng som kan brukes i kall til visveginfo
    """
    
    vegref = str(fylke).rjust(2, '0') + str(kommune).rjust(2, '0') + vegkat.upper() + vegstat.upper() + \
            str(vegnummer).rjust(5, '0') + str(hp).rjust(3, '0') + str(meter).rjust(5, '0') 
    return vegref

 
def test( ): 
    jsonfiler = recursive_findfiles( 'fy*hp*m*.json', where='.') 
    
    with open( jsonfiler[0]) as f: 
        meta = json.load(f)
        
    meta = visveginfo_vegreferanseoppslag( meta) 
    return meta
    
if __name__ == '__main__': 

    datadir = None
    overskrivStedfesting = False
    logdir = 'log' 
    logname='stedfestvegbilder_' 
    proxies = { 'http' : 'proxy.vegvesen.no:8080', 'https' : 'proxy.vegvesen.no:8080'  }

    
    versjonsinfo = "Stedfest vegbilder Versjon 3.2 den 1. okt 2019"
    print( versjonsinfo ) 
    if len( sys.argv) < 2: 

        print( "BRUK:\n")
        print( 'stedfest_vegbilder.exe "../eksempelbilder/"\n')
        print( '\t... eller ha oppsettdata i json-fil\n')
        print( 'stedfest_vegbilder.exe stedfest_vegbilder_oppsettfil.json') 
        time.sleep( 1.5) 
    
    else: 
    
        if len( sys.argv ) > 2 and 'overskriv' in sys.argv[2].lower(): 
            overskrivStedfesting = True
            print('Kommandolinje-argument', sys.argv[2], ' => vil også stedfeste', 
                    'også bilder som er stedfestet fra før' )     
    
        if '.json' in sys.argv[1][-5:].lower(): 
            print( 'vegbilder_lesexif: Leser oppsettfil fra', sys.argv[1] ) 
            with open( sys.argv[1]) as f: 
                oppsett = json.load( f) 

            if 'datadir' in oppsett.keys(): 
                datadir = oppsett['datadir']
                
            if 'logdir' in oppsett.keys():
                logdir = oppsett['logdir']

            if 'logname' in oppsett.keys():
                logname = oppsett['logname']

            duallog.duallogSetup( logdir=logdir, logname=logname) 
            logging.info( versjonsinfo ) 
            
            if 'proxies' in oppsett.keys():
                proxies = oppsett['proxies']
            
            if 'overskrivStedfesting' in oppsett.keys(): 
                tmp_overskriv = oppsett['overskrivStedfesting']
                if tmp_overskriv: 
                    logging.info( 'Beskjed om å overskrive gamle *.json metadata funnet i ' + sys.argv[1] ) 
                
                if overskrivStedfesting and not tmp_overskriv: 
                    logging.warning( ' '.join( [ 'Konflikt mellom parametre på kommandolinje', 
                        '(overskriv gamle json-metadata) og oppsettfil', sys.argv[1], 
                        '(IKKE overskriv)' ] ) ) 
                    logging.warning( 'Stoler mest på kommandolinje, overskriver gamle *.json metadata')
                else: 
                    overskrivStedfesting = tmp_overskriv                
                   
        else: 
            datadir = sys.argv[1]
            duallog.duallogSetup( logdir=logdir, logname=logname) 
            logging.info( versjonsinfo ) 

            
        if not datadir: 
            logging.error( 'Påkrevd parameter "datadir" ikke angitt, du må fortelle meg hvor vegbildene ligger') 
        else: 

            logging.info( 'Konfigurasjon: overskrivStedfesting=' + str( overskrivStedfesting ) ) 
            if oppsett: 
                logging.info( 'Henter oppsett fra fil' + sys.argv[1] ) 
                
            if proxies: 
                logging.info( 'Bruker proxy for http-kall: ' + str( proxies )  ) 
            else: 
                logging.info( 'Bruker IKKE proxy for http kall' )  
                
            if not isinstance( datadir, list): 
                datadir = [ datadir ] 
                
            for idx, enmappe in enumerate( datadir ): 

                logging.info( ' '.join( [ "Prosesserer mappe", str(idx+1), 'av', str(len(datadir)), enmappe ] ) ) 
                sorter_mappe_per_meter( enmappe ) 
                stedfest_jsonfiler( enmappe, overskrivStedfesting=overskrivStedfesting, proxies=proxies )  
  
            logging.info( "FERDIG " + versjonsinfo ) 

