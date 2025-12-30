class LLMGenerationError(Exception):
    """
    Custom exception raised when the LLM fails to generate a valid response.
    check the 'message' attribute for details.
    """
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)
