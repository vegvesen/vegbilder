import logging 

from formatsjekk import kvalitetskontroll, finnfiltype, filnavndata
from flyttvegbilder_v54 import lesjsonfil
import duallog

duallog.duallogSetup( logdir='loggdir', logname='loggfil')

filer = finnfiltype( 'testdata/allefiler_flatt', '.json' )

for filnavn in filer:
    jsondata = lesjsonfil( filnavn)
    try:
        kvalitetskontroll( jsondata, filnavn)
    except AssertionError as myErr:
        logging.warning( myErr)


# sjekker funksjonen filnavndata 
filnavn = 'Fy06_Ev134_hp04_f1_m00031'
filnavnsvar = { 'fylke': 6,
                'vegkat': 'E',
                'vegstat': 'v',
                'vegnr': 134,
                'hp': 4,
                'felt': 1,
                'meter': 31}
try: 
    assert filnavndata( filnavn) == filnavnsvar, 'funksjon filnavndata gir feil svar' 
    assert filnavndata( filnavn + '.json') == filnavnsvar, 'funksjon filnavndata gir feil svar ved filetternavn .json' 
    assert filnavndata( filnavn + '.jpg') == filnavnsvar, 'funksjon filnavndata gir feil svar ved filetternavn .jpg' 
    assert filnavndata( '\\mappe\\mappe\\' + filnavn) == filnavnsvar, 'funksjon filnavnsvar feiler ved backslash i filnavn' 
    assert filnavndata( '//asdf/mappe/mappe/' + filnavn) == filnavnsvar, 'funksjon filnavnsvar feiler ved slash i filnavn' 
    assert filnavndata( '//asdf\\mappe/mappe\\mappe/mappe\\mappe/' + filnavn) == filnavnsvar, 'filnavnsvar feiler ved backslash-slash kombinasjon' 
    assert filnavndata( '//asdf\\mappe/mappe\\mappe/mappe\\mappe\\' + filnavn) == filnavnsvar, 'filnavnsvar feiler ved slash-backslash kombinasjon' 
except AssertionError as myErr:
    logging.warning( myErr)
else: 
    logging.info( 'Funksjon filnavnsvar passerer test')

