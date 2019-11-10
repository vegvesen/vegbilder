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
from copy import deepcopy


import requests
# import xmltodict # Må installeres, rett fram 
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
                filnavn.append( re.sub( '\\\\', '/', os.path.join( root, name) ) )
    
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


def fiksutf8( meta): 

    kortalfabet = 'abcdefghijklmnopqrstuvwxyz'
    alfabet = kortalfabet + 'æøå'
    tegn  = '0123456789.,:;-_ *+/++<>\\' 
    godkjent = tegn + alfabet + alfabet.upper()
    raretegn = False

    tulletegn = set( ) 
    # Prøver å fikse tegnsett 
    if meta and isinstance( meta, dict): 
        old = deepcopy( meta) 
        for key, value in old.items():
            if isinstance( value, str): 
                nystr = ''
                rart = False 
                for bokstav in value: 
                    if bokstav in godkjent: 
                        nystr += bokstav
                    else:
                       tulletegn.add( bokstav)  
                       rart = True 
                       
                if rart: 
                    nystr = nystr.replace( 'Æ', '_')
                    nystr = nystr.replace( 'Å', '_') 
                    
                    nystr = re.sub('_{2,}', '_', nystr )
                    
                    raretegn = True 
                meta[key] = nystr

    return meta, raretegn


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

def opensqlite( sqlitefile, opprettfil=False ): 
    """'
    Åpner sqlite-fil med metadata
    
    Arguments
        sqlitefile: file name.sqlite/table_name of file to open 
        
    keywords
        opprettfil: Will make an sqlite-fil and/or table if none exists. 
    
    Returns 
        CURSOR object for the relevant table, or None if not successful  
    """
    
    return None 


def sjekkgammeldatabase( gammeldatabase, metadata, tilfoygammel=False): 
    """
    Sjekker om metadataelement finnes fra før, og føyer det evt til om det mangler
    
    Arguments
        gammeldatabase: None eller Kobling til sqlite-tabell med 
                        allerede indekserte metadata-element
        metadata: Metadata-element lest fra json-fil
        
    Keywords
        tilfoygammel: false (default) | true 
    """
    if not gammeldatabase: 
        return False 

    finnes = False 
    return finnes

def skrivmetadataSqlite( sqlitecurs, metadata, filnavn): 
    """
    Skriver metadata til angitt tabell 
    
    Arguments: 
        sqlitecurs: Cursor for sqlite-tabell

        metadata: Metadataelement som skal skrives
        
        filnavn: Filnavn for json-fil / bildefil 
        
    
    Returns: True (successful) or False (fail) 
    """ 
    
    print( filnavn) 
    
    return True 

def indekser_jsonfiler( mappe, database, gammel_database=None ):
    t0 = datetime.now()
    jsonfiler = recursive_findfiles( 'fy*hp*m*.json', where=mappe) 
    count = 0
    count_suksess = 0 
    count_fatalt = 0 
    
    # gmlsqlite = opensqlite( gammel_database, opprettfil=False)
    # nysqlite = opensqlite( database, opprettfil=True) 
 
    for (nummer, filnavn) in enumerate(jsonfiler): 
        count += 1 
        meta = lesjsonfil( filnavn) 

        if meta: 
            # print( meta) 
            (meta, raretegn) = fiksutf8( meta) 
            print( json.dumps( meta, indent=4)) 
            
            return 

            # if not sjekkgammeldatabase( gmlsqlite, meta, tilfoygammel=True):  
                # suksess = skrivmetadataSqlite( nysqlite, meta, filnavn)
                # if suksess:
                    # count_suksess += 1

    # dt = datetime.now() - t0
    # logging.info( ' '.join( [ 'Indekserte', str( count_suksess ) , 'av', 
                                # str( len(jsonfiler)), 'vegbilder på', 
                                # str( dt.total_seconds()), 'sekunder' ] ) ) 
                                
    # diff = len(jsonfiler) - count_suksess
    # if diff > 0: 
        # logging.info( 'Hoppet over ' + str( diff) + ' av ' + str( len( jsonfiler) ) + ' vegbilder' ) 

    # diff = count - count_suksess
    # if diff > 0: 
        # logging.warning( 'Indeksering FEILET for ' + str( diff) + ' av ' + str( len( jsonfiler) ) + ' vegbilder' ) 
        
    # if count_fatalt > 0: 
        # logging.error( 'Stedfesting FEILET med ukjent feilsituasjon for ' + str( count_fatalt) + ' vegbilder' ) 

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
    
    versjonsinfo = "Indekser vegbilder Versjon 0.1 den 20. okt 2019"
    print( versjonsinfo ) 
    if len( sys.argv) < 2: 

        print( "BRUK:\n")
        print( 'indekservegbilder.exe oppsettfil_indekserbilder.json') 
        time.sleep( 1.5) 
    
    else: 
        
        if '.json' in sys.argv[1][-5:].lower(): 
            print( 'Leser oppsettfil fra', sys.argv[1] ) 
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
            
            if 'gammel_database' in oppsett.keys(): 
                gammel_database = oppsett['gammel_database']
                if gammel_database: 
                    logging.info( 'Sammenligner med eksisterende metadata: ' + gammel_database  ) 
                                   
        else: 
            datadir = sys.argv[1]
            duallog.duallogSetup( logdir=logdir, logname=logname) 
            logging.info( versjonsinfo ) 

            
        if not datadir: 
            logging.error( 'Påkrevd parameter "datadir" ikke angitt, du må fortelle meg hvor vegbildene ligger') 
        else: 
                
            if not isinstance( datadir, list): 
                datadir = [ datadir ] 
                
            for idx, enmappe in enumerate( datadir ): 

                logging.info( ' '.join( [ "Prosesserer mappe", str(idx+1), 'av', str(len(datadir)), enmappe ] ) ) 
                
                indekser_jsonfiler( enmappe, database, gammel_database=gammel_database )  
  
            logging.info( "FERDIG " + versjonsinfo ) 

