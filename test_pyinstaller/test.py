# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""

import time
import json
import sys

def hoved( arg1='dummy'): 
    print( "Hovedrutine, her er mine argumenter:")
    print( 'Argument 1:', arg1) 
    time.sleep( 1)
    
    
if __name__ == "__main__":
    if len( sys.argv) > 1: 
        inputarg = sys.argv[1]
    

        # Leser oppsett fra *.json-fil    
        if '.json' in inputarg[-5:].lower():
            with open( inputarg) as f: 
                myinput = json.load( f) 
               
            if 'arg1' in myinput.keys(): 
                print( "Henter argumenter fra angitt .json-fil:", inputarg ) 
                print( "Kjører kommando:\nhoved(", myinput['arg1'], ')'  )
                hoved( arg1=myinput['arg1']) 
                
        else: 
            print( "Argument = tekst fra kommandolinje:" ) 
            print( "Kjører kommando: \nhoved(" , inputarg, ")" )  
            
            hoved( inputarg )
       
    else: 
        
        print( "Test av hvordan vi bruker kommandolinje-argumenter ")
        print( "for python-kode kompilert til windows-kjørbare filer (*.exe)")
        print( "To muligheter: ")
        print( "")
        print( "  1. Angi filnavn (*.json) for oppsettfil med nødvendige argumenter")
        print( "  ")
        print( "        test.exe testinput.json")
        print( "  ")
        print( "  2. Angi argumentene direkte fra kommandonlinjen ")
        print( "        ")
        print( '        test.exe "argument 1 (typisk langt og kronglete mappenavn" ')
        print( "")
        print( "")
		
    time.sleep( 2) 
