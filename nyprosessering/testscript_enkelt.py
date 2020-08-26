import logging 

from formatsjekk import kvalitetskontroll, finnfiltype
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