"""
Stefester vegbilder; en liten json-fil med metadata finner vi gyldig vegreferanse da bildet ble tatt
Denne fila blir så oppdatert med vegreferanse-informasjon, veglenkeposisjon og koordinat for senterlinje 
hentet fra Visveginfo-tjensten. 
""" 

import os 
import fnmatch 
import re
import glob
import json
from datetime import datetime
import sys
import time

import requests
import xmltodict # Må installeres, rett fram 


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


def visveginfo_vegreferanseoppslag( metadata): 
    """
    Mottar et metadata-element, fisker ut det som trengs for å gjøre oppslag på vegreferanse,
    oppdaterer metadata-elementet og sender det tilbake. 
    """ 
    
    fylke = str(metadata['exif_fylke']).zfill(2) 
    kommune = '00' 
    vegnr = str( metadata['exif_vegnr']).zfill(5)
    hp = str(metadata['exif_hp']).zfill(3)
    meter = str(round( float( metadata['exif_meter'] ))).zfill(5) 
    
    vegref = fylke + kommune + metadata['exif_vegkat'] + metadata['exif_vegstat'] + \
            vegnr + hp + meter 
            
    params = { 'roadReference' : vegref, 'ViewDate' : metadata['exif_dato'], 'topologyLevel' : 'Overview' } 
    
    url = 'http://visveginfo-static.opentns.org/RoadInfoService3d/GetRoadReferenceForReference' 
    r = requests.get( url, params=params)
    vvidata = xmltodict.parse( r.text )
    
    # Putter viatech XML sist... 
    exif_imageproperties = metadata.pop( 'exif_imageproperties') 

    if 'ArrayOfRoadReference' in vvidata.keys() and 'RoadReference' in vvidata['ArrayOfRoadReference'].keys(): 
        
        
        
        vvi = vvidata['ArrayOfRoadReference']['RoadReference']

        metadata['senterlinjeposisjon'] = 'srid=25833;POINT Z( ' + \
                                        str( round( float( vvi['RoadNetPosition']['X']), 3)) + ' ' + \
                                        str( round( float( vvi['RoadNetPosition']['Y']), 3))  + ' ' + \
                                        str( round( float( vvi['RoadNetPosition']['Z']), 3)) + ' )'
                      
                      
        metadata['veglenkeid']  = int( vvi['ReflinkOID'] )
        metadata['veglenkepos'] = round( float( vvi['Measure']), 8)
        metadata['allefelt']    =  vvi['LaneCode']
        metadata['lenkeretning'] =  round( float( vvi['RoadnetHeading']), 3)
        # metadata['visveginfoparams'] =  params 
        # metadata['visveginfosuksess'] =  True 
        metadata['stedfestet'] = 'JA'
        
        # Legger på vegreferanse-informasjon slik at bildet blir søkbart. 
        metadata['ny_allefelt']     =  vvi['LaneCode']
        metadata['ny_lenkeretning'] =  round( float( vvi['RoadnetHeading']), 3)
        metadata['fylke']        = int( vvi['County'] )
        metadata['kommune']      = int( vvi['Municipality'] ) 
        metadata['vegkat']       = vvi['RoadCategory'] 
        metadata['vegstat']      = vvi['RoadStatus']
        metadata['vegnr']        = int( vvi['RoadNumber'] ) 
        metadata['hp']           = int( vvi['RoadNumberSegment'] ) 
        metadata['meter']        = int( vvi['RoadNumberSegmentDistance']) 

        metadata['vegreferansedato'] = params['ViewDate'] 
        
    else: 
        print( 'Ugyldig vegreferanse', vegref, 'for dato', params['ViewDate'] ) 
        geometry = None
        # metadata['visveginfoparams'] = params
        metadata['visveginfosuksess'] =  False 
        metadata['stedfestet'] = 'Ugyldig'
        
    metadata['exif_imageproperties'] = exif_imageproperties

    return metadata

def stedfest_jsonfiler( mappe='../bilder/regS_orginalEv134', overskrivStedfesting=False ):
    t0 = datetime.now()
    jsonfiler = recursive_findfiles( 'fy*hp*m*.json', where=mappe) 
    count = 0
 
    for (nummer, filnavn) in enumerate(jsonfiler): 
        with open( filnavn ) as f: 
            meta = json.load(f)    
 
        # Stedfester kun dem som ikke er stedfestet fra før: 
        if overskrivStedfesting or (not 'stedfestet' in meta.keys() or \
                                            meta['stedfestet'].upper() != 'JA'): 
            count += 1
            meta = visveginfo_vegreferanseoppslag( meta) 
            with open( filnavn, 'w') as fw: 
                json.dump( meta, fw, ensure_ascii=False, indent=4) 
                
        if nummer == 10 or nummer == 100 or nummer % 500 == 0: 
            dt = datetime.now() - t0 
            print( 'Stedfester bilde', nummer+1, 'av', len(jsonfiler), dt.total_seconds(), 'sekunder') 
 
    dt = datetime.now() - t0
    print( 'Stedfestet', count, 'av', len(jsonfiler), 'vegbilder på', dt.total_seconds(), 'sekunder') 
 
def test( ): 
    jsonfiler = recursive_findfiles( 'fy*hp*m*.json', where='.') 
    
    with open( jsonfiler[0]) as f: 
        meta = json.load(f)
        
    meta = visveginfo_vegreferanseoppslag( meta) 
    return meta
    
if __name__ == '__main__': 

    datadir = None
    overskrivStedfesting = False
    
    print( "Versjon 1.0 27.05.2019") 
    if len( sys.argv) < 2: 

        print( "BRUK:\n")
        print( 'stedfest_vegbilder.exe "../eksempelbilder/"\n')
        print( '\t... eller ha oppsettdata i json-fil\n')
        print( 'stedfest_vegbilder.exe stedfest_vegbilder_oppsettfil.json') 
        time.sleep( 1.5) 
    
    else: 
    
        if len( sys.argv ) > 2 and 'overskriv' in sys.argv[2].lower(): 
            overskrivStedfesting = True
            print('Kommandolinje-argument', sys.argv[2], ' => vil også stedfeste', 
                    'også bilder som er stedfestet fra før' )     
    
        if '.json' in sys.argv[1][-5:].lower(): 
            print( 'vegbilder_lesexif: Leser oppsettfil fra', sys.argv[1] ) 
            with open( sys.argv[1]) as f: 
                oppsett = json.load( f) 

            if 'datadir' in oppsett.keys(): 
                datadir = oppsett['datadir']
                
            if 'overskrivStedfesting' in oppsett.keys(): 
                tmp_overskriv = oppsett['overskrivStedfesting']
                if tmp_overskriv: 
                    print( 'Beskjed om å overskrive gamle *.json metadata funnet i ', 
                        sys.argv[1] ) 
                
                if overskrivStedfesting and not tmp_overskriv: 
                    print( 'Konflikt mellom parametre på kommandolinje', 
                        '(overskriv gamle json-metadata) og oppsettfil', sys.argv[1], 
                        '(IKKE overskriv)') 
                    print( 'Stoler mest på kommandolinje, overskriver gamle *.json metadata')
                else: 
                    overskrivStedfesting = tmp_overskriv                
        
        else: 
            datadir = sys.argv[1]
            
        if not datadir: 
            print( 'Påkrevd parameter "datadir" ikke angitt, du må fortelle meg hvor vegbildene ligger') 
        else: 
            print( 'Stedfester metadata i mappe', datadir ) 
            stedfest_jsonfiler( datadir, overskrivStedfesting=overskrivStedfesting )  
    