# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""

import json
import sys
import requests 

def hoved( proxies, lenker=[ { "url" : "http://example.com", "params" : "" } ]  ): 

    for lenke in lenker: 
        print( "Henter",  lenke["url"], lenke['params'] ) 
        # print( '\tUten proxy:') 
        # r = requests.get( lenke['url'], params=lenke['params'] ) 
        # if r.ok: 
            # print( '\t\tSUKSESS') 
        # else: 
            # print( '\t\t??? status kode:', r.status_code ) 
        
        
        # print( '\tMed proxy' )
        r = requests.get( lenke['url'], params=lenke['params'], proxies=proxies ) 
        if r.ok: 
            print( '\t\tSUKSESS') 
        else: 
            print( '\t\t??? status kode:', r.status_code ) 
        

    
    
if __name__ == "__main__":

    versjonsinfo = "versjon 1.1, 27.05.2019"
    print( versjonsinfo ) 

    proxies = None
    lenker = { "url" : "http://example.com", "params" : ""  }

    if len( sys.argv) > 1: 
        print( "Test av argumenter til kompilert python-kode (*.exe" ) 
        inputarg = sys.argv[1]
        print( "\tArgument 1 (arg1) =", inputarg) 
   

        # Leser oppsett fra *.json-fil    
        if '.json' in inputarg[-5:].lower():
            with open( inputarg) as f: 
                myjsoninput = json.load( f) 

            print( "Henter argumenter fra angitt .json-fil", inputarg ) 

            if 'proxies' in myjsoninput.keys(): 
                proxies = myjsoninput['proxies']
                
            if 'lenker' in myjsoninput.keys():
                lenker = myjsoninput['lenker'] 
                
           
        else: 
            proxies = inputarg
 
                        
        # Klar til å kjøre funksjon
        print( "Kjører funksjon hoved( proxies=", proxies) 
        hoved( proxies, lenker = lenker ) 
        
       
    else: 
        
        print( "Du må oppgi filnavn på oppsettfil (*.json)")
 

    print( versjonsinfo ) 
