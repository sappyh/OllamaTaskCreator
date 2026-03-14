from pathlib import Path
import os
from orchestrator.src.interfaces import BaseNotesSource

class ObsidianInterface(BaseNotesSource):
    def __init__(self, pathToVault):
        self.path = Path(pathToVault).expanduser()
    
    def listAllFiles(self):
        listFiles = []
        for file in self.path.iterdir():
            if file.is_file():
                listFiles.append(file.name)
        return listFiles
    
    def retrieveContentFromFile(self, fileName):
        filesList = self.listAllFiles()
        if fileName in filesList:
            file = self.path / fileName
            file = open(file, 'r')
            content = file.read()
            file.close()
            return content
        else:
            return NameError
    
        
    


        
