import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from unittest.mock import patch, MagicMock
from custom_exceptions import LLMGenerationError
from llm_helper import generate_project_plan
from dotenv import load_dotenv

# Load env to avoid path errors
load_dotenv(override=True)

def test_exception_raising():
    print("🧪 Testing Exception Handling...")

    # Mocking requests.post to simulate a 500 error
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        try:
            print("🔹 Triggering Mocked API Error...")
            generate_project_plan("Test", "User", "Content", "Date", "Date", "Docs")
            print("❌ FAILURE: Exception was NOT raised!")
        except LLMGenerationError as e:
            print(f"✅ SUCCESS: Caught Expected Exception -> {e.message}")
        except Exception as e:
            print(f"❌ FAILURE: Caught wrong exception type -> {type(e)}")

if __name__ == "__main__":
    test_exception_raising()
