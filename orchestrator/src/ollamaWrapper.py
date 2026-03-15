import ollama

class OllamaWrapper:
    def __init__(self, modelName='llama3.1:8b'):
        self.modelName = modelName
    
    def isRunning(self):
        """
        Checks if the exact model name self.modelName is available in Ollama.
        """
        try:
            response = ollama.list()
        except Exception:
            return False

        listOfModels = response.get('models', [])
        for modelInfo in listOfModels:
            modelName = modelInfo.get('model')
            # Check for exact match or match-with-tag
            if modelName == self.modelName or (modelName and modelName.split(':')[0] == self.modelName):
                return True
        return False
    
    async def initModel(self):
        """
        Asynchronously checks if the models are locally available and pulls them if not.
        """
        client = ollama.AsyncClient()
        if not self.isRunning():
            print(f"[*] Pulling main model: {self.modelName}")
            await client.pull(self.modelName)
        
        # Pull embedding model if not present? Actually list() shows all.
        # Let's just pull nomic-embed-text to be sure.
        print("[*] Ensuring embedding model 'nomic-embed-text' is available...")
        await client.pull('nomic-embed-text')
            
    async def getEmbedding(self, text: str) -> list:
        """
        Generates an embedding vector for the given text.
        """
        if not text.strip():
            return [0.0] * 768 # nomic-embed-text dimension is 768
        
        try:
            client = ollama.AsyncClient()
            response = await client.embed(model='nomic-embed-text', input=text)
            
            # Handle both Pydantic model (new) and dict (old) responses
            if hasattr(response, 'embeddings'):
                embeddings = response.embeddings
            elif isinstance(response, dict):
                embeddings = response.get('embeddings', [])
            else:
                embeddings = []

            if embeddings:
                return embeddings[0]
            return [0.0] * 768
        except Exception as e:
            print(f"DEBUG: Embedding error: {str(e)}")
            return [0.0] * 768
            
    async def generateTasksFromNotes(self, notes: list) -> str:
        """
        Generates actionable tasks from a list of notes.
        Returns a JSON string.
        """
        system_prompt = (
            "You are an expert Project Manager and System Architect. Your goal is to transform vague notes into high-quality, actionable technical tasks.\n\n"
            "CRITICAL RULES:\n"
            "1. NO SUMMARY TASKS: If a note describes a project (e.g., 'Build a Pi weather app'), DO NOT create a high-level task like 'Build the app'. Instead, break it into 5-10 small, atomic tasks.\n"
            "2. ATOMIC DECOMPOSITION: Every task must be a single, specific unit of work. If a task description contains multiple distinct steps, break those out into separate tasks.\n"
            "3. ACTIONABLE DESCRIPTIONS: Every task MUST have a detailed description that outlines the EXACT technical steps to complete it. Use bullet points in descriptions.\n"
            "4. SINGLE TAG POLICY: Exactly ONE tag per task. Use the project name (e.g., [\"WeatherApp\"]) to link related tasks.\n"
            "5. EXAMPLE OF GRANULARITY:\n"
            "   - CORRECT: 'Set up SSH on Raspberry Pi', 'Install Flask on Pi', 'Register for OpenWeather API'.\n"
            "   - INCORRECT: 'Complete Weather App Project' (Too broad).\n\n"
            "Task Fields:\n"
            "   - name: Clear, concise title.\n"
            "   - description: STEP-BY-STEP manual or technical sub-steps.\n"
            "   - priority: 'Low', 'Medium', or 'High'.\n"
            "   - status: Always 'TODO'.\n"
            "   - tags: A single-element list.\n\n"
            "Output format (STRICT): JSON object with a \"tasks\" key."
        )
        
        user_prompt = "RECAP OF ALL NOTES TO PROCESS:\n"
        for i, note in enumerate(notes, 1):
            user_prompt += f"--- START NOTE {i} ---\n{note}\n--- END NOTE {i} ---\n\n"
            
        print(f"DEBUG: Sending to Ollama:\n{user_prompt}")
        
        try:
            client = ollama.AsyncClient()
            response = await client.chat(
                model=self.modelName,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt}
                ],
                format="json"
            )
            content = response.get('message', {}).get('content', '{}')
            if not content or content.strip() == "":
                return '{"tasks": []}'
            return content
        except Exception as e:
            print(f"DEBUG: Ollama chat error: {str(e)}")
            return '{"tasks": []}'
