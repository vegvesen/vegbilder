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
import glob 


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
        logging.debug( r.url + ' status kode: ' + str( r.status_code ))
        svartekst = r.text
        
        # Tom returverdi = veglenkeposisjon finnes ikke. 
        # XML-dokument med <RoadReference ... = godkjent
        # Alt anna = feilmelding fra server (Unavailable etc...) 
        if 'RoadReference' in svartekst or len( svartekst) == 0: 
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
        tekstrespons = anropvisveginfo( url, params, filnavn, proxies=proxies )
        if 'RoadPointReference' in tekstrespons: 
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
    
    
def sjekkretningsendringer( metadata, strekningsnavn, proxies='' ): 
    """
    Sjekker endringer i metreringsretning for ett metadata-element ved hjelp av visveginfo-oppslag
    Først på bildedato, dernest på dato for den nye vegreferansen (= dagens verdi i alle scenarier jeg kan komme på) 
    """
    
    if 'filnavn' in metadata.keys():
        filnavn = '/'.join( [ strekningsnavn, metadata['filnavn'] ]) 
    else: 
        filnavn = '/'.join( [ strekningsnavn, metadata['exif_filnavn'] ]) 
        logging.warning( 'Ikke noe filnavn-element i JSON-fil ' + strekningsnavn + ' gammelt filnavn ' + filnavn ) 
  
    snuretning = 'Ikke snudd'    
    
    if metadata['ny_visveginfosuksess']: 
        gammalretning = metreringsretning( metadata['exif_fylke'], metadata['exif_vegkat'], metadata['exif_vegstat'], 
                                            metadata['exif_vegnr'], metadata['exif_hp'], metadata['exif_meter'], 
                                            metadata['exif_dato'], filnavn, proxies=proxies) 
        
        nyretning = metreringsretning( metadata['fylke'], metadata['vegkat'], metadata['vegstat'], 
                                            metadata['vegnr'], metadata['hp'], metadata['meter'], 
                                            metadata['vegreferansedato'], filnavn, proxies=proxies) 

        if gammalretning and nyretning and gammalretning != nyretning: 
            snuretning = 'snudd' 
    else: 
        logging.warning( ' '.join( [ "Sjekkretning: Irrelevant å sjekke retning på historisk bilde", 
                                    filnavn, metadata['datafangstuuid'] ] ) )         
        
        
    return snuretning 
        
        
    
def metreringsretning( fylke, vegkat, vegstat, vegnr, hp, meter, dato, filnavn, proxies=''): 

    pos0 = pos2 = minpos = retning = motsatt = None 
    url = 'http://visveginfo-static.opentns.org/RoadInfoService3d/GetRoadReferenceForReference' 

    fylke = str(int( fylke)).zfill(2) 
    kommune = '00' 
    vegnr = str( int( vegnr)).zfill(5)
    hp = str( int( hp) ).zfill(3)
    meter1 = str(round( float( meter ))).zfill(5) 
    
    vegref1 = fylke + kommune + vegkat + vegstat + vegnr + hp + meter1
    params = { 'roadReference' : vegref1, 'ViewDate' : dato, 'topologyLevel' : 'Overview' } 
    
    svartekst = anropvisveginfo( url, params, filnavn, proxies = proxies) 
    if '<RoadReference' in svartekst: 
        vvidata = xmltodict.parse( svartekst) 
        minpos = float( vvidata['ArrayOfRoadReference']['RoadReference']['Measure'] ) 
    else: 
        logging.warning( "Sjekk metreringsretning for enkelt bilde: Vegreferanseoppslag FEILER: " + filnavn + " " + str( params )  ) 
        return None 


    # En meter bakover
    if int( meter1) >= 1: 
        params['roadReference'] = fylke + kommune + vegkat + vegstat + vegnr + hp + str( int( meter1)-1 ).zfill(5) 
        svar0 = anropvisveginfo( url, params, filnavn, proxies = proxies ) 
        if '<RoadReference' in svar0: 
            vvidata0 = xmltodict.parse( svar0) 
            pos0 = float( vvidata0['ArrayOfRoadReference']['RoadReference']['Measure'] ) 
        
    # En meter framover 
    params['roadReference'] = fylke + kommune + vegkat + vegstat + vegnr + hp + str( int( meter1)+1 ).zfill(5) 
    svar2 = anropvisveginfo( url, params, filnavn, proxies = proxies ) 
    if '<RoadReference' in svar2: 
        vvidata2 = xmltodict.parse( svar2) 
        pos2 = float( vvidata2['ArrayOfRoadReference']['RoadReference']['Measure'] ) 

    
    # Antar at metrering følger lenka, for så å evt bli motbevist
    retning = 'lenkeretning' 
    if pos0 and pos0 > minpos: 
        retning = 'motsatt' 
        
    if pos2 and pos2 < minpos: 
        retning = 'motsatt' 
        
    # Dårlig integritet i data... 
    if pos0 and pos2 and pos0 > pos2 and retning != 'motsatt': 
        logging.warning( ' '.join( [ 'FEIL i metreringsverdier', filnavn  ] ))
    
    if not pos0 and not pos2: 
        logging.warning( ' '.join( [ 'Klarte ikke sjekke metreringsretning:', filnavn, 
                                    'Hverken forrige eller neste meter-tall ga mening'] ))
    
    return retning


    
    
    

def sjekkretning(strekningsdata, proxies=''): 
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
    
    # Ekstra sjekk hvis det kun er ett bilde i den nye mappenavn
    if antObjekt == 1: 
        logging.info( "Kun ett bilde i " + strekningsdata['strekningsnavn'] + ", kjører ekstra sjekk for gammel vs ny metreringsretning" ) 
        retning = sjekkretningsendringer( strekningsdata['filer'][0], strekningsdata['strekningsnavn'], proxies=proxies ) 
        
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

        # Hardkoder inn feilhåndtering hvis feltkode mangler helt (f.eks på gangstier) 
        manglerfelt = False
        if not isinstance( metadata['feltoversikt'], str): 
            metadata['feltoversikt'] = "1#2"
            manglerfelt = True
 
        if not isinstance( metadata['feltoversikt_perbildedato'], str): 
            metadata['feltoversikt_perbildedato'] = '1#2' 
            manglerfelt = True
            
        if manglerfelt: 
            logging.warning( 'Ingen feltinformasjon: ' + metadata["temp_gammelfilnavn"] )

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
            tmp_muligefelt_string = '#'.join( muligeFelt ) 
            logging.warning( ' '.join( [ "Klarte ikke snu feltretning", metadata['exif_feltkode'], 
                                        'til noe i', tmp_muligefelt_string,  bildenavn ] ) ) 
            nyFeltKode = metadata['feltoversikt']
        
        metadata['feltkode'] = nyFeltKode
        
    return metadata
        
def plukkstedsnavn( hpnavn, ukjent='', fjernraretegn=True): 
    """
    Plukker ut stedsnavn-komponenten av navnet hp05_Granåsen eller hp50_X_Ditt_Fv309_datt
    
    Nøkkelord ukjent='' kan detaljstyre hva som er returverdi hvis vi ikke har noe stedsnavn 
    """ 
    junk = ''
   
    stedsnavn = '_'.join( hpnavn.split( '_')[1:] ) 
     
    if not stedsnavn: 
        stedsnavn = ukjent
    if fjernraretegn: 
        (stedsnavn, raretegn) = slettraretegn( stedsnavn) 
    else: 
        (junk, raretegn) = slettraretegn( stedsnavn)
        
     
    return (stedsnavn, raretegn)
    
def slettraretegn( tekst): 
    """
    Fjerner rester av tegnsett-rot fra tekst
    """

    
    tekst = re.sub( r'ÃƒÆ’Ã¢â‚¬Â¦', 'Å', tekst ) 
    tekst = re.sub( r'Ã¥', 'å', tekst ) 
    tekst = re.sub( r'ÃƒËœ', 'Æ', tekst ) 
    
    allowedchars = '[^0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZÆØÅæøå._-]'
    disallow     =  '[0123456789abcdefghijklmnopqrstuvwxyzÆØÅæøåABCDEFGHIJKLMNOPQRSTUVWXYZ._-]'
    merkelig = re.sub( disallow, '', tekst ) 
    tekst = re.sub( allowedchars, '_', tekst) 
    tekst = re.sub( ' ', '_', tekst) 
    tekst = re.sub( r'_{1,}', '_', tekst) 
    
    return (tekst, merkelig) 

def lag_strekningsnavn( metadata, fjernraretegn=True): 
    """
    Komponerer nytt strekningsnavn og filnavn, og returnerer tuple (strekningsnavn, filnavn, stedsnavn, raretegn) 
    
    Modifiserer IKKE metadata
    """ 
    raretegn = ''
    
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
        (stedsnavn, raretegn) = plukkstedsnavn( hpbit, fjernraretegn=fjernraretegn ) 
        
        

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
        stedsnavn = ''
        
        if 'feltkode' in metadata.keys(): 
            felt = 'F' + str( metadata['feltkode'] )
        else: 
            felt = 'F' + str( metadata['exif_feltkode'] ) 
        dato =  '_'.join( metadata['exif_dato'].split('-')[0:3] )   
        
        nystrekning = os.path.join( nystrekning, '_'.join( [felt, dato] ) )
        nyttfilnavn = '_'.join( [   'Fy' + vegnavn, hptekst, felt, 'm' + str( round( metadata['meter'] )).zfill(5) ] )
    
    else: 
        # Returnerer det gamle navnet på streking og filnavn
        # men overstyrer fylke og aar - delen av navnet 
        # fordi vi av og til bruker "siste" - mappe 
        nyttfilnavn = re.sub( '.jpg', '', metadata['exif_filnavn'] ) 
        (rot, vegnavn, hpnavn, felt, filnavn) = mypathsplit( metadata['temp_gammelfilnavn'], 4)
        
        aar = metadata['exif_dato'][0:4] 
        if 'fylke' in metadata.keys() and ( isinstance( metadata['fylke'], str) or isinstance( metadata['fylke'], int) ): 
            fylke = str( metadata['fylke']).zfill(2)
        else: 
            fylke = str( metadata['exif_fylke'] ).zfill(2)
            
        # fjerner eventuelle stedsnavn 
        hpnavn = hpnavn.split('_')[0] 
        
        hpnavn = 'HISTORISK-' + hpnavn 
        
        # Knar på vegnavn for å sikre at vi har formen 07_Eg18, ikke 07_EG018
        vegnavn = knavegnavn(metadata, vegnavn, fylke) 
        
        nystrekning = '/'.join( [ fylke, aar, vegnavn, hpnavn, felt ] ) 
                
        stedsnavn = '' # Stedsnavn står allerede i gammelt filnavn, trenger ikke føye det til 2 ganger
    
    nystrekning = re.sub( '\\\\', '/', nystrekning) 
     
    return (nystrekning, nyttfilnavn, stedsnavn, raretegn) 

def knavegnavn( metadata, vegnavn, fylke): 
    vegkat = metadata['exif_vegkat'].upper()
    vegstat = metadata['exif_vegstat'].lower()
    if vegkat in ['E', 'R']: 
        mysep = '_'
    else: 
        mysep = '-'
        
    vegnavn = str(int(fylke)).zfill(2) + mysep + vegkat + vegstat + str(int( metadata['exif_vegnr'] ) )

    return vegnavn 
    
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
                nyttdir='../bilder/testflytting/test1_Ev134', proxies='', 
                stabildato='1949-31-12', fjernraretegn=True ): 
    
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
    mineraretegn = set() 
    gammelcount = 0 
    for strekning in gammelt.keys():
        for fil in gammelt[strekning]['filer']: 
            
            gammelcount += 1
            if fil['ny_visveginfosuksess']: 
                (nytt_strekningsnavn, junk, stedsnavn, raretegn)  = lag_strekningsnavn( fil, fjernraretegn=fjernraretegn) 
                
            else: # Mangler stefesting = historiske data
                (rot, hpmappenavn, feltmappenavn) = mypathsplit( strekning, 2) 
                (stedsnavn, raretegn) = plukkstedsnavn( hpmappenavn, fjernraretegn=fjernraretegn )  
                nytt_strekningsnavn = '/'.join( [ rot, 'HISTORISK-'+hpmappenavn, feltmappenavn ] )
                # pdb.set_trace()

            
            if raretegn and raretegn not in mineraretegn: 
                mineraretegn.add( raretegn) 
                logging.error( 'Fant snåle tegn: ' + raretegn + ' i mappe ' + strekning + ' exif mappenavn: ' + fil['exif_mappenavn'] ) 
             
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
        snuretning = sjekkretning( tempnytt[strekning], proxies=proxies ) 
        # logging.info( strekning + " " +  snuretning) 
        
        # Tar med oss info om retningen skal snus og komponerer nye streknings (mappe) og filnavn: 
        for fil in tempnytt[strekning]['filer']: 
            tempcount += 1
            meta = deepcopy( sjekkfelt( fil, snuretning=snuretning) )
            (nystrekning, nyttfilnavn, stedsnavn, raretegn) = lag_strekningsnavn( meta, fjernraretegn=fjernraretegn) 
                        
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
                    
                # Sammenligner gammelt og nytt strekningsnavn. Må  dekomponere for å sikre oss mot / versus \ - problematikk
                gamlebiter  = mypathsplit( gmltStrNavn, 3) 
                nyebiter    = mypathsplit( nystrekning, 3) 
                
                if '/'.join( gamlebiter[1:]) ==  '/'.join( nyebiter[1:] ): 
                    infostr = 'Mappenavn uendret'
                else: 
                    infostr = 'Mappenavn ENDRET'
                
                logging.info( " ".join( [ infostr, gmltStrNavn, snuindikator, '=>', nystrekning ] ) ) 

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
            
            # Kopierer bildefil
            kopierfil( gammelfil + '.jpg', skrivnyfil + '.jpg' ) 
            
            # Kopierer webp-fil -- hvis den finnes 
            # Prøver å kontroller for nettverksbrudd ved samtidig å sjekke om 
            # bildefilen finnes (det er ikke alltid vi har webp-fil) 
            # Hvis vi IKKE finner bildefilen har vi nettverksbrudd og 
            # prøver å flytte webp-filen. 
            # Statistikken count_manglerwebpfil vil bli 1 element for lite hvis vi 
            # har spesialtilfellet at webp - fila mangler og vi har nettverksbrudd 
            # akkurat i det bildePath.exists()-sjekken foretas. 
            # Det er imidlertid andre skriveoperasjoner som tar MYE mer tid enn dette, 
            # så sjangsen for at akkurat denne operasjonen er det som påtreffer nettverksbrudd
            # er ganske liten... 
            webpPath =  Path( gammelfil + '.webp' ) 
            bildePath = Path( gammelfil + '.jpg' ) 
            
            if webpPath.exists() or not bildePath.exists(): 
                kopierfil( gammelfil + '.webp', skrivnyfil + '.webp' ) 
            else: 
                count_manglerwebpfil += 1
            
            # Flytter exif-XML helt nederst i strukturen 
            exif_imageproperties = meta.pop( 'exif_imageproperties')
            meta['exif_imageproperties'] = exif_imageproperties
            
            # Fjerner flagget 
            junk = meta.pop( 'ny_visveginfosuksess' )

            # logging.info( "Venter litt, så du kan simulere nettverksbrudd") 
            # time.sleep(5)
                
            skrivjsonfil( skrivnyfil + '.json', meta) 

    if count_manglerwebpfil > 0: 
        logging.warning( "Mangler " + str(count_manglerwebpfil) + " webp-filer"  ) 
    logging.info( " ".join( [ "Antall filnavn på ulike steg:", str( len( tempfilnavn)), str( len(ferdigfilnavn)) ]) )
    dt = datetime.now() - t0
    logging.info( " ".join( [ "Tidsforbruk denne mappen:", str( dt.total_seconds()), 'sekunder' ])) 

def kopierfil( gammelfil, nyfil, ventetid=15): 
    """
    Filkopiering som er tolererer nettverksfeil og tar en pause før vi prøver på ny (inntil 4 ganger)
    """ 
    
    count = 0
    sovetid = 0 
    anropeMer = True 
    maxTries = 4
    while count < maxTries and anropeMer: 
        count += 1

        try: 
            copyfile( gammelfil, nyfil )  
        except (OSError, FileNotFoundError) as myErr: 
            sovetid = sovetid + count * ventetid
            
            if count < maxTries: 
                logging.error( "Kopiering av fil FEILET " + gammelfil + " prøver på ny om " + str( sovetid) + " sekunder" ) 
                time.sleep( sovetid) 
            else: 
                logging.error( "Skriving til fil FEILET " + gammelfil + ", gir opp og går videre"  ) 
                logging.error( str(myErr)) 
 
        else: 
            anropeMer = False
    

def skrivjsonfil( filnavn, data, ventetid=15): 
    """
    Skriver dict til json-fil. Tolererer nettverksfeil og tar en pause før vi prøver på ny (inntil 4 ganger)
    """ 
    
    count = 0
    sovetid = 0 
    anropeMer = True 
    maxTries = 4
    while count < maxTries and anropeMer: 
        count += 1

        try: 
            with open( filnavn, 'w', encoding='utf-8') as fw: 
                json.dump( data, fw, ensure_ascii=False, indent=4) 
        except OSError as myErr: 
            sovetid = sovetid + count * ventetid
            
            if count < maxTries: 
                logging.error( "Skriving til fil FEILET " + filnavn + " prøver på ny om " + str( sovetid) + " sekunder" ) 
                time.sleep( sovetid) 
            else: 
                logging.error( "Skriving til fil FEILET " + filnavn + ", gir opp og går videre"  ) 
                logging.error( str(myErr)) 
 
        else: 
            anropeMer = False

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


def lesjsonfil( filnavn, ventetid=15): 
    """
    Åpner og leser JSON-fil. Tolererer nettverksfeil og tar en pause før vi prøver på ny (inntil 4 ganger
    """ 
    
    meta = None 
    count = 0
    sovetid = 0 
    anropeMer = True 
    maxTries = 4
    while count < maxTries and anropeMer: 
        count += 1
    
        try: 
            with open( filnavn ) as f: 
                meta = json.load(f)    
            
        except UnicodeDecodeError as myErr: 
            logging.warning( ' '.join( [  "Tegnsett-problem, prøver å fikse:", fname, str(myErr) ] ) ) 
        
            try: 
                with open( fname, encoding='latin-1') as f: 
                    text = f.read()
                    textUtf8 = text.encode('utf-8') 
                    meta = json.loads( textUtf8) 
            except UnicodeDecodeError as myErr2:
                logging.warning( ' '.join( [  "Gir opp å fikse tegnsett-problem:", fname, str(myErr2) ] ) ) 
                meta = None
                anropeMer = False
        
        except (json.decoder.JSONDecodeError) as myErr: 
            logging.error( ' '.join( ["Feil i JSON-fil, ignorerer:", filnavn, str(myErr ) ] ) )
            meta = None         
        
        except OSError as myErr: 
            sovetid = sovetid + count * ventetid
            
            if count < maxTries: 
                logging.error( "Lesing av JSON-fil feilet, " + filnavn + " prøver på ny om " + str( sovetid) + " sekunder" ) 
                time.sleep( sovetid) 
            else: 
                logging.error( "Lesing av JSON-fil FEILET " + filnavn + ", gir opp og går videre"   ) 
                logging.error( str( myErr) ) 
                meta = None

 
        else: 
            anropeMer = False
        
     

    return meta 


def utledMappenavn( mappe ):
    mapper = splitpath( mappe, 6) 
    return '/'.join( mapper[-5:-1]) 

def splitpath( filnavn, recdybde ):
    """
    Deler filnavn opp i liste med undermapper + filnavn (siste element i listen)
    """
    deling1 = os.path.split( filnavn )
    recdybde -= 1

    if deling1[0] == '/' or deling1[0] == '' or deling1[1] == '' or recdybde == 0: 
        mapper = [ filnavn ]
    else: 
        mapper = splitpath( deling1[0], recdybde )
        mapper.append( deling1[1])

    return mapper

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
    count_raretegn = 0

    t0 = datetime.now()
    logging.info(str( t0) )
    # Finner alle mapper med bilder: 
    folders = set(folder for folder, subfolders, files in os.walk(datadir) for file_ in files if os.path.splitext(file_)[1].lower() == '.jpg')
    
    for mappe in folders: 
        logging.info( "leter i mappe " + mappe) 
        jsonfiler = findfiles( 'fy*hp*m*.json', where=mappe) 
        metadata = None
        count = 0 # Debug, mindre datasett
        for ii, bilde in enumerate(jsonfiler): 
            fname = os.path.join( mappe, bilde)

            if ii > 0 and ii % 1000 == 0: 
                logging.info( 'i mappe ' + mappe + ', leser bilde ' + str(ii) + ' av ' + str( len( jsonfiler )) + ' ' + fname )
            
            metadata  = lesjsonfil( fname) 
                                
            if metadata: 

                (metadata, raretegn) = fiksutf8( metadata) 
                # if raretegn: 
                    # logging.info( 'Rare tegn funnet i fil' + fname ) 
                    # count_raretegn += 1 

                # Mangler vi mappenavn? Snålt, fiks det! 
                if not 'mappenavn' in metadata.keys():
                    metadata['mappenavn'] = utledMappenavn( mappe )
                    logging.warning( 'Mappenavn mangler i json-fil, opprettet dynamisk ' + fname) 

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
    

def fiksutf8( meta): 

    kortalfabet = 'abcdefghijklmnopqrstuvwxyz'
    alfabet = kortalfabet + 'æøå'
    tegn  = '0123456789.,:;-_ *+/++<>\\()#?=' 
    godkjent = tegn + alfabet + alfabet.upper()
    raretegn = False

    tulletegn = set( ) 
    # Prøver å fikse tegnsett 
    if meta and isinstance( meta, dict): 
        old = deepcopy( meta) 
        for key, value in old.items():
            if isinstance( value, str): 
                nystr = ''
                rart = False 
                for bokstav in value: 
                    if bokstav in godkjent: 
                        nystr += bokstav
                    else:
                       tulletegn.add( bokstav)  
                       rart = True 
                       
                if rart: 
                    nystr = nystr.replace( 'Æ', '_')
                    nystr = nystr.replace( 'Å', '_') 
                    
                    nystr = re.sub('_{2,}', '_', nystr )
                    
                    raretegn = True 
                meta[key] = nystr

    # if len(tulletegn) > 0: 
        # print( "Tulletegn: ", tulletegn) 
        
    return meta, raretegn


def finnundermapper( enmappe, huggMappeTre=None, **kwargs):

    if huggMappeTre: 
    
        logging.info( "finner undermapper til: " +  enmappe ) 
        huggMappeTre = huggMappeTre - 1
        
        folders = [f for f in glob.glob(enmappe + "/*/")]
        for undermappe in folders: 
            logging.info( "fant undermappe: " + undermappe) 
            finnundermapper( undermappe, **kwargs )

    else: 
        print( "Starter proseessering av undermappe: " + enmappe) 
    
        flyttfiler( gammeltdir=enmappe, **kwargs)

if __name__ == "__main__": 

    nyttdir = None
    gammeltdir = None
    logdir = 'loggfiler_flyttvegbilder' 
    logname='flyttvegbilder_' 
    proxies = { 'http' : 'proxy.vegvesen.no:8080', 'https' : 'proxy.vegvesen.no:8080'  }
    eldstedato = '1949-31-12'
    stabildato = eldstedato
    fjernraretegn = True
    huggMappeTre = False


    # flyttfiler(gammeltdir='vegbilder/testbilder_prosessert/orginal_stedfesting', 
                # nyttdir='vegbilder/testbilder_prosessert/ny_stedfesting')


    versjoninfo = "Flyttvegbilder Versjon 5.0 den 3. februar 2020"
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

            if 'fjernraretegn' in oppsett.keys():
                fjernraretegn = oppsett['fjernraretegn']
            
            if 'huggMappeTre' in oppsett.keys():
                huggMappeTre = oppsett['huggMappeTre']
                
        else: 
            gammeltdir = sys.argv[1]
            
            
        if len( sys.argv) > 2: 
            
            if nyttdir: 
                print( "Navn på ny mappe angitt både i oppsettfil og på kommandolinje") 
                print( "Jeg stoler mest på kommandolinja, og lar den overstyre") 
                
            nyttdir = sys.argv[2] 
            
    if not gammeltdir or not nyttdir: 
        print( "STOPP - kan ikke prosessere uten at du angir mappenavn for der bildene finnes og dit oppdatert stedfesting kan skrives") 
        if not gammeltdir: 
            print( "Mangler parameter orginalmappe") 
        if not nyttdir: 
            print( "Mangler parameter nymappe" ) 
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
            
        t0 = datetime.now()
        for idx, enmappe in enumerate( gammeltdir): 
        
        
        
            logging.info( ' '.join( [ "Prosesserer mappe", str(idx+1), 'av', str(len(gammeltdir)) ] ) ) 
            
            if huggMappeTre:
                if huggMappeTre == 1: 
                    logging.info( 'huggMappeTre: Vil ta hver undermappe i katalogen(e) "datadir" for seg' )
                else:
                    logging.info( 'huggMappeTre: Vil ta under-underkataloger for ' + str( huggMappeTre) + 
                                    'nivåer nedover relativt til "datadir"-katalogen(e) for seg' ) 
            else: 
                logging.info( "Ingen huggMappeTre - parameter") 

            # flyttfiler( gammeltdir=enmappe, nyttdir=nyttdir, proxies=proxies, stabildato=stabildato, fjernraretegn=fjernraretegn) 
            finnundermapper( enmappe, huggMappeTre=huggMappeTre, proxies=proxies, 
                            nyttdir=nyttdir, stabildato=stabildato, fjernraretegn=fjernraretegn )              
            
            
        dt = datetime.now() - t0
        logging.info( " ".join( [ "Tidsforbruk TOTALT: ", str( dt.total_seconds()), 'sekunder' ])) 
        logging.info( "FERDIG" + versjoninfo ) 
    