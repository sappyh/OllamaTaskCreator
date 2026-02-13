import ollama

class OllamaWrapper:
    def __init__(self, modelName='ministral-3'):
        self.modelName = modelName
    
    def isRunning(self):
        """
        Checks if a model with a name starting with self.modelName is running in Ollama.
        """
        try:
            response = ollama.list()
        except Exception:
            # It's good practice to handle potential connection errors,
            # for example if the Ollama service is not running.
            return False

        # The response from ollama.list() is a dictionary of dictionaries
        # The 'models' key contains a list of dictionaries with model details.
        listOfModels = response.get('models')
        for modelInfo in listOfModels:
            modelName = modelInfo.get('model')
            if modelName and modelName.startswith(self.modelName):
                return True
        return False
    
    def getModel(self):
        

    
