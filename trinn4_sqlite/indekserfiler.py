"""
Indekserer metadata for vegbilder og (mellom)lagrer data til sqlite-database. 

Parametre (angitt i json-oppsettfil eller funksjonskall) 
    datadir:  Mappen, eller en liste med mapper som skal indekseres
    
    rotURL: Statisk URL til webserver der bildene ligger. Denne         
            webserveren serverer ut mappetreet direkte, slik at det 
            er 1:1 forhold mellom mappetre på webserver og filserver. 
            URL - mappestrukturen er slik: Statisk del + vegbildehierarki  
                Statisk del https://[utv|test|www].vegvesen.no / kart / vegbilder / 
                Vegbildehierarki: fylke / år / vegnr / hp / felt / bildefil.jpg 
            rotURL er den statiske delen av adressen. 
    
    database: Filnavn og tabellnavn på sqlite-filen der metadata (mellom)lagres
                Merk syntaks "../sti/til/filnavn.sqlite/tabellnavn" 
    
    gammel_database: Filnavn og tabellnavn for sqlite med bilder som er blitt 
            indeksert tidligere . Merk syntaks         
                            "../sti/til/filnavn.sqlite/tabellnavn"     
            I så fall blir kun nye eller endrede 
            metadata-objekter skrevet til den nye databasen. 
    
    logname: Filnavn for logging 
    
    logdir: Mappe der loggfilene havner 
    
    proxies: Adresse til eventuelle proxies på nettverket (hvis nødvendig) 
    
    
    NB! IKKE IMPLEMENTERT, kun overordnet funksjonsbeskrivelse 
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


def indekser_jsonfiler( mappe=, database, gammel_database=None, proxies=None ):
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
                    # meta = visveginfo_vegreferanseoppslag( meta, proxies=proxies, filnavn=filnavn) 
                    pass 
                except Exception:
                    count_fatalt += 1
                    logging.error( "Fatal feil i visveginfo_referanseoppslag for fil: " + filnavn )
                    logging.exception("Stack trace for fatal feil:")
                else: 
                
                    if meta['stedfestet'] == 'JA' : 
                        count_suksess += 1
                    
                    # skrivjsonfil( filnavn, meta) 
                    
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
    


    
if __name__ == '__main__': 

    datadir = None
    gammel_database = ''
    logdir = 'log' 
    logname='indekservegbilder_' 
    proxies = { 'http' : 'proxy.vegvesen.no:8080', 'https' : 'proxy.vegvesen.no:8080'  }

    
    versjonsinfo = "Indekser vegbilder Versjon 0.1 den 20. okt 2019"
    print( versjonsinfo ) 
    if len( sys.argv) < 2: 

        print( "BRUK:\n")
        print( 'indekservegbilder.exe oppsettfil_indekserbilder.json') 
        time.sleep( 1.5) 
    
    else: 
        
        if '.json' in sys.argv[1][-5:].lower(): 
            print( 'vegbilder_lesexif: Leser oppsettfil fra', sys.argv[1] ) 
            with open( sys.argv[1]) as f: 
                oppsett = json.load( f) 

            if 'datadir' in oppsett.keys(): 
                datadir = oppsett['datadir']

            if 'database' in oppsett.keys(): 
                database = oppsett['database']

            if 'gammel_database' in oppsett.keys(): 
                gammel_database = oppsett['gammel_database']
                
            if 'logdir' in oppsett.keys():
                logdir = oppsett['logdir']

            if 'logname' in oppsett.keys():
                logname = oppsett['logname']

            duallog.duallogSetup( logdir=logdir, logname=logname) 
            logging.info( versjonsinfo ) 
            
            if 'proxies' in oppsett.keys():
                proxies = oppsett['proxies']
            
            if 'gammel_database' in oppsett.keys(): 
                gammel_database = oppsett['gammel_database']
                if gammel_database: 
                    logging.info( 'Sammenligner med eksisterende metadata: ' + sys.gammel_database  ) 
                                   
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
                
                indekser_jsonfiler( enmappe, database, gammel_database=gammel_database, proxies=proxies )  
  
            logging.info( "FERDIG " + versjonsinfo ) 

