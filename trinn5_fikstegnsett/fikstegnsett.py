import re
import os
from copy import deepcopy
from datetime import datetime
import logging
import sys
import json
import duallog
import fnmatch
import glob


def fiksutf8( meta): 

    kortalfabet = 'abcdefghijklmnopqrstuvwxyz'
    alfabet = kortalfabet + 'æøå'
    tegn  = '0123456789.,:;-_ *+/++<>\\()#?=' 
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

    # if len(tulletegn) > 0: 
        # print( "Tulletegn: ", tulletegn) 
        
    return meta, raretegn
    
def fikslinje( eilinje): 
    kortalfabet = 'abcdefghijklmnopqrstuvwxyz'
    alfabet = kortalfabet + 'æøå'
    tegn  = '"0123456789.,:;-_ *+/++<>\\()#?={}' 
    godkjent = tegn + alfabet + alfabet.upper()

    svar = ''
    rart = False
    count = 0
    lengde = len( eilinje )
    for bokstav in eilinje: 
        if bokstav in godkjent: 
            svar += bokstav 
        elif bokstav == '\n': 
            pass 
        else: 
            rart = True
            
        count += 1
        if count > 0 and count % 1e7 == 0:
            print( 'Bokstav ' + str( count) + ' av ' + str(  lengde )  + ' ' + str( round( 100* count / lengde, 2) ) + '%'  )
    
    return (svar, rart)    
    
    
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

def fikstegnsett_fil( filnavn): 
    
    rentekst = ''
    
    raretegn = set() 
    
    with open( filnavn, encoding='utf-8',  errors='ignore') as f: 
        for line in f: 
            lengde = len( line) 
            if lengde  > 1e4: 
                print( 'Lang linje ' + str( lengde)  + ' tegn i fil ' + filnavn ) 
            (nylinje, rart) = fikslinje( line) 
            raretegn.add(rart) 
            rentekst += nylinje + '\n' 
            
    if True in raretegn: 
        logging.info ('Rare tegn funnet i ' + filnavn ) 
    
        with open( filnavn, 'w', encoding='utf-8') as f2:
            f2.write( rentekst ) 

def fiksfiler( datadir): 
    
    jsonfiler = recursive_findfiles( 'fy*hp*m*.json', where=datadir) 
    antfiler = len( jsonfiler) 
    logging.info( 'Fant ' + str( antfiler) + ' json-filer i ' + datadir ) 
    
    for eifil in jsonfiler: 
        fikstegnsett_fil( eifil ) 
    

def finnundermapper( enmappe, huggMappeTre=None, **kwargs):

    if huggMappeTre: 
    
        logging.info( "finner undermapper til: " +  enmappe ) 
        huggMappeTre = huggMappeTre - 1
        
        folders = [f for f in glob.glob(enmappe + "/*/")]
        for undermappe in folders: 
            logging.info( "fant undermappe: " + undermappe) 
            finnundermapper( undermappe, **kwargs )

    else: 
        print( "Starter proseessering av undermappe: " + enmappe) 
    
        fiksfiler( enmappe, **kwargs)

     
if __name__ == '__main__': 

    datadir = None
    logdir = 'log' 
    logname='fikstegnsett_' 
    huggMappeTre = False

    t0 = datetime.now()
    versjonsinfo = "Fikstegnsett JSON Versjon 1.0 den 3. des 2019"
    print( versjonsinfo ) 
    if len( sys.argv) < 2: 

        print( "BRUK:\n")
        print( 'fikstegnsett.exe oppsettfil_fikstegnsett.json') 
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
                
            if 'huggMappeTre' in oppsett.keys():
                huggMappeTre = oppsett['huggMappeTre'] 

            duallog.duallogSetup( logdir=logdir, logname=logname) 
            logging.info( versjonsinfo ) 
            
                                   
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
                
                if huggMappeTre:
                    if huggMappeTre == 1: 
                        logging.info( 'huggMappeTre: Vil ta hver undermappe i katalogen(e) "datadir" for seg' )
                    else:
                        logging.info( 'huggMappeTre: Vil ta under-underkataloger for ' + str( huggMappeTre) + 
                                        ' nivåer nedover relativt til "datadir"-katalogen(e) for seg' ) 
                else: 
                    logging.info( "Ingen huggMappeTre - parameter") 

                finnundermapper( enmappe, huggMappeTre=huggMappeTre )           
  
        dt = datetime.now() - t0
        logging.info( " ".join( [ "Tidsforbruk TOTALT: ", str( dt.total_seconds()), 'sekunder' ])) 
        logging.info( "FERDIG" + versjonsinfo ) 
