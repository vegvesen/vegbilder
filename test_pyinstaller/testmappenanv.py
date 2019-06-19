# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""

import os
import locale
import sys
from pathlib import Path
import logging
import pdb
import json

import duallog

def mypathsplit( filnavn, antallbiter): 
    """
    Deler opp et filnavn (mappenavn) i antallbiter komponenter, regnet bakfra, pluss rot-komponent

    returnerer liste med [rot, tredjbakerst, nestbakerst, bakerst] for antallbiter=3
    
    Hvis antallbiter > antall komponenter reduserers så mange elementer som fil/mappenavnet kan deles opp i 
    """
  
    biter = []
    for i in range(antallbiter) : 
        (rot, hale) = os.path.split( filnavn ) 
        if hale: 
            biter.append( hale) 
        filnavn = rot
    
    if rot: 
        biter.append( rot) 
        
    return list( reversed( biter) ) 

def hoved( inngangsdata='inngangsdata', out1 ='resultat_utenkonvertering', out2='resultat_medkonvertering'  ): 
    
    
    datadir = inngangsdata
    
    tegnsett = locale.getpreferredencoding() 
    filsystemtegnsett = sys.getfilesystemencoding()
    logging.info( 'Tegnsett = ' + tegnsett) 
    logging.info( 'Filsystem tegnsett = ' + filsystemtegnsett) 
    
    logging.info( 'Lager filnavn uten encoding-decoding seremoni\n' ) 
    # filer = os.listdir( inngangsdata) 
    
    folders = set(folder for folder, subfolders, files in os.walk(datadir) for file_ in files if os.path.splitext(file_)[1].lower() == '.jpg')
    
    for mappe in folders: 
        mylist = mypathsplit( mappe, 5) 
        # pdb.set_trace()
        
        mappenavn = os.path.join( 'resultat_utenkonvertering', mylist[1], mylist[2], mylist[3], mylist[4], mylist[5] ) 
        nymappe = Path( mappenavn ) 
        nymappe.mkdir( parents=True, exist_ok=True)
    
        fname = os.path.join( mappenavn, 'dummy.txt' ) 
    
        logging.info( fname ) 
        
        with open( fname, 'w') as f: 
            f.write( 'ASdf' ) 
        
    
    filer = os.listdir( inngangsdata.encode() ) 

    folders = set(folder for folder, subfolders, files in os.walk(datadir ) for file_ in files if os.path.splitext(file_)[1].lower() == '.jpg')


    logging.info( '\nLager filnavn der vi prøver på byte-encoding og dekoding fra filsystem-tegnsett => utf-8\n' ) 
    for mappe in folders: 
 
        mylist = mypathsplit( mappe, 5) 
  
        # pdb.set_trace()
        mappenavn = os.path.join( 'resultat_medkonvertering', 
                                    bytes( mylist[1], filsystemtegnsett).decode( 'utf-8'), 
                                    bytes( mylist[2], filsystemtegnsett).decode( 'utf-8'), 
                                    bytes( mylist[3], filsystemtegnsett).decode( 'utf-8'), 
                                    bytes( mylist[4], filsystemtegnsett).decode( 'utf-8'), 
                                    bytes( mylist[5], filsystemtegnsett).decode( 'utf-8') ) 

        fname = os.path.join( mappenavn, 'dummy.txt' ) 
        nymappe = Path( mappenavn ) 
        nymappe.mkdir( parents=True, exist_ok=True)
        logging.info( fname ) 
       
        with open( fname, 'w') as f: 
            f.write( 'Hahahaha' ) 
        
    

        

    
    
if __name__ == "__main__":

    
    versjonsinfo = "Test tegnsett mappenavn versjon 1.2, 19.06.2019 kl 14:49"
    logdir = 'loggfiler_testmappenavn' 
    logname='testmappenavn_'
    duallog.duallogSetup( logdir=logdir, logname=logname) 
    
    logging.info( versjonsinfo ) 

    if len( sys.argv) < 2: 
        print( "BRUK:\n")
        print( 'testmappenavn.exe oppsettfil_flyttvegbilder.json\n') 
        time.sleep( 1.5) 
        
    else: 

        if '.json' in sys.argv[1][-5:].lower(): 
            print( 'flyttvegbilder.exe: Leser oppsettfil fra', sys.argv[1] ) 
            with open( sys.argv[1]) as f: 
                oppsett = json.load( f) 
        
            if 'orginalmappe' in oppsett.keys():
                gammeltdir = oppsett['orginalmappe']

        else: 
            gammeltdir = sys.argv[1]

    if not gammeltdir: 
        print( "STOPP - kan ikke prosessere uten at du angir mappenavn") 
    else:     
    
        if not isinstance( gammeltdir, list): 
            gammeltdir = [ gammeltdir ] 
        
        for idx, enmappe in enumerate( gammeltdir): 
            logging.info( ' '.join( [ "Prosesserer mappe", str(idx+1), 'av', str(len(gammeltdir)) ] ) ) 
            hoved( inngangsdata=enmappe ) 
    
    logging.info( versjonsinfo ) 


