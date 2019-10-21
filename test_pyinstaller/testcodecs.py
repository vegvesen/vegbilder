import json 
import re
import os

def lesexifstrekning( kodek ): 
    liste = [ 'F1_2018_08_21/Fy08_Fv402_hp01_f1_m00044.json' ]  

#            'C:\DATA\leveranser\vegbilder\kode\vegbilder\testbilder_prosessert\orginal_stedfesting\06\2018\06_Ev134\Hp05_Damåsen\F1_2018_06_21'


    for filnavn in liste: 

        with open( filnavn, encoding=kodek) as f: 
            metadata = json.load( f) 
            
        tekst1 = metadata['exif_strekningsnavn'] 
        print( tekst1 ) 
        data3 = re.sub( r'ÃƒËœ', 'Æ', tekst1 ) 
        print( data3) 
        
        
        
        allowedchars = r'[^0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZÆØÅæøå/-._]'
        disallow = r'[0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZÆØÅæøå/\-._]'
        data = re.sub( disallow, '_',  tekst1 ) 
        print( data) 
        data = re.sub( r'_{1,}', '_', data)
        print( data) 
        # print( re.sub( r'[^0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ]', '_', metadata['exif_strekningsnavn'] )) 
        # print( re.sub( r'[^LKEDALEN]', '_',  metadata['exif_strekningsnavn'] ) ) 
        
        # delchars = ''.join(c for c in map(chr, range(256)) if c not in (string.punctuation + string.digits + string.letters) )
    
    
    # return metadata['exif_strekningsnavn' ] 


    