import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from unittest.mock import patch, MagicMock
from custom_exceptions import LLMGenerationError
from llm_helper import generate_project_plan
from dotenv import load_dotenv
import requests

load_dotenv(override=True)

def test_retry_mechanism():
    print("🧪 Testing Retry Logic (3 Attempts)...")

    # Mock requests.post to ALWAYS fail (simulating persistent outage)
    with patch('requests.post') as mock_post:
        # Create a mock response with a 500 error
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        # Side effect: Print every time the mock is called so we can count
        def side_effect(*args, **kwargs):
            print("   -> 📞 API Called")
            return mock_response
            
        mock_post.side_effect = side_effect

        try:
            generate_project_plan("Test", "User", "Content", "Date", "Date", "Docs", retries=3)
            print("❌ FAILURE: Function should have raised exception after retries.")
        except LLMGenerationError as e:
            print(f"✅ SUCCESS: Caught Final Exception -> {e.message}")
            
        # Check how many times the API was actually called
        count = mock_post.call_count
        print(f"📊 Total API Calls: {count}")
        
        if count == 3:
            print("✅ SUCCESS: Retried exactly 3 times.")
        else:
            print(f"❌ FAILURE: Expected 3 calls, got {count}.")

if __name__ == "__main__":
    test_retry_mechanism()
