# Standard library 
import json
import logging
import os 
from pathlib import Path

# Well known 3rd party libraries

# Custom libraries
import duallog
from flyttvegbilder_v54 import lesjsonfil
from flyttvegbilder_v54 import findfiles, kopierfil

def sjekktagger( jsonmal, jsondata, filnavn ):
    """
    Sjekker om dictionary har alle påkrevde tagger 
    
    ARGUMENTS
        jsonmal - dictionary som vi sammenligner med
        
        jsondata - dictionary som skal kvalitetssjekkes
        
        filnavn - Filnavn til jsondata. Brukes til logging
    """
    
    # Sjekker at alle påkrevde tagger finnes
    for akey in jsonmal.keys(): 
    
        assert akey in jsondata.keys(), ' '.join( [  
                'SKJEMAFEIL Mangler', akey, 'elementet i', filnavn ] ) 
    
    # Sjekker om det finnes overflødige tagger
    for akey in jsondata.keys(): 
    
        assert akey in jsonmal.keys(), ' '.join( [ 'SKJEMAFEIL Ekstra element', 
                            akey, 'i jsonfil', filnavn ] ) 
                            
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


                            
if __name__ == '__main__': 

    logdir  = 'test_loggdir'
    logname = 'test_loggnavn'
    duallog.duallogSetup( logdir=logdir, logname=logname) 

    with open( 'vegbildejson_mal.json', encoding='utf-8') as f: 
        jsonmal = json.load( f) 

    mappenavn = 'testdata/'
    jsonfiler = findfiles( '*.json', mappenavn) 
    for filnavn in jsonfiler: 
        jsondata = lesjsonfil( filnavn, ventetid=15) 
    
        try: 
            sjekktagger( jsonmal, jsondata, filnavn) 
        except AssertionError as myErr: 
            logging.error( str( myErr) ) 
