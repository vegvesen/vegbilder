"""

"""

import json 
import os
from copy import deepcopy
from datetime import datetime
import logging 
import sys
import duallog
import fnmatch
import glob 
from pathlib import Path
import re 

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

def fiksmetadata( filnavn:str, inputdir:str, outputdir:str ): 

    with open( filnavn, encoding='utf-8' ) as f: 
        meta = json.load( f )

    meta = fikstagger( meta, filnavn )

    # Må plassere ny undermappe riktig i outputdir-strukturen
    # Finner først det som er felles
    fellesRot = '' 
    for ix, x in enumerate( filnavn ):
        if len( inputdir ) >= ix and inputdir[0:ix] == filnavn[0:ix]:
            fellesRot = filnavn[0:ix]

    filnavnRelativtFellesRot = filnavn[len( fellesRot):]
    if filnavnRelativtFellesRot[0] != '/': 
        filnavnRelativtFellesRot = '/' + filnavnRelativtFellesRot
    nyttFilnavn = outputdir + filnavnRelativtFellesRot

    nymappe = Path( os.path.split( nyttFilnavn )[0] )
    nymappe.mkdir( parents=True, exist_ok=True )
    skrivjsonfil( nyttFilnavn, meta )

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

def fikstagger( meta:dict, filnavn:str): 
    """
    Retter opp taggene bildeid og exif_filnavn slik at de matcher 
    meterverdien til filnavnet

    Finner først meterverdi ut fra filnavnet. Sjekker at disse taggene 
    har rett filnavn-verdi, med identisk meterverdi som i filnavnet

    Hyler ut dersom det er avvik eller inkonsistens   
    """
    # Finner meterverdi fra filnavn
    meter = filnavn.split( '.' )[0].split( 'm' )[-1]

    # Sjekker bildeid - taggen, på formen "2014-05-14T14.13.34_Fy16_Fv001_hp01_m00299_Planar_1"
    biter = meta['bildeid'].split( '_' )
    nyebiter = []
    fantMeter = False
    gammelMeter = '' 
    endretMeter = False 
    for bit in biter: 
        if bit[0].lower() == 'm': 
            fantMeter = True 
            if bit[1:] != meter: 
                endretMeter = True
                gammelMeter = deepcopy( bit[1:] ) 
            nyebiter.append( 'm' + meter)
        else: 
            nyebiter.append( bit )
    if endretMeter: 
        meta['bildeid'] = '_'.join( nyebiter )
        logging.info( f"{filnavn} bildeid: endret meterverdi {gammelMeter} => {meter}: {meta['bildeid']} " )

    if not fantMeter: 
        logging.warning( f"Fant ikke meterverdi i bildeid-tagg {filnavn} {meta['bildeid']} " )

    # Sjekker exif_filnavn taggen, på formen "Fy16_Fv001_hp01_f1_m00299.jpg"
    biter = meta['exif_filnavn'].split( '_' )
    nyebiter = []
    fantMeter = False
    gammelMeter = '' 
    endretMeter = False 
    for bit in biter: 
        if bit[0].lower() == 'm': 
            fantMeter = True 
            meterbit = bit.split( '.')[0]
            if meterbit[1:] != meter: 
                endretMeter = True
                gammelMeter = deepcopy( meterbit[1:] ) 
            nyebiter.append( 'm' + meter + '.' + ''.join( bit.split('.')[1:] ) )
        else: 
            nyebiter.append( bit )
    if endretMeter: 
        meta['exif_filnavn'] = '_'.join( nyebiter )
        logging.info( f"{filnavn} exif_filnavn: endret meterverdi {gammelMeter} => {meter}: {meta['exif_filnavn']} " )


    if not fantMeter: 
        logging.warning( f"Fant ikke meterverdi i exif_filnavn-tagg {filnavn} {meta['exif_filnavn']} " )

    # from IPython import embed; embed()

    return meta 


def fiksfiler( datadir, inputdir, outputdir ): 
    
    jsonfiler = recursive_findfiles( 'fy*hp*m*.json', where=datadir) 
    antfiler = len( jsonfiler) 
    logging.info( 'Fant ' + str( antfiler) + ' json-filer i ' + datadir ) 
    
    for eifil in jsonfiler: 
        fiksmetadata( eifil, inputdir, outputdir ) 


def finnundermapper( enmappe:str, inputdir:str, outputdir:str, huggMappeTre=None, **kwargs):

    if huggMappeTre: 
    
        logging.info( "finner undermapper til: " +  enmappe ) 
        huggMappeTre = huggMappeTre - 1
        
        folders = [f for f in glob.glob(enmappe + "/*/")]
        for undermappe in folders: 
            logging.info( "fant undermappe: " + undermappe) 
            finnundermapper( undermappe, outputdir, **kwargs )

    else: 
        print( "Starter proseessering av undermappe: " + enmappe) 
    
        fiksfiler( enmappe, inputdir, outputdir, **kwargs)


if __name__ == '__main__': 

    inputdir = None 
    logdir = 'log'
    logname = 'fiksmetadata'
    t0 = datetime.now()
    versjonsinfo = "Fiksmetadata filinfo JSON Versjon 1.0 den 28.6.2022"
    print( versjonsinfo ) 
    
    if len( sys.argv) < 2: 
        oppsettfil = 'oppsettfil_fiksmetadata.json'
    else: 
        oppsettfil = sys.argv[1]

    print( f'Prøver å lese oppsett fra fil {oppsettfil} ')
    with open( oppsettfil ) as f: 
        oppsett = json.load( f )

    if 'inputdir' in oppsett.keys(): 
        inputdir = oppsett['inputdir']
        
    if 'outputdir' in oppsett.keys(): 
        outputdir = oppsett['outputdir']

    if 'logdir' in oppsett.keys():
        logdir = oppsett['logdir']

    if 'logname' in oppsett.keys():
        logname = oppsett['logname']
        
    if 'huggMappeTre' in oppsett.keys():
        huggMappeTre = oppsett['huggMappeTre'] 

    duallog.duallogSetup( logdir=logdir, logname=logname) 
    logging.info( versjonsinfo ) 

    if not inputdir: 
        logging.error( 'Påkrevd parameter "inputdir" ikke angitt, du må fortelle meg hvor JSON-filene ligger') 
    elif not outputdir: 
        logging.error( 'Påkrevd parameter "outputdir" ikke angitt, du må fortelle meg hvor JSON-filene skal kopieres til')         
    else: 
            
        if not isinstance( inputdir, list): 
            inputdir = [ inputdir ] 
            
        for idx, enmappe in enumerate( inputdir ): 

            logging.info( ' '.join( [ "Prosesserer mappe", str(idx+1), 'av', str(len(inputdir)), enmappe ] ) ) 
            
            if huggMappeTre:
                if huggMappeTre == 1: 
                    logging.info( 'huggMappeTre: Vil ta hver undermappe i katalogen(e) "inputdir" for seg' )
                else:
                    logging.info( 'huggMappeTre: Vil ta under-underkataloger for ' + str( huggMappeTre) + 
                                    ' nivåer nedover relativt til "inputdir"-katalogen(e) for seg' ) 
            else: 
                logging.info( "Ingen huggMappeTre - parameter") 

            finnundermapper( enmappe, enmappe, outputdir, huggMappeTre=huggMappeTre )   

    dt = datetime.now() - t0
    logging.info( " ".join( [ "Tidsforbruk TOTALT: ", str( dt.total_seconds()), 'sekunder' ])) 
    logging.info( "FERDIG " + versjonsinfo )     