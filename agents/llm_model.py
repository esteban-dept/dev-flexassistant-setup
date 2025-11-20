from langchain_openai import AzureChatOpenAI
from dotenv import load_dotenv
import os

class AzureModelProvider:
    """
    Provides access to Azure OpenAI chat models.
    Loads configuration from environment variables.
    """

    def __init__(
        self,
        primary_deployment: str = "gpt-4.1",
        primary_model: str = "gpt-4.1",
        light_deployment: str = "gpt-4.1-mini",
        light_model: str = "gpt-4.1-mini",
        temperature: float = 0
    ):
        load_dotenv()

        self.azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.api_version = "2024-12-01-preview"

        # Primary heavy model
        self.primary_model = AzureChatOpenAI(
            azure_endpoint=self.azure_endpoint,
            api_key=self.api_key,
            api_version=self.api_version,
            azure_deployment=primary_deployment,
            model=primary_model,
            temperature=temperature
        )

        # Lighter model for simple tasks
        self.light_model = AzureChatOpenAI(
            azure_endpoint=self.azure_endpoint,
            api_key=self.api_key,
            api_version=self.api_version,
            azure_deployment=light_deployment,
            model=light_model,
            temperature=temperature
        )

    def get_primary_model(self):
        return self.primary_model

    def get_light_model(self):
        return self.light_model
