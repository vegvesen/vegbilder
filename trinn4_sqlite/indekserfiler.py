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
# from xml.parsers.expat import ExpatError
from copy import deepcopy


import requests
# import xmltodict # Må installeres, rett fram 
import duallog 
import sqlite3
import pdb


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
    tegn  = '0123456789.,:;-_ *+/++<>\\()' 
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

def opensqlite( sqlitefile  ): 
    """'
    Åpner sqlite-fil/tabell med metadata. Vil opprette ny dersom angitt fil ikke finnes
    
    Arguments
        sqlitefile: file name.sqlite/table_name of file to open 
            
    Returns 
        (CONNECTION, CURSOR) objects for the relevant db and table, or None if not successful  
    """
    
    tmp = sqlitefile.split( '/')
    if len( tmp) < 2: 
        logging.error( "Ugyldig navn på SQLITE database, skal ha formen filnavn.sqlite/tabellnavn") 
        return None, None
        
    tabellnavn = tmp[-1]
    filnavn = ( '/').join( tmp[:-1] ) 

    if not os.path.isfile( filnavn ): 
        logging.info( "Sqlite db finnes ikke, vil opprette: " + filnavn)
        
    
    con = sqlite3.connect( filnavn )
    cur = con.cursor()
    
    # Leser tabellnavn
    r = cur.execute( "SELECT NAME from sqlite_master WHERE type='table';")
    tnavn = r.fetchall()
    alletabeller = [ t[0] for t in tnavn]
    nytabell = False
    if tabellnavn not in alletabeller: 
        logging.info( 'Oppretter tabell ' + tabellnavn + ' i db ' + filnavn) 
        nytabell = True 
    
    skjema = skjemadefinisjon()
    kolonner = ' , '.join(x + ' ' + y for x, y in skjema.items())
    createtbl = 'CREATE TABLE IF NOT EXISTS ' + tabellnavn + ' ( pkid INTEGER PRIMARY KEY, ' + kolonner + ' )' 
    cur.execute( createtbl) 
    
    if nytabell: 
        cur.execute( 'CREATE UNIQUE INDEX uuid_idx ON ' + tabellnavn + '(bildeuiid)' )
    
    con.commit()
    
    return con, cur, tabellnavn
     

def skjemadefinisjon(): 

    skjema = { "exif_tid": "TEXT",
                "exif_dato": "TEXT",
                "exif_numeriskdato" : "INTEGER", 
                "exif_speed": "REAL",
                "exif_heading": "REAL",
                "exif_gpsposisjon": "TEXT",
                "exif_strekningsnavn": "TEXT",
                "exif_fylke": "INTEGER",
                "exif_vegkat": "TEXT",
                "exif_vegstat": "TEXT",
                "exif_vegnr": "INTEGER",
                "exif_hp": "INTEGER",
                "exif_meter": "REAL",
                "exif_feltkode": "TEXT",
                "exif_mappenavn": "TEXT",
                "exif_filnavn": "TEXT",
                "exif_strekningreferanse": "TEXT",
                "exif_xptitle": "TEXT",
                "retning": "TEXT",
                "filnavn_feltkode": "TEXT",
                "mappenavn": "TEXT",
                "datafangstuuid": "TEXT",
                "bildeuiid": "TEXT",
                "forrige_uuid": "TEXT",
                "neste_uuid": "TEXT",
                "stedfestet": "TEXT",
                "indeksert_i_db": "TEXT",
                "senterlinjeposisjon": "TEXT",
                "veglenkeid": "INTEGER",
                "veglenkepos": "REAL",
                "feltoversikt": "TEXT",
                "feltoversikt_perbildedato": "TEXT",
                "lenkeretning": "REAL",
                "lenkeretning_perbildedato": "REAL",
                "fylke": "INTEGER",
                "kommune": "INTEGER",
                "vegkat": "TEXT",
                "vegstat": "TEXT",
                "vegnr": "INTEGER",
                "hp": "INTEGER",
                "meter": "INTEGER",
                "fase" : "TEXT", 
                "trafikantgruppe": "TEXT",
                "strekning": "INTEGER",
                "delstrekning" : "INTEGER",
                "arm" : "TEXT",
                "adskilte løp": "TEXT", 
                "meterverdi": "INTEGER",
                "kryssystem": "INTEGER",
                "kryssdel": "INTEGER",
                "kryssdelmeter": "INTEGER",
                "sideanlegg": "INTEGER",
                "sideanleggsdel": "INTEGER",
                "sideanleggmeter": "INTEGER",
                "vegsystemreferanse": "TEXT",
                "vegreferansedato": "TEXT",
                "vegreferansedato_numerisk" : "INTEGER", 
                "vegsystemreferansedato" : "TEXT",
                "vegsystemreferansedato_numerisk": "INTEGER",
                "feltkode": "TEXT",
                "filnavn": "TEXT",
                "retningsnudd": "TEXT",
                "strekningsreferanse": "TEXT",
                "stedfestingdato": "TEXT",
                "stedfestingdato_numerisk": "INTEGER",
                "exif_imageproperties": "TEXT", 
                "filplassering": "TEXT"  
                }


    return skjema



def skrivmetadataSqlite( sqlitecurs, metadata, tabellnavn, filnavn): 
    """
    Skriver metadata til angitt tabell 
    
    Arguments: 
        sqlitecurs: Cursor for sqlite-tabell

        metadata: Metadataelement som skal skrives
        
        filnavn: Filnavn for json-fil / bildefil 
        
    
    Returns: True (successful) or False (fail) 
    """ 
    
    skjema = skjemadefinisjon()
    
    # Ny metadata-oppføring, eller sjekk av gammel? 
    r = sqlitecurs.execute( "SELECT * from " + tabellnavn + " WHERE bildeuiid = '" + metadata['bildeuiid'] + "' ;" ) 
    f = r.fetchall()
    
    if len( f ) > 0: 
        for key in skjema.keys(): 
            if key in metadata.keys() and metadata[key]: 
                if skjema[key] == 'TEXT': 
                    sqlitecurs.execute("UPDATE " + tabellnavn + " SET " + key + " = '" + str( metadata[key] ) + "' WHERE bildeuiid = '" + 
                                        str( metadata['bildeuiid'] ) + "';" ) 
                else: 
                    sqlitecurs.execute("UPDATE " + tabellnavn + " SET " + key + " = " + str(metadata[key]) + " WHERE bildeuiid = '" + 
                                        metadata['bildeuiid'] + "';" ) 
        print( "Oppdaterer eksisterende metadata-element i tabell") 
    else: 
        insertsql = "INSERT INTO " + tabellnavn + "( " 
        values = "VALUES ( "
        for key in skjema.keys(): 
            if key in metadata.keys() and metadata[key]:
                insertsql += key + ", " 
                if skjema[key] == "TEXT": 
                    values += "'" + str( metadata[key] ) + "', "
                else: 
                    values += str( metadata[key] ) + ", "

        # Fjerner siste komma 
        insertsql = insertsql[:-2] 
        values = values[:-2] 
        insertsql += ") " + values + ") ;"  
        sqlitecurs.execute( insertsql) 
        
    metadata['indeksert_i_db'] = True
    # skrivjsonfil( filnavn, metadata) 
       
    return True 

def alleredeindeksert( sqlitecurs, tabellnavn, bildeuiid): 
    """
    Sjekker om bildeuuid finnes fra før i databasen over hva som er indeksert fra tidligere
    """
    
    finnes = False
    
    if sqlitecurs: 
        sqlitecurs.execute( "SELECT bildeuiid FROM " + tabellnavn + " WHERE bildeuiid = '" + bildeuiid + "' ;" )  
        f = r.fetchall()
        if len( f ) > 0:
            finnes = True
        
    return finnes
    
def berikdata( meta ): 
    """
    Beriker med en del metadata-elementer vi savner
    """      
    
    if not 'vegsystemreferanse' in meta.keys(): 
        
        url = 'https://www.vegvesen.no/nvdb/api/v3/veg.json'
        params = { 'veglenkesekvens' : str( meta['veglenkepos'] ) + '@' + str( meta['veglenkeid'] ) }
        r = requests.get( url,  params = params) 
            
        if r.ok: 
            resultat = r.json()
            vegsys = resultat['vegsystemreferanse']['vegsystem'] 
            
            meta["vegsystemreferanse"] = resultat['vegsystemreferanse']['kortform'] 
            meta['vegkat'] = vegsys['vegkategori'] 
            meta['fase'] = vegsys['fase'] 
            meta['nummer'] = vegsys['nummer'] 

            strek = resultat['vegsystemreferanse']['strekning'] 
            meta['strekning'] = strek['strekning'] 
            meta["delstrekning"] = strek["delstrekning"]
            meta['arm'] = strek['arm']
            meta['adskilte_lop'] = strek["adskilte_løp"]
            meta["trafikantgruppe"] = strek["trafikantgruppe"]
            meta['meterverdi'] = round( strek["meter"] )
            
            if 'kryssystem' in resultat['vegsystemreferanse']: 
                kryss = resultat['vegsystemreferanse']['kryssystem']
                meta["kryssystem"] = kryss["kryssystem"] 
                meta["kryssdel"] = kryss["kryssdel"]
                meta["kryssdelmeter"] = kryss["meter"]  
                meta["trafikantgruppe"] = kryss[ "trafikantgruppe" ]
 
            if 'sideanlegg' in resultat['vegsystemreferanse']: 
                side = resultat['vegsystemreferanse']['sideanlegg']
                meta["sideanlegg"] = side["sideanlegg"]
                meta["sideanleggsdel"] = side["sideanleggsdel"]
                meta["sideanleggmeter"] = side["meter"]
                meta["trafikantgruppe"] = side["trafikantgruppe"]

                meta["vegsystemreferansedato"]  = str( datetime.datetime.now())[0:10] 
                meta["vegsystemreferansedato_numerisk"] = int( re.sub( '-', '', meta["vegsystemreferansedato"] ) )

    meta["vegreferansedato_numerisk"] = int( re.sub( '-', '', meta["vegreferansedato"] ) )
    return meta

def lagfilplassering( meta, filnavn):
    """
    Konstruerer stien til bildefila, oppover relativt fra /vegbilder/ - elementet
    """

    mapper = splitpath(filnavn)
    filplassering = '/'.join( mapper[-6:])
    meta['filplassering'] = filplassering

    return meta

def splitpath( filnavn ):
    """
    Deler filnavn opp i liste med undermapper + filnavn (siste element i listen)
    """
    deling1 = os.path.split( filnavn )

    if deling1[0] == '/' or deling1[0] == '' or deling1[1] == '': 
        mapper = [ filnavn ]
    else: 
        mapper = splitpath( deling1[0] )
        mapper.append( deling1[1])

    return mapper 
    
def indekser_jsonfiler( mappe, database, gammel_database=None ):
    t0 = datetime.now()
    jsonfiler = recursive_findfiles( 'fy*hp*m*.json', where=mappe) 
    count = 0
    count_suksess = 0 
    count_fatalt = 0 
    count_raretegn = 0 
    indeksert_tidligere = 0
    gmlsqlite_conn = False
    gmlsqlite_cur = False
    gammeltabell = 'junk'
    
    if gammel_database: 
        pass
        # (gmlsqlite_conn, gmsqlite_cur, gammeltabell) = opensqlite( gammel_database, opprettfil=False)
        
    (nysqlite_conn, nysqlite_cur, nytabell) = opensqlite( database ) 
 
    for (nummer, filnavn) in enumerate(jsonfiler): 
        count += 1 
        meta = lesjsonfil( filnavn) 

        if count == 10 or count == 50 or count % 250 == 0: 
            logging.info( 'Indekserer bilde ' + str( count ) + ' av ' + str( len( jsonfiler)) )

        if meta: 
            meta = lagfilplassering(meta, filnavn)
            (meta, raretegn) = fiksutf8( meta) 
            if raretegn and count_raretegn < 2: 
                logging.info( 'Rare tegn funnet i fil' + filnavn) 
                count_raretegn += 1 
            
            # Sjekker den gamle, 
            if not alleredeindeksert( gmlsqlite_cur, gammeltabell, meta['bildeuiid'] ):

                meta = berikdata( meta ) 
                suksess = skrivmetadataSqlite(nysqlite_cur, meta, nytabell, filnavn)
                if suksess: 
                    count_suksess += 1
                else:
                    count_fatalt += 1
                
                if gmlsqlite_cur: 
                    junk = skrivmetadataSqlite(gmlsqlite_cur, meta, gammeltabell, filnavn)
            
            else: 
                indeksert_tidligere += 1 
                print( 'Bilde indeksert fra tidligere') 
            
            
    if nysqlite_conn: 
        nysqlite_conn.commit()
        nysqlite_conn.close()
    
    if gmlsqlite_conn: 
        gmlsqlite_conn.commit()
        gmlsqlite_conn.close()
    
    dt = datetime.now() - t0
    logging.info( ' '.join( [ 'Indekserte', str( count_suksess ) , 'av', 
                                str( len(jsonfiler)), 'vegbilder på', 
                                str( dt.total_seconds()), 'sekunder' ] ) ) 
                                
    diff = count - count_suksess
    if diff > 0: 
        logging.warning( 'Indeksering FEILET for ' + str( diff) + ' av ' + str( len( jsonfiler) ) + ' vegbilder' ) 
        
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
    gammel_database = None
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
                
            if 'logdir' in oppsett.keys():
                logdir = oppsett['logdir']

            if 'logname' in oppsett.keys():
                logname = oppsett['logname']

            duallog.duallogSetup( logdir=logdir, logname=logname) 
            logging.info( versjonsinfo ) 
            
            if 'database' in oppsett.keys(): 
                database = oppsett['database']
                logging.info( 'Lagrer resultater i SQLITE database ' + database )
            
            if 'gammel_database' in oppsett.keys(): 
                gammel_database = oppsett['gammel_database']
                if gammel_database: 
                    logging.info( 'Sammenligner med eksisterende database: ' + gammel_database  )
                    logging.info( ' => Kun data IKKE funnet i eksisterende database blir skrevet til ' + database ) 
                                   
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

