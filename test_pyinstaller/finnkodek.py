import locale
import sys
import socket

def hoved(   ): 
    
    maskin = socket.gethostname()
    adr = socket.gethostbyname(maskin)
    tegnsett = locale.getpreferredencoding() 
    filsystemtegnsett = sys.getfilesystemencoding()

    print( 'maskin:', maskin, adr) 
    print( 'Tegnsett = ' + tegnsett) 
    print( 'Filsystem tegnsett = ' + filsystemtegnsett) 
    
    outputlines = [ 'Tegnsett på denne maskinen\n', str(maskin), '\n', str(adr), '\nTegnsett= ' + tegnsett, '\nFilsystemtegnsett= ' + filsystemtegnsett ]  
       
    with open( 'tegnsett.txt', 'w', encoding='utf-8') as f: 
        f.writelines( outputlines     )
        
    
if __name__ == "__main__":
    
    hoved() 

    
   


