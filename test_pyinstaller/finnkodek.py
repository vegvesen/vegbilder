import locale
import sys

def hoved(   ): 
    
    
    tegnsett = locale.getpreferredencoding() 
    filsystemtegnsett = sys.getfilesystemencoding()

    print( 'Tegnsett = ' + tegnsett) 
    print( 'Filsystem tegnsett = ' + filsystemtegnsett) 
    
    outputlines = [ 'Tegnsett på denne maskinen', 'Tegnsett= ' + tegnsett, 'Filsystemtegnsett= ' + filsystemtegnsett ]  
       
    with open( 'tegnsett.txt', 'w', encoding='utf-8') as f: 
        f.writelines( outputlines     )
        
    
if __name__ == "__main__":
    
    hoved() 

    
   


