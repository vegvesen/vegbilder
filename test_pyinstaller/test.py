# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""

import time
import json
import sys

def hoved( arg1='dummy', arg2="Uendret, bruker standard i hovedfunksjonen"): 
    print( "Hovedrutine, her er mine argumenter:")
    print( '\tArgument 1:', arg1, "argument2", arg2) 
    time.sleep( 1)
    
    
if __name__ == "__main__":

    arg1 = None
    arg2 = "Defaultverdi for argument 2" 
    flagg_arg2_i_json = False
    

    if len( sys.argv) > 1: 
        print( "Test av argumenter til kompilert python-kode (*.exe" ) 
        inputarg = sys.argv[1]
        print( "\tArgument 1 (arg1) =", inputarg) 
   
        # Angitt argument #2 ? 
        if len( sys.argv) > 2: 
            arg2 = sys.argv[2] 
            print( "\tArgument 2 (arg2) =", arg2) 
        else: 
            print( "\tIkke noe argument nummer 2") 

        # Leser oppsett fra *.json-fil    
        if '.json' in inputarg[-5:].lower():
            with open( inputarg) as f: 
                myjsoninput = json.load( f) 

            print( "Henter argumenter fra angitt .json-fil", inputarg ) 

            if 'arg1' in myjsoninput.keys(): 
                print( "Fant argument arg1 i .json-fil", inputarg) 
                arg1 = myjsoninput['arg1']
            else: 
                print( 'Fant ingen oppføring "arg1" i json-fil', inputarg )
                
            if 'arg2' in myjsoninput.keys():
                print( "Fant argument arg2 i .json-fil", inputarg) 
                arg2 = myjsoninput['arg2']
                flagg_arg2_i_json = True
            else: 
                print( 'Fant ingen oppføring "arg2" i json-fil, vil bruke defaultverdi=', arg2) 
           
        else: 
            arg1 = inputarg
 
        
        # Angitt argument #2 ? 
        if len( sys.argv) > 2: 
            if flagg_arg2_i_json: 
                print( "Konflikt! Argument #2 oppgis både i json-fil og på kommandolinje!") 
                print( "kommandolinje", sys.argv[2] ) 
                print( "Json-fil", arg2) 
                print( "Lar kommandolinje overstyre json-fil for arg2") 

            arg2 = sys.argv[2] 
                
        # Klar til å kjøre funksjon
        print( "Kjører funksjon hoved( arg1=", arg1, "arg2=", arg2, ")" ) 
        hoved( arg1=arg1, arg2=arg2) 
        
       
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
