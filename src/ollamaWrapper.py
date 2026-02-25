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
    
    async def initModel(self):
        """
        Asynchronously checks if the model is locally available and pulls it if not.
        """
        if not self.isRunning():
            client = ollama.AsyncClient()
            await client.pull(self.modelName)
            
    def generateTasksFromNotes(self, notes: list) -> str:
        """
        Generates actionable, GTD-style tasks from a list of Obsidian notes.
        """
        system_prompt = (
            "You are an expert productivity assistant adhering to Getting Things Done (GTD) principles. "
            "Your task is to review the following memos and brain dumps and generate a clean, actionable "
            "to-do list. For items that are actionable, write them as clear tasks. For items that are not "
            "immediately actionable, create tasks for clarification. Output only the task list."
        )
        
        user_prompt = "Here are the notes:\n\n"
        for i, note in enumerate(notes, 1):
            user_prompt += f"--- Note {i} ---\n{note}\n\n"
            
        response = ollama.chat(
            model=self.modelName,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ]
        )
        
        return response.get('message', {}).get('content', '')
