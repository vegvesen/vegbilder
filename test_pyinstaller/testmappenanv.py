# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""

import os
import locale
import sys
import duallog
import logging
import pdb

def hoved( inngangsdata='inngangsdata', out1 ='resultat_utenkonvertering', out2='resultat_medkonvertering'  ): 
    
    
    tegnsett = locale.getpreferredencoding() 
    filsystemtegnsett = sys.getfilesystemencoding()
    logging.info( 'Tegnsett = ' + tegnsett) 
    logging.info( 'Filsystem tegnsett = ' + filsystemtegnsett) 
    
    logging.info( 'Lager filnavn uten encoding-decoding seremoni' ) 
    filer = os.listdir( inngangsdata) 
    
    for fil in filer: 
        
        fname = os.path.join( 'resultat_utenkonvertering', fil) 
        logging.info( fname ) 
        
        with open( fname, 'w') as f: 
            f.write( 'ASdf' ) 
        
        
        
    
    filer = os.listdir( inngangsdata.encode() ) 
    
    for fil in filer: 
        
        # pdb.set_trace()
        fname = os.path.join( 'resultat_medkonvertering', fil.decode( filsystemtegnsett ) )
        logging.info( fname) 
        
        with open( fname, 'w') as f: 
            f.write( 'Hahahaha' ) 
        
    

        

    
    
if __name__ == "__main__":

    
    versjonsinfo = "Test tegnsett mappenavn versjon 1.0, 19.06.2019"
    logdir = 'loggfiler_testmappenavn' 
    logname='testmappenavn_'
    duallog.duallogSetup( logdir=logdir, logname=logname) 
    
    logging.info( versjonsinfo ) 
    hoved( ) 
 
    logging.info( versjonsinfo ) 
