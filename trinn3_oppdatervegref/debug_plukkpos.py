import json
from pathlib import Path
import pdb
import re

import flyttvegbilder

def wkt2posarray( wktpoint ): 
    """
    Omsetter WKT-streng for punkt => array som geojson liker
    """
    if 'POINT' in wktpoint.upper():
        tmp = wktpoint.split( '(')
        tmpB = re.sub( '\)', '', tmp[1])
        tmp2 = tmpB.split( )

        # coordinates = [-112.0372, 46.608058]
        #                 lon, lat dvs X, y
        return [ float( tmp2[0]), float( tmp2[1]) ]


    else: 
        print( 'Ikke WKT punkt', wktpoint)

def json2geojson( inputdir, outputgjson='ev134NYstedfesting'):
    """
    Leser alle json  - filer i en makke og lager to geojson-filer,
    en med senterlinjeposisjon og en med bildeposisjon 
    """

    # filer = flyttvegbilder.findfiles( 'fy*hp*m*.json', where=inputdir) 
    filer = []


    senterlinje = { "type": "FeatureCollection","features": [] }
    gps = { "type": "FeatureCollection","features": [] }

    # for eifil in filer: 
    count = 0 
    for path in Path(inputdir).rglob('fy*hp*m*.json'):

        count += 1 

        filnavn =  '/'.join( [ str( path.parent), path.name] )
        filer.append( filnavn )

        meta = flyttvegbilder.lesjsonfil( filnavn )
        (meta, raretegn) = flyttvegbilder.fiksutf8( meta) 

        meta.pop( 'exif_imageproperties')
        # if count <= 3: 
        gps['features'].append( {  "type": "Feature",
                                    "geometry": {
                                        "type": "Point",
                                        "coordinates": wkt2posarray( meta['exif_gpsposisjon'])
                                    },
                                    "properties": meta
                                    } )


        senterlinje['features'].append( {  "type": "Feature",
                                    "geometry": {
                                        "type": "Point",
                                        "coordinates": wkt2posarray( meta['senterlinjeposisjon'])
                                    },
                                    "properties": meta
                                    } )

    if len(filer ) > 0: 
        print( 'fant', len(filer), 'json filer')
        flyttvegbilder.skrivjsonfil( outputgjson + '_gps.geojson', gps )
        flyttvegbilder.skrivjsonfil( outputgjson + '_senter.geojson', senterlinje )
    else: 
        print( 'Fant ingen json-filer i mappe', inputdir)