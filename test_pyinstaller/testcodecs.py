import json 


def lesexifstrekning( kodek ): 
    filnavn = '/mnt/c/DATA/leveranser/vegbilder/bilder/debug_08Fv402hp1/orginal_stedfesting/' + \
                '08/2018/08-Fv402/Hp01_LØKEDALEN_XF401/F1_2018_08_21/Fy08_Fv402_hp01_f1_m00044.json'



    with open( filnavn, encoding=kodek) as f: 
        metadata = json.load( f) 
        
    
    print( metadata['exif_strekningsnavn'] ) 
    return metadata['exif_strekningsnavn' ] 
