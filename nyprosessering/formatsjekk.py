# Standard library 
import json
import logging
import os 
from pathlib import Path

import pdb

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
    

    # Sjekker at alle påkrevde tagger finnes, evt duplikater
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

def kvalitetskontroll( jsonmal, jsondata, filnavn): 
    """
    Kvalitetskontroll av ferdige prosesserte data 

    ARGUMENTS
        jsonmal - dictionary som vi sammenligner med
        
        jsondata - dictionary som skal kvalitetssjekkes
        
        filnavn - Filnavn til jsondata. Brukes til logging
    """
    sjekktagger( jsonmal, jsondata, filnavn)
                            
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
    jsonmal = lesjsonfil( 'vegbildejson_mal.json', ventetid=15) 

    for filnavn in kopiertefiler: 
        jsondata = lesjsonfil( filnavn, ventetid=15) 

        try: 
            kvalitetskontroll( jsonmal, jsondata, filnavn) 
        except AssertionError as myErr: 
            logging.error( str( myErr) ) 

                            
if __name__ == '__main__': 

    logdir  = 'test_loggdir'
    logname = 'test_loggnavn'
    duallog.duallogSetup( logdir=logdir, logname=logname) 

    jsonmal = lesjsonfil( 'vegbildejson_mal.json' )

    mappenavn = 'testdata/'
    jsonfiler = findfiles( '*.json', mappenavn) 
    for filnavn in jsonfiler: 
        jsondata = lesjsonfil( filnavn, ventetid=15) 
    
        try: 
            kvalitetskontroll( jsonmal, jsondata, filnavn) 
        except AssertionError as myErr: 
            logging.error( str( myErr) ) 
