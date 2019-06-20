import json 
import re

def lesexifstrekning( kodek ): 
    liste = [ '/mnt/c/DATA/leveranser/vegbilder/bilder/debug_08Fv402hp1/orginal_stedfesting/' + \
                '08/2018/08-Fv402/Hp01_LØKEDALEN_XF401/F1_2018_08_21/Fy08_Fv402_hp01_f1_m00044.json', 
                '/mnt/c/DATA/leveranser/vegbilder/kode/vegbilder/testbilder_prosessert/orginal_stedfesting/06/2018/06_Ev134/Hp05_Damåsen/F1_2018_06_21/Fy06_Ev134_hp05_f1_m03212.json' ]

#            'C:\DATA\leveranser\vegbilder\kode\vegbilder\testbilder_prosessert\orginal_stedfesting\06\2018\06_Ev134\Hp05_Damåsen\F1_2018_06_21'


    for filnavn in liste: 

        with open( filnavn, encoding=kodek) as f: 
            metadata = json.load( f) 
            
        
        print( metadata['exif_strekningsnavn'] ) 
        data3 = re.sub( r'ÃƒËœ', 'Æ', metadata['exif_strekningsnavn']) 
        print( data3) 
        
        
        allowedchars = r'[^0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZÆØÅæøå!-._]'
        data = re.sub( allowedchars, '_',  metadata['exif_strekningsnavn'] ) 
        print( data) 
        data = re.sub( r'_{1,}', '_', data)
        print( data) 
        # print( re.sub( r'[^0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ]', '_', metadata['exif_strekningsnavn'] )) 
        # print( re.sub( r'[^LKEDALEN]', '_',  metadata['exif_strekningsnavn'] ) ) 
        
        # delchars = ''.join(c for c in map(chr, range(256)) if c not in (string.punctuation + string.digits + string.letters) )
    
    
    # return metadata['exif_strekningsnavn' ] 


    