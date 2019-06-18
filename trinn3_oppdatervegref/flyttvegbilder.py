"""
Oppdatering av vegreferanse-verdier for vegbilder

Kopierer alle vegbilder (*.jpg) med tilhørende metadata (*.webp, *.json) til ny 
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
import logging
from xml.parsers.expat import ExpatError
import time



import requests
import xmltodict

import duallog


def anropvisveginfo( url, params, filnavn, proxies='', ventetid=15): 
    """
    Anroper visveginfo og har en del feilhåndtering-logikk. Prøver på ny etter en pause ved nettverksfeil eller overbelastning
    """ 
    
    logging.debug( ' '.join( [ 'Skal anrope visveginfo:', url, str(params), filnavn ] ) )  
    count = 0
    sovetid = 0 
    anropeMer = True 
    while count < 4 and anropeMer: 
        count += 1
        r = requests.get( url, params=params, proxies=proxies) 
        svartekst = r.text
        
        # Tom returverdi = veglenkeposisjon finnes ikke. 
        # XML-dokument med <RoadReference ... = godkjent
        # Alt anna = feilmelding fra server (Unavailable etc...) 
        if '<RoadReference' in svartekst or len( svartekst) == 0: 
            anropeMer = False 
        
        if count > 1 and anropeMer: 
            sovetid = sovetid + count * ventetid
            logging.warning( ' '.join( [ "Visvegionfo-kall FEILET", url, str(params),  filnavn, 'Svar fra Visveginfo:' ] ) )
            logging.warning( svartekst)  
            logging.info( ' '.join( [ "prøver igjen om", str( sovetid), "sekunder" ] ) ) 
            time.sleep( sovetid) 

    return svartekst



def visveginfo_veglenkeoppslag( metadata, filnavn='', proxies=''): 
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
        r = requests.get( url, params=params, proxies=proxies)
        logging.debug( r.url) 
        tekstrespons = r.text
        if len( tekstrespons) > 0: 
            try: 
                vvidata = xmltodict.parse( tekstrespons )
            except ExpatError as myErr:
                params['info'] = 'Problemer med stedfesting' 
                svar = re.findall( "<p>(.*?)</p>", tekstrespons )
                vvidata = { 'Annen type' : 'feil' } 
                if len(svar) > 0: 
                    params['info2'] = re.findall( "<p>(.*?)</p>", text)
                logging.warning( ' '.join([ 'Problemer med stedfesting', 
                    filnavn, str(myErr), tekstrespons ] ) ) 
                
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
        
        logging.info( ' '.join( [ 'Ugyldig vegnett:', str( params ), 
                                os.path.join( metadata['mappenavn'], metadata['exif_filnavn'] ) ] ) ) 
        
        if metadata['stedfestet'].upper() == 'JA':
            metadata['stedfestet'] =  'historisk' 

        metadata['vegkat']  = None
        metadata['vegstat'] = None
        metadata['vegnr']   = None
        metadata['hp']      = None
        metadata['meter']      = None

        # Midlertidig suksessflagg, slettes før skriving
        metadata['ny_visveginfosuksess'] = False

        
    metadata['vegreferansedato'] = datetime.today().strftime('%Y-%m-%d')      
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
                    logging.warning( ' '.join( [ 'Mismatch felttype når vi snur retning', 
                            metadata['exif_feltkode'], '=>', nyFeltKode, 'av mulige', 
                            metadata['feltoversikt'], bildenavn ] ) )
                
        if not nyFeltKode: 
            logging.warning( ' '.join( [ "Klarte ikke snu feltretning", metadata['exif_feltkode'], 
                                        'til noe i', muligeFelt,  bildenavn ] ) ) 
            nyFeltKode = metadata['feltoversikt']
        
        metadata['feltkode'] = nyFeltKode
        
    return metadata
        
def plukkstedsnavn( hpnavn, ukjent=''): 
    """
    Plukker ut stedsnavn-komponenten av navnet hp05_Granåsen eller hp50_X_Ditt_Fv309_datt
    
    Nøkkelord ukjent='' kan detaljstyre hva som er returverdi hvis vi ikke har noe stedsnavn 
    """ 
    
    stedsnavn = '_'.join( hpnavn.split( '_')[1:] ) 
    
    if not stedsnavn: 
        stedsnavn = ukjent
        
    return stedsnavn 
    


def lag_strekningsnavn( metadata): 
    """
    Komponerer nytt strekningsnavn og filnavn, og returnerer tuple (strekningsnavn, filnavn, stedsnavn) 
    
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
        stedsnavn = plukkstedsnavn( hpbit ) 

        vegnr = metadata['vegkat'].upper() + metadata['vegstat'].lower() + \
                    str( metadata['vegnr'] ) 
        
        # E, R skal ha - mellom fylke og vegkat, mens F skal ha _
        # Dette for at sortering i filutforsker skal liste E, R før F
        if metadata['vegkat'].upper() in [ 'E', 'R']:         
            vegnavn = '_'.join( [ fylke, vegnr ]) 
        else: 
            vegnavn = '-'.join( [ fylke, vegnr ]) 
            
        
        rotnavn = os.path.join( fylke, aar, vegnavn, hptekst) 
        
        
        ## Blir bare kluss med stedsnavn for strekninger 
        # if stedsnavn: 
            # nystrekning = ( '_'.join( [rotnavn, stedsnavn ]) )
        # else: 
            # nystrekning = rotnavn
        nystrekning = rotnavn
        
        if 'feltkode' in metadata.keys(): 
            felt = 'F' + str( metadata['feltkode'] )
        else: 
            felt = 'F' + str( metadata['exif_feltkode'] ) 
        dato =  '_'.join( metadata['exif_dato'].split('-')[0:3] )   
        
        nystrekning = os.path.join( nystrekning, '_'.join( [felt, dato] ) )
        nyttfilnavn = '_'.join( [   'Fy' + vegnavn, hptekst, felt, 'm' + str( round( metadata['meter'] )).zfill(5) ] )

        # pdb.set_trace()

    else: 
        # Returnerer det gamle navnet på streking og filnavn
        nyttfilnavn = re.sub( '.jpg', '', metadata['exif_filnavn'] ) 
        tmpmapper = mypathsplit( metadata['temp_gammelfilnavn'], 6)
        
        tmpmapper[-3] = 'HISTORISK-' + tmpmapper[-3] 
        nystrekning = '/'.join( tmpmapper[-6:-1] ) 
                
        stedsnavn = '' # Stedsnavn står allerede i gammelt filnavn, trenger ikke føye det til 2 ganger
                
    return (nystrekning, nyttfilnavn, stedsnavn) 
    
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
   
def uniktstedsnavn( mydict, stedsnavn): 
    """
    Sjekker at stedsnavn kun forekommer 1 og kun 1 gang
    """
    
    count = 0
    for kk in mydict.keys():
        if stedsnavn in mydict[kk]: 
            count += 1
            
    if count == 1: 
        return True
    else: 
        return False 
    
   
def flyttfiler(gammeltdir='../bilder/regS_orginalEv134/06/2018/06_Ev134/Hp07_Kongsgårdsmoen_E134_X_fv__40_arm',  
                nyttdir='../bilder/testflytting/test1_Ev134', proxies='', stabildato='1949-31-12'): 
    
    """
    Kopierer bilder (*.jpg) og metadata (*.webp, *.json) over til mappe- og filnavn som er riktig etter 
    gjeldende vegreferanse. 
    """ 
 
    logging.info( "Kopierer bilder fra: " + gammeltdir ) 
    logging.info( "                til: " + nyttdir ) 
    
    gammelt = lesfiler_nystedfesting(datadir=gammeltdir, proxies=proxies, stabildato=stabildato) 
    
    tempnytt = { } # Midlertidig lager for nye strekninger, før vi evt snur retning
    nytt = {} # her legger vi nye strekninger etter at de evt er snudd. 
    
    t0 = datetime.now()
    
    # Datastruktur som holder på relasjonen 06_Ev134_hp5 <=> Granåsen
    # Hvis vi skal gjenbruke navnet på strekningen (Granåsen) så må vi 
    # sikre at det er 1:1 mellom gammmel og ny HP-inndeling. 
    # Dvs at Granåsen ikke brukes på flere HP-inndelinger enn denne. 
    # Vi bygger opp en datastruktur som ser slik ut
    # 
    #   hpnavn = { '06_Ev134' { 'hp05' : set( 'Granåsen' ), 
    #                            'hp06' : set( 'X1_Asdf_X2' ) 
    #                 }
    #           
    # Hvis hvert sett kun har ett medlem, og dette medlemmet ikke finnes i noen av de andre 
    # hp-elementene for '06_Ev134' så kan vi gjenbruke navnet. 

    hpnavn = { } 
    
    gammelcount = 0 
    for strekning in gammelt.keys():
        for fil in gammelt[strekning]['filer']: 
            
            gammelcount += 1
            if fil['ny_visveginfosuksess']: 
                (nytt_strekningsnavn, junk, stedsnavn)  = lag_strekningsnavn( fil) 
                
            else: # Mangler stefesting = historiske data
                (rot, hpmappenavn, feltmappenavn) = mypathsplit( strekning, 2) 
                stedsnavn =  plukkstedsnavn( hpmappenavn )  
                nytt_strekningsnavn = '/'.join( [ rot, 'HISTORISK-'+hpmappenavn, feltmappenavn ] )
                
            if not nytt_strekningsnavn in tempnytt.keys():
                tempnytt[nytt_strekningsnavn] = { 'strekningsnavn' : nytt_strekningsnavn, 'filer' : [] }
            
            
            nyfil = deepcopy( fil) 
            tempnytt[nytt_strekningsnavn]['filer'].append( nyfil) 
            
            # Populerer "hpnavn-datastrukturen med verdier
            if stedsnavn: 
                (rot, hp, felt) = mypathsplit( nytt_strekningsnavn, 2 ) 
                if not rot in hpnavn.keys(): 
                    hpnavn[rot] = {} 
                    
                
                if not hp in hpnavn[rot].keys(): 
                    hpnavn[rot][hp] = {  stedsnavn }
                else: 
                    hpnavn[rot][hp].add( stedsnavn ) 
            
    tempcount = 0
    tempfilnavn = set()
    
    for strekning in tempnytt.keys():
        # Sjekker om strekningene skal snus på strekningen relativt til info i EXIF-headeren
        snuretning = sjekkretning( tempnytt[strekning] ) 
        # logging.info( strekning + " " +  snuretning) 
        
        # Tar med oss info om retningen skal snus og komponerer nye streknings (mappe) og filnavn: 
        for fil in tempnytt[strekning]['filer']: 
            tempcount += 1
            meta = deepcopy( sjekkfelt( fil, snuretning=snuretning) )
            (nystrekning, nyttfilnavn, stedsnavn) = lag_strekningsnavn( meta) 
            
            # Føyer til stedsnavn hvis vi har et og det er unikt: 
            (rot, hp, felt) = mypathsplit( nystrekning, 2) 
            if stedsnavn and rot in hpnavn.keys() and uniktstedsnavn( hpnavn[rot], stedsnavn): 
                hp = '_'.join( [ hp, stedsnavn ] ) 
            nystrekning = '/'.join( [ rot, hp, felt] ) 
            
            meta['filnavn'] = nyttfilnavn
            meta['mappenavn'] = nystrekning
            meta['strekningsreferanse'] = '/'.join( nystrekning.split('/')[-3:-1])
            meta['retningsnudd'] = snuretning
            
            tempfilnavn.add( os.path.join( nyttdir, nystrekning, nyttfilnavn) )
            
            if not nystrekning in nytt.keys(): 
            
                # gmltStrNavn = '/'.join( meta['temp_gammelfilnavn'].split('/')[-6:-1] ) 
                gmlnavn = mypathsplit( meta['temp_gammelfilnavn'], 6) 
                gmltStrNavn = '/'.join( gmlnavn[-6:-1] ) 
                # pdb.set_trace()
                
                snuindikator = snuretning
                if snuretning == 'snudd': 
                    snuindikator = snuretning.upper()
            
                logging.info( " ".join( [ 'Mappenavn', gmltStrNavn, snuindikator, '=>', nystrekning ] ) ) 

                nytt[nystrekning] = { 'strekningsnavn' : nystrekning, 'filer' : [] }

            meta2 = deepcopy( meta)
            nytt[nystrekning]['filer'].append( meta2) 
            
    ferdigcount = 0  
    count_manglerwebpfil = 0 
    ferdigfilnavn = set()

    # holder styr på hvor vi er hen: 
    mappeCount = 0
    antallMapper = str( len( nytt.keys()) ) 
    
    # teller opp om bildet finnes fra før med samme filnavn
    countBildetFinnes = 0 
    countJsonFinnes = 0
    countWebpFines = 0 
    
    for ferdigstrekning in nytt.keys(): 
        # logging.info( 'Ny strekningdefinisjon: ' + ferdigstrekning) 
        mappeCount += 1
        for eifil in nytt[ferdigstrekning]['filer']:
            ferdigcount += 1
        
            if ferdigcount in (1, 5, 10, 50) or ferdigcount % 100 == 0: 
                logging.info( ' '.join( [ 'Kopierer fil ', str( ferdigcount ), 'av', str( tempcount), 
                                            'mappe', str( mappeCount), 'av', antallMapper ] ) ) 
        
            meta = deepcopy( eifil) 
            # Klargjør for selve filflytting-operasjonen
            gammelfil = meta.pop( 'temp_gammelfilnavn' )
            skrivefil = meta['filnavn'] 
            skrivnyfil = os.path.join( nyttdir, ferdigstrekning, skrivefil) 
            logging.debug( ' '.join( ['ENDRINGSINFO Kopierer filer', gammelfil, ' => ', skrivnyfil ]) ) 
            ferdigfilnavn.add( skrivnyfil)    
                        
            nymappenavn = os.path.join( nyttdir, ferdigstrekning)
            nymappe = Path( nymappenavn ) 
            nymappe.mkdir( parents=True, exist_ok=True)
            
            try: 
                copyfile( gammelfil + '.jpg', skrivnyfil + '.jpg' ) 
            except FileNotFoundError: 
                logging.error( 'Fant ikke JPG-fil:' + gammelfil+'.jpg') 

            try: 
                copyfile( gammelfil + '.webp', skrivnyfil + '.webp' ) 
            except FileNotFoundError: 
                count_manglerwebpfil += 1
            
            # Flytter exif-XML helt nederst i strukturen 
            exif_imageproperties = meta.pop( 'exif_imageproperties')
            meta['exif_imageproperties'] = exif_imageproperties
            
            # Fjerner flagget 
            junk = meta.pop( 'ny_visveginfosuksess' )

            with open( skrivnyfil + '.json', 'w', encoding='utf-8') as f: 
                json.dump( meta, f, indent=4, ensure_ascii=False) 

    if count_manglerwebpfil > 0: 
        logging.warning( "Mangler " + str(count_manglerwebpfil) + " webp-filer"  ) 
    logging.info( " ".join( [ "Antall filnavn på ulike steg:", str( len( tempfilnavn)), str( len(ferdigfilnavn)) ]) )
    dt = datetime.now() - t0
    logging.info( " ".join( [ "Tidsforbruk", str( dt.total_seconds()), 'sekunder' ])) 
    
                
    # pdb.set_trace()

def sjekkdato( nyeste, eldste): 
    """
    Sjekker om den første datoen er nyere enn den eldste (TRUE), eller om de er byttet om
    
    Dato = tekststreng på formen '2019-03-31' 
    """
    mylist = [ nyeste, eldste ]
    mylist_sortert = sorted( mylist) 
    
    if mylist[0] == mylist_sortert[0]: 
        return True
    else: 
        return False


def lesfiler_nystedfesting(datadir='../bilder/regS_orginalEv134/06/2018/06_Ev134/Hp07_Kongsgårdsmoen_E134_X_fv__40_arm', 
                        proxies='', stabildato='1949-12-31'): 
    """
    Finner alle mapper der det finnes *.json-filer med metadata, og sjekker stedfestingen 
    på disse. Returnerer dictionary sortert med 
    med metadata og filnavn sortert på hp-strekning-mappe. 
      
    """

    oversikt = { } 
    count_fatalt = 0 
    count_ferskvare = 0 

    t0 = datetime.now()
    logging.info(str( t0) )
    # Finner alle mapper med bilder: 
    folders = set(folder for folder, subfolders, files in os.walk(datadir) for file_ in files if os.path.splitext(file_)[1].lower() == '.jpg')
    
    for mappe in folders: 
        logging.info( "leter i mappe " + mappe) 
        jsonfiler = findfiles( 'fy*hp*m*.json', where=mappe) 
        metadata = None
        count = 0 # Debug, mindre datasett
        for bilde in jsonfiler: 
            fname = os.path.join( mappe, bilde)
            try:
                with open( fname ) as f:
                    metadata = json.load( f) 

            except UnicodeDecodeError as myErr: 
                logging.warning( ' '.join( [  "Tegnsett-problem, prøver å fikse:", fname, str(myErr) ] ) )  
                
                try: 
                    with open( fname, encoding='latin-1') as f: 
                        text = f.read()
                    textUtf8 = text.encode('utf-8') 
                    metadata = json.loads( textUtf8) 
                except UnicodeDecodeError as myErr2:
                    logging.warning( ' '.join( [  "Gir opp å fikse tegnsett-problem:", fname, str(myErr2) ] ) ) 

            except OSError as myErr: 
                logging.warning( ' '.join( [  "Kan ikke lese inn JSON-fil", fname, str(myErr) ] ) ) 
                
            if metadata: 
                
                feltmappe = metadata['exif_mappenavn'].split('/')[-1] 
                strekningsmappe = os.path.join( metadata['mappenavn'], feltmappe) 
                
                # Legger til strekning hvis den ikke finnes i oversikt
                if strekningsmappe not in oversikt.keys(): 
                    oversikt[strekningsmappe] = { 'strekningsnavn' : strekningsmappe, 
                                                    'filer' : [] }
                    count = 0 # Debug, mindre datasett 
                                                    
                metadata['temp_gammelfilnavn'] = os.path.join( mappe, 
                                                    os.path.splitext( bilde)[0] )
                
                # logging.info( 'DEBUG: Gammelt filnavn: ' + metadata['temp_gammelfilnavn'] ) 
                # tmp = a

                count += 1      # Debug, mindre datasett
                if count <= 10: # Debug, mindre datasett
                    pass
                
                if 'vegreferansedato' in metadata.keys() and sjekkdato( stabildato, metadata['vegreferansedato']):
                    count_ferskvare += 1
                    metadata2 = deepcopy( metadata )
                    metadata2['ny_visveginfosuksess'] = True
                    oversikt[strekningsmappe]['filer'].append( metadata2 )
                else: 
                    # Oppdaterer vegreferanseverdier:
                    try: 
                        metadata2 = deepcopy( visveginfo_veglenkeoppslag( metadata, filnavn=fname, proxies=proxies) ) 
                    except Exception:
                        count_fatalt += 1 
                        logging.error( 'Fatal feil i visveginfo_veglenkeoppslag for fil' + fname)
                        logging.exception('Stack trace for fatal feil' )
                    else: 
                        oversikt[strekningsmappe]['filer'].append( metadata2) 
                
            else: 
                logging.warning( 'Måtte gi opp lesing av fil ' + fname ) 

    if count_fatalt > 0:
        logging.error( 'Faltal feil for ' + str(count_fatalt) + 'filer' ) 
        
    if count_ferskvare == 0: 
        logging.info( "Ingen vegbilder hadde vegreferansedato nyere enn " + stabildato ) 
    else:
        logging.info( str( count_ferskvare ) + " vegbilder hadde vegreferansedato nyere enn " + stabildato )
    
    logging.info( str( datetime.now()))
    dt = datetime.now() - t0
    logging.info( " ".join( [ "Tidsforbruk", str(dt.total_seconds()), 'sekunder' ] ))     
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
    logdir = 'loggfiler_flyttvegbilder' 
    logname='flyttvegbilder_' 
    proxies = { 'http' : 'proxy.vegvesen.no:8080', 'https' : 'proxy.vegvesen.no:8080'  }
    eldstedato = '1949-31-12'
    stabildato = eldstedato


    # flyttfiler(gammeltdir='vegbilder/testbilder_prosessert/orginal_stedfesting', 
                # nyttdir='vegbilder/testbilder_prosessert/ny_stedfesting')


    versjoninfo = "Flyttvegbilder Versjon 3.1 den 18. Juni 2019 kl 0941"
    print( versjoninfo ) 
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
                
            if 'logdir' in oppsett.keys():
                logdir = oppsett['logdir']

            if 'logname' in oppsett.keys():
                logname = oppsett['logname']
                
            if 'proxies' in oppsett.keys():
                proxies = oppsett['proxies']            

            if 'stabildato' in oppsett.keys():
                stabildato = oppsett['stabildato']            

                
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
        duallog.duallogSetup( logdir=logdir, logname=logname) 
        logging.info( versjoninfo ) 
        if proxies: 
            logging.info( 'Bruker proxy for http-kall: ' + str( proxies )  ) 
        else: 
            logging.info( 'Bruker IKKE proxy for http kall' ) 
            
        if stabildato != eldstedato: 
            logging.info( "Sjekker kun bilder med vegreferansedato eldre enn " + stabildato ) 
            
        if not isinstance( gammeltdir, list): 
            gammeltdir = [ gammeltdir ] 
            
        for idx, enmappe in enumerate( gammeltdir): 
            logging.info( ' '.join( [ "Prosesserer mappe", str(idx+1), 'av', str(len(gammeltdir)) ] ) ) 
            flyttfiler( gammeltdir=enmappe, nyttdir=nyttdir, proxies=proxies, stabildato=stabildato) 
        logging.info( "FERDIG" + versjoninfo ) 
    