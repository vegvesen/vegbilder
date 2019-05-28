"""
Oppdatering av vegreferanse-verdier for vegbilder

Flytter alle vegbilder (*.jpg) med tilhørende metadata (*.webp, *.json) til ny 
katalog. Fil og mappenavn blir oppdatert med nye vegreferanseverdier (hvis nødvendig). 


Etterpå må metadatabasen (meta-geo-database) oppdateres med nye filnavn og URL'er.  
""" 
import os
from datetime import datetime
import re
import fnmatch
import json 
import pdb # debug
from copy import deepcopy 
from pathlib import Path
from shutil import copyfile
import sys


import requests
import xmltodict

def visveginfo_veglenkeoppslag( metadata): 
    """
    Mottar et metadata-element, fisker ut det som trengs for å gjøre oppslag på veglenkeID og posisjon,
    henter oppdatert vegreferanse, føyer det til metadata-elementet og sender tilbake. 
    """ 
    
    
    
    idag = str(datetime.now())
    if metadata['stedfestet'].upper() == 'JA' : 
        params = { 'reflinkoid' : metadata['veglenkeid'], 
                    'rellen' : metadata['veglenkepos'],
                    'ViewDate' : idag[0:10] } 
        
        url = 'http://visveginfo-static.opentns.org/RoadInfoService/GetRoadReferenceForNVDBReference' 
        r = requests.get( url, params=params)
        tekstrespons = r.text
        if len( tekstrespons) > 0: 
            try: 
                vvidata = xmltodict.parse( tekstrespons )
            except ExpatError:
                params['info'] = 'Problemer med stedfesting' 
                svar = re.findall( "<p>(.*?)</p>", tekstrespons )
                vvidata = { 'Annen type' : 'feil' } 
                if len(svar) > 0: 
                    params['info2'] = re.findall( "<p>(.*?)</p>", text)
                
        else: 
            params['info'] = 'Stedfesting ikke lenger gyldig vegnett!' 
            vvidata = { 'Stedfestet på' : 'historisk vegnett' } 
        # metadata['ny_visveginfoparams'] =  params 
    else: 
        vvidata = { 'Gyldig veglenkeID og posisjon' : 'finnes ikke' } 
        params = { 'Bildet er ikke stedfestet' : 'Med veglenkeID og posisjon' }


    # Putter viatech XML sist... 
    exif_imageproperties = metadata.pop( 'exif_imageproperties') 
    
    if 'RoadReference' in vvidata.keys(): 

        vvi = vvidata['RoadReference']

        metadata['feltoversikt']     =  vvi['LaneCode']
        metadata['lenkeretning'] =  round( float( vvi['RoadnetHeading']), 3)
        metadata['fylke']        = int( vvi['County'] )
        metadata['kommune']      = int( vvi['Municipality'] ) 
        metadata['vegkat']       = vvi['RoadCategory'] 
        metadata['vegstat']      = vvi['RoadStatus']
        metadata['vegnr']        = int( vvi['RoadNumber'] ) 
        metadata['hp']           = int( vvi['RoadNumberSegment'] ) 
        metadata['meter']        = int( vvi['RoadNumberSegmentDistance']) 

        # Midlertidig suksessflagg, slettes før skriving
        metadata['ny_visveginfosuksess'] = True

    else: 
        
        print( 'Ugyldig vegnett:', params, '\n\t', os.path.join( metadata['mappenavn'], metadata['exif_filnavn'] )) 
        
        if metadata['stedfestet'].upper() == 'JA':
            metadata['stedfestet'] =  'historisk' 

        metadata['vegkat']  = None
        metadata['vegstat'] = None
        metadata['vegnr']   = None
        metadata['hp']      = None
        metadata['meter']      = None

        # Midlertidig suksessflagg, slettes før skriving
        metadata['ny_visveginfosuksess'] = False

        
    metadata['vegreferansedato'] = datetime.today().strftime('%Y-%m%d')      
    metadata['exif_imageproperties'] = exif_imageproperties
    return metadata

def sjekkretning(strekningsdata): 
    """
    Sjekker om metreringsretning er snudd for denne strekningen
    """
    
    retning = 'Ikke snudd' 
    
    # Sorterer på filnavn
    filnavnliste = [ m['exif_filnavn'] for m in strekningsdata['filer'] ]
    myindex = sorted( range( len( filnavnliste)), key=lambda k: filnavnliste[k] )
    
    # # Rundkjøring? 
    # hp = int( strekningsdata['filer'][0]['exif_hp'] ) 
    # if hp >= 400 and hp < 600: 
        # return 'Ikke snudd' 
    
    startMeterNy = None
    sluttMeterNy = None
    startMeterGammel = None
    sluttMeterGammel = None
    antObjekt = len( strekningsdata['filer'] )
    count = 0
    while (not startMeterNy) and count < antObjekt:
        
        if not startMeterGammel: 
            startMeterGammel = float( strekningsdata['filer'][ myindex[count]]['exif_meter'] ) 

        if 'meter' in strekningsdata['filer'][ myindex[count]].keys() and \
                            strekningsdata['filer'][ myindex[count]]['ny_visveginfosuksess']: 
            startMeterNy = float( strekningsdata['filer'][ myindex[count]]['meter'] )
        
        count += 1
    
    count = 0 
    while (not sluttMeterNy) and count < antObjekt: 
        if not sluttMeterGammel: 
            sluttMeterGammel = float( strekningsdata['filer'][myindex[ -1*(count+1)]]['exif_meter'])
        
        if 'meter' in strekningsdata['filer'][myindex[-1*(count+1)]].keys() and \
                    strekningsdata['filer'][myindex[-1*(count+1)]]['ny_visveginfosuksess']: 
            sluttMeterNy  = float( strekningsdata['filer'][myindex[-1*(count+1)]]['meter'] ) 
        count += 1

    gammelGradient = gradientsjekk( startMeterGammel, sluttMeterGammel) 
    if startMeterNy and sluttMeterNy: 
        nyGradient = gradientsjekk( startMeterNy, sluttMeterNy) 
        
        if nyGradient != gammelGradient: 
            retning = 'snudd'
    
    return retning
        
def gradientsjekk( m1, m2): 
    
    if (m2-m1) >= 0: 
        gradient = 'positiv'
    else:
        gradient = 'negativ'
    
    return gradient
    
    
  
def sjekkfelt( metadata, snuretning='Ikke snudd'):
    """
    Lager ny feltkode, som så igjen brukes i fil- og mappenavn 
    """
    
    if snuretning == 'Ikke snudd': 
        metadata['feltkode'] = metadata['exif_feltkode'] 
    else: 
        
        nyFeltKode = None
        gmltFeltNr = int( re.sub( '\D', '', metadata['exif_feltkode'] ) )
        gmlFeltType = re.sub( '\d+', '', metadata['exif_feltkode'] ) 
        if gmltFeltNr % 2 == 0:
            etterlystFeltNr = gmltFeltNr - 1
            backupfelt = '1'
        else: 
            etterlystFeltNr = gmltFeltNr + 1
            backupfelt = '2'
        
        bildenavn = os.path.join( metadata['exif_strekningreferanse'], metadata['exif_filnavn'] )

        muligeFelt = metadata['feltoversikt'].split('#') 
        for felt in muligeFelt: 
            muligFeltNr = int( re.sub( '\D','', felt) )
            muligFeltType = re.sub( '\d+', '', felt) 
 
            if etterlystFeltNr == muligFeltNr: 
                nyFeltKode = felt 
                if gmlFeltType != muligFeltType: 
                    print( 'Mismatch felttype når vi snur retning', 
                            metadata['exif_feltkode'], '=>', nyFeltKode, 'av mulige', 
                            metadata['feltoversikt'], bildenavn )
                
        if not nyFeltKode: 
            print( "Klarte ikke snu feltretning", metadata['exif_feltkode'], 'til noe i', muligeFelt,  bildenavn ) 
            nyFeltKode = metadata['feltoversikt']
        
        metadata['feltkode'] = nyFeltKode
        
    return metadata
        

def lag_strekningsnavn( metadata): 
    """
    Komponerer nytt strekningsnavn og filnavn, og returnerer tuple (strekningsnavn, filnavn) 
    
    Modifiserer IKKE metadata
    """ 
    
    if 'ny_visveginfosuksess' in metadata.keys() and metadata['ny_visveginfosuksess']:
    
        aar = metadata['exif_dato'].split('-')[0]
        fylke = str(metadata['fylke']).zfill(2)
        if metadata['hp'] < 100: 
            hp = str(metadata['hp']).zfill(2)
        else: 
            hp = str(metadata['hp']).zfill(3)
        
        hptekst = 'hp' + hp
        
        # Deler opp navn av typen 06_Ev134/Hp07_Kongsgårdsmoen_E134_X_fv__40_arm 
        # og plukker ut navne-biten av 
        hpbit = metadata['exif_strekningreferanse'].split('/')[1]
        strekningsnavn = '_'.join( hpbit.split('_')[1:] ) 

        vegnr = metadata['vegkat'].upper() + metadata['vegstat'].lower() + \
                    str( metadata['vegnr'] ) 
        vegnavn = '_'.join( [ fylke, vegnr ]) 
        rotnavn = os.path.join( fylke, aar, vegnavn, hptekst) 
        
        
        ## Blir bare kluss med stedsnavn for strekninger 
        # if strekningsnavn: 
            # nystrekning = ( '_'.join( [rotnavn, strekningsnavn ]) )
        # else: 
            # nystrekning = rotnavn
        nystrekning = rotnavn
        
        
        if 'feltkode' in metadata.keys(): 
            felt = 'F' + str( metadata['feltkode'] )
        else: 
            felt = 'F' + str( metadata['exif_feltkode'] ) 
        dato =  '_'.join( metadata['exif_dato'].split('-')[0:3] ) 
        
        
        nystrekning = os.path.join( nystrekning, '_'.join( [felt, dato] ) )
        nyttfilnavn = '_'.join( [   'Fy' + vegnavn, hptekst, felt, 'm' + str( round( metadata['meter'] )) ] )

    else: 
        # Returnerer det gamle navnet på streking og filnavn
        nyttfilnavn = re.sub( '.jpg', '', metadata['exif_filnavn'] ) 
        nystrekning = '/'.join( metadata['temp_gammelfilnavn'].split('/')[-6:-1] )
        nystrekning = re.sub( '-', '_', nystrekning) 
        
    return (nystrekning, nyttfilnavn) 
    
def flyttfiler(gammeltdir='../bilder/regS_orginalEv134/06/2018/06_Ev134/Hp07_Kongsgårdsmoen_E134_X_fv__40_arm',  nyttdir='../bilder/testflytting/test1_Ev134'): 
    
    """
    Flytter bilder (*.jpg) og metadata (*.webp, *.json) over til mappe- og filnavn som er riktig etter 
    gjeldende vegreferanse. 
    """ 
    
    gammelt = lesfiler_nystedfesting(datadir=gammeltdir) 
    
    tempnytt = {} # Midlertidig lager for nye strekninger, før vi evt snur retning
    nytt = {} # her legger vi nye strekninger etter at de evt er snudd. 
    
    t0 = datetime.now()
    
    gammelcount = 0 
    for strekning in gammelt.keys():
        for fil in gammelt[strekning]['filer']: 
            
            gammelcount += 1
            if fil['ny_visveginfosuksess']: 
                (nytt_strekningsnavn, junk)  = lag_strekningsnavn( fil) 
                
            else: 
                nytt_strekningsnavn = str(strekning) 
                
            if not nytt_strekningsnavn in tempnytt.keys():
                tempnytt[nytt_strekningsnavn] = { 'strekningsnavn' : nytt_strekningsnavn, 'filer' : [] }
                
            nyfil = deepcopy( fil) 
            tempnytt[nytt_strekningsnavn]['filer'].append( nyfil) 
    
    tempcount = 0
    tempfilnavn = set()
    for strekning in tempnytt.keys():
        # Sjekker om strekningene skal snus på strekningen relativt til info i EXIF-headeren
        snuretning = sjekkretning( tempnytt[strekning] ) 
        print( strekning, snuretning) 
        
        # Tar med oss info om retningen skal snus og komponerer nye streknings (mappe) og filnavn: 
        for fil in tempnytt[strekning]['filer']: 
            tempcount += 1
            meta = deepcopy( sjekkfelt( fil, snuretning=snuretning) )
            (nystrekning, nyttfilnavn) = lag_strekningsnavn( meta) 
            meta['filnavn'] = nyttfilnavn
            meta['mappenavn'] = nystrekning
            meta['strekningsreferanse'] = '/'.join( nystrekning.split('/')[-3:-1])
            meta['retningsnudd'] = snuretning
            
            tempfilnavn.add( os.path.join( nyttdir, nystrekning, nyttfilnavn) )
            
            if not nystrekning in nytt.keys(): 
                print( strekning, snuretning, '=>\n\t', nystrekning ) 

                nytt[nystrekning] = { 'strekningsnavn' : nystrekning, 'filer' : [] }

            meta2 = deepcopy( meta)
            nytt[nystrekning]['filer'].append( meta2) 
            
    ferdigcount = 0  
    ferdigfilnavn = set()
    for ferdigstrekning in nytt.keys(): 
        print( 'Ny strekningdefinisjon', ferdigstrekning) 
        for eifil in nytt[ferdigstrekning]['filer']:
            ferdigcount += 1
        
            meta = deepcopy( eifil) 
            # Klargjør for selve filflytting-operasjonen
            gammelfil = meta.pop( 'temp_gammelfilnavn' )
            skrivefil = meta['filnavn'] 
            skrivnyfil = os.path.join( nyttdir, ferdigstrekning, skrivefil) 
            # print( 'flytter filer', gammelfil, ' => ', skrivnyfil) 
            ferdigfilnavn.add( skrivnyfil)    
            
            nymappenavn = os.path.join( nyttdir, ferdigstrekning)
            nymappe = Path( nymappenavn ) 
            nymappe.mkdir( parents=True, exist_ok=True)
            
            try: 
                copyfile( gammelfil + '.jpg', skrivnyfil + '.jpg' ) 
            except FileNotFoundError: 
                print( 'Fant ikke fil:', gammelfil+'.jpg') 

            try: 
                copyfile( gammelfil + '.webp', skrivnyfil + '.webp' ) 
            except FileNotFoundError: 
                pass
                # print( 'Fant ikke fil', gammelfil+'.webp') 
            
            # Flytter exif-XML helt nederst i strukturen 
            exif_imageproperties = meta.pop( 'exif_imageproperties')
            meta['exif_imageproperties'] = exif_imageproperties
            
            # Fjerner flagget 
            junk = meta.pop( 'ny_visveginfosuksess' )

            with open( skrivnyfil + '.json', 'w') as f: 
                json.dump( meta, f, indent=4, ensure_ascii=False) 
                
    print("Antall filnavn på ulike steg:", len( tempfilnavn), len(tempfilnavn), len(ferdigfilnavn) )
    dt = datetime.now() - t0
    print( "Tidsforbruk", dt.total_seconds(), 'sekunder') 
    
                
    # pdb.set_trace()

def lesfiler_nystedfesting(datadir='../bilder/regS_orginalEv134/06/2018/06_Ev134/Hp07_Kongsgårdsmoen_E134_X_fv__40_arm'): 
    """
    Finner alle mapper der det finnes *.json-filer med metadata, og sjekker stedfestingen 
    på disse. Returnerer dictionary sortert med 
    med metadata og filnavn sortert på hp-strekning-mappe. 
      
    """

    oversikt = { } 
    

    t0 = datetime.now()
    print( "ny versjon")
    print( t0) 
    # Finner alle mapper med bilder: 
    folders = set(folder for folder, subfolders, files in os.walk(datadir) for file_ in files if os.path.splitext(file_)[1].lower() == '.jpg')
    
    for mappe in folders: 
        print( "leter i mappe", mappe) 
        jsonfiler = findfiles( 'fy*hp*m*.json', where=mappe) 
        
        count = 0 # Debug, mindre datasett
        for bilde in jsonfiler: 
            with open( os.path.join( mappe, bilde) ) as f:
                metadata = json.load( f) 
                
            feltmappe = metadata['exif_mappenavn'].split('/')[-1] 
            strekningsmappe = os.path.join( metadata['mappenavn'], feltmappe) 
            
            # Legger til strekning hvis den ikke finnes i oversikt
            if strekningsmappe not in oversikt.keys(): 
                oversikt[strekningsmappe] = { 'strekningsnavn' : strekningsmappe, 
                                                'filer' : [] }
                count = 0 # Debug, mindre datasett 
                                                
            metadata['temp_gammelfilnavn'] = os.path.join( mappe, 
                                                os.path.splitext( bilde)[0] )
                                                
                                                
            count += 1      # Debug, mindre datasett
            if count <= 10: # Debug, mindre datasett
                pass
            
            # Oppdaterer vegreferanseverdier:
            metadata2 = deepcopy( visveginfo_veglenkeoppslag( metadata) ) 

            oversikt[strekningsmappe]['filer'].append( metadata2) 
    
    print( datetime.now())
    dt = datetime.now() - t0
    print( "Tidsforbruk stedfesting", dt.total_seconds(), 'sekunder')     
    return oversikt
            
        
        
        
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
    
    
if __name__ == "__main__": 

    nyttdir = None
    gammeltdir = None

    # flyttfiler(gammeltdir='vegbilder/testbilder_prosessert/orginal_stedfesting', 
                # nyttdir='vegbilder/testbilder_prosessert/ny_stedfesting')


    print( "Versjon 1.1 27.05.2019") 
    if len( sys.argv) < 2: 
        print( "BRUK:\n")
        print( 'flyttvegbilder.exe "../../testbilder_prosessert/", "../../testbilder_nystedfesting')
        print( '\t... eller ha oppsettdata i json-fil\n')
        print( 'vegbilder_lesexif.exe oppsettfil_flyttvegbilder.json\n') 
        time.sleep( 1.5) 
        
    else: 
        
        if '.json' in sys.argv[1][-5:].lower(): 
            print( 'vegbilder_lesexif: Leser oppsettfil fra', sys.argv[1] ) 
            with open( sys.argv[1]) as f: 
                oppsett = json.load( f) 
        
            if 'orginalmappe' in oppsett.keys():
                gammeltdir = oppsett['orginalmappe']
            
            if 'nymappe' in oppsett.keys():
                nyttdir = oppsett['nymappe'] 
                
        else: 
            gammeltdir = sys.argv[1]
            
            
        if len( sys.argv) > 2: 
            
            if nyttdir: 
                print( "Navn på ny mappe angitt både i oppsettfil og på kommandolinje") 
                print( "Jeg stoler mest på kommandolinja, og lar den overstyre") 
                
            nyttdir = sys.argv[2] 
            
    if not gammeltdir or not nyttdir: 
        print( "STOPP - kan ikke prosessere uten at du angir mappenavn for der bildene finnes og dit oppdatert stedfesting kan skrives") 
    else: 
        flyttfiler( gammeltdir=gammeltdir, nyttdir=nyttdir) 
        
    