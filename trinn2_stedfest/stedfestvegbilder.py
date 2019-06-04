"""
Stefester vegbilder; en liten json-fil med metadata finner vi gyldig vegreferanse da bildet ble tatt
Denne fila blir så oppdatert med vegreferanse-informasjon, veglenkeposisjon og koordinat for senterlinje 
hentet fra Visveginfo-tjensten. 
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

import requests
import xmltodict # Må installeres, rett fram 

def utledMappenavn( mappe ):
    mapper = mappe.split('/') 
    return '/'.join( mapper[-5:-1]) 


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
        metadata['feltoversikt']    =  vvi['LaneCode']
        metadata['feltoversikt_perbildedato']     =  vvi['LaneCode']
        metadata['lenkeretning'] =  round( float( vvi['RoadnetHeading']), 3)
        metadata['lenkeretning_perbildedato'] =  round( float( vvi['RoadnetHeading']), 3)
        # metadata['visveginfoparams'] =  params 
        # metadata['visveginfosuksess'] =  True 
        metadata['stedfestet'] = 'JA'
        
        # Legger på vegreferanse-informasjon slik at bildet blir søkbart. 
        metadata['fylke']        = int( vvi['County'] )
        metadata['kommune']      = int( vvi['Municipality'] ) 
        metadata['vegkat']       = vvi['RoadCategory'] 
        metadata['vegstat']      = vvi['RoadStatus']
        metadata['vegnr']        = int( vvi['RoadNumber'] ) 
        metadata['hp']           = int( vvi['RoadNumberSegment'] ) 
        metadata['meter']        = int( vvi['RoadNumberSegmentDistance']) 

        metadata['vegreferansedato'] = params['ViewDate'] 
        
        metadata['feltkode'] = metadata['exif_feltkode']
        if 'filnavn' not in metadata.keys(): 
            metadata['filnavn'] = re.sub( '.jpg', '', metadata['exif_filnavn'] ) 
            metadata['filnavn'] = re.sub( '.JPG', '', metadata['filnavn'] ) 

        metadata['retningsnudd'] = 'ikkesnudd'
        metadata['strekningsreferanse'] = metadata['exif_strekningreferanse']
            
    else: 
        print( 'Ugyldig vegreferanse', vegref, 'for dato', params['ViewDate'] ) 
        geometry = None
        # metadata['visveginfoparams'] = params
        metadata['visveginfosuksess'] =  False 
        metadata['stedfestet'] = 'Ugyldig'
       
    metadata['stedfestingdato'] = datetime.today().strftime('%Y-%m-%d')
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
        if overskrivStedfesting or (not 'stedfestet' in meta.keys() or       \
                                ('stedfestet' in meta.keys()                 \
                                    and isinstance( meta['stedfestet'], str) \
                                    and meta['stedfestet'].upper() != 'JA' )): 
            count += 1
            meta = visveginfo_vegreferanseoppslag( meta) 
            with open( filnavn, 'w') as fw: 
                json.dump( meta, fw, ensure_ascii=False, indent=4) 
                
        if nummer == 10 or nummer == 100 or nummer % 500 == 0: 
            dt = datetime.now() - t0 
            print( 'Stedfester bilde', nummer+1, 'av', len(jsonfiler), dt.total_seconds(), 'sekunder') 
 
    dt = datetime.now() - t0
    print( 'Stedfestet', count, 'av', len(jsonfiler), 'vegbilder på', dt.total_seconds(), 'sekunder') 


def sorter_mappe_per_meter(datadir, overskrivStedfesting=False): 
    # Finner alle mapper med json-filer, sorterer bildene med forrige-neste logikk
    # 
    # folders = set(folder for folder, subfolders, files in os.walk(datadir) for file_ in files if os.path.splitext(file_)[1] == '.')
    folders = set(folder for folder, subfolders, files in os.walk(datadir) for file_ in files if re.search( "fy[0-9]{1,2}.*hp.*m[0-9]{1,6}.json", file_, re.IGNORECASE)  )

    for mappe in folders: 
        print( "Leter i mappe", mappe) 

        templiste = []
        meta_datafangst_uuid = str( uuid.uuid4() )

        jsonfiler = findfiles( 'fy*hp*m*.json', where=mappe) 

        # Finner feltinformasjon ut fra mappenavn F1_yyyy_mm_dd 
        feltnr = 1 # Default
        (rotmappe, feltmappe) = os.path.split( mappe) 
        feltmappebiter = feltmappe.split( '_') 
        meta_kjfelt = feltmappebiter[0]
        
        if len( feltmappebiter) != 4 or meta_kjfelt[0].upper() != 'F': 
            print( "QA-feil: Feil mappenavn, forventer F<feltnummer>_<år>_<mnd>_<dag>", mappe) 
        try: 
            feltnr = int( re.sub( "\D", "", meta_kjfelt )) 
        except ValueError:
            print( 'QA-feil: Klarte ikke finne feiltinformasjon for mappe', mappe) 
        
        if feltnr % 2 == 0:
            meta_retning = 'MOT'
            jsonfiler.sort( reverse=True)
        else: 
            meta_retning = 'MED'
            jsonfiler.sort() 
            
        for eijsonfil in jsonfiler: 
            
            fname = os.path.join( mappe, eijsonfil) 
            try: 
                with open( fname) as f: 
                    metadata = json.load( f) 
            except OSError as myErr: 
                print( "Kan ikke lese inn bildefil", fname, str(myErr)) 
                
            else: 
                
            
               # Legger vianova-xml'en sist
                imageproperties = metadata.pop( 'exif_imageproperties' ) 
                
                metadata['temp_filnavn'] =  fname

                
                # Retning og feltkode
                metadata['retning'] = meta_retning
                metadata['filnavn_feltkode'] = meta_kjfelt
              
                
                # Utleder riktig mappenavn 
                metadata['mappenavn'] = utledMappenavn( mappe) 
            
                # Unik ID for hvert bilde, og felles ID for alle bilder i samme mappe
                metadata['datafangstuuid'] = meta_datafangst_uuid
                if not 'bildeuiid' in metadata.keys() or not metadata['bildeuiid']: 
                    metadata['bildeuiid'] = str( uuid.uuid4() ) 
                metadata['forrige_uuid'] = None
                metadata['neste_uuid'] = None
                
                
                # Legger til et par tagger for administrering av metadata
                metadata['stedfestet'] = 'NEI'
                metadata['indeksert_i_db'] = None

                # Legger vianova-xml'en sist
                metadata['exif_imageproperties' ] = imageproperties
                
                # Føyer på den korte listen
                templiste.append(  metadata)            

         # Lenkar sammen den lenkede listen 
        for ii in range( 0, len(templiste)): 
            
            # Forrige element i listen
            if ii > 0 and ii < len(templiste): 
                templiste[ii]['forrige_uuid']    = templiste[ii-1]['bildeuiid']
            
            # Neste element     
            if ii < len(templiste)-1: 
                templiste[ii]['neste_uuid']    = templiste[ii+1]['bildeuiid']

        # Skriver json-fil med metadata til fil
        for jsonfil in templiste:

            filnavn = jsonfil.pop( 'temp_filnavn' ) 
                
            with open( filnavn, 'w') as f: 
                json.dump( jsonfil, f, indent=4, ensure_ascii=False) 

 
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
    
    
def formatvegref( fylke, kommune, vegkat, vegstat, vegnummer, hp, meter): 
    """
    Formatterer en vegreferanse-streng som kan brukes i kall til visveginfo
    """
    
    vegref = str(fylke).rjust(2, '0') + str(kommune).rjust(2, '0') + vegkat.upper() + vegstat.upper() + \
            str(vegnummer).rjust(5, '0') + str(hp).rjust(3, '0') + str(meter).rjust(5, '0') 
    return vegref

 
def test( ): 
    jsonfiler = recursive_findfiles( 'fy*hp*m*.json', where='.') 
    
    with open( jsonfiler[0]) as f: 
        meta = json.load(f)
        
    meta = visveginfo_vegreferanseoppslag( meta) 
    return meta
    
if __name__ == '__main__': 

    datadir = None
    overskrivStedfesting = False
    
    versjonsinfo = "Versjon 2.0 den 3. juni 2019 kl 15:31"
    print( versjonsinfo ) 
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
            sorter_mappe_per_meter( datadir ) 
            stedfest_jsonfiler( datadir, overskrivStedfesting=overskrivStedfesting )  

    print( versjonsinfo ) 
 