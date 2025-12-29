import os
from dotenv import load_dotenv
from llm_helper import generate_project_plan

load_dotenv(override=True)

def test_llm_connection():
    print("🧪 Testing LLM Provider Connection...")
    
    provider = os.getenv("LLM_PROVIDER", "ncku")
    print(f"🔹 Configured Provider: {provider}")
    
    # Mock data
    result = generate_project_plan(
        course_name="Test Course",
        members="Alice, Bob",
        assignment_text="Build a Hello World app.",
        current_date="2024-01-01",
        due_date="2024-01-07",
        output_format="Docs"
    )
    
    print("\n📝 Response Preview:")
    print("-" * 20)
    print(result[:200] + "..." if len(result) > 200 else result)
    print("-" * 20)

    if result.startswith("❌"):
        print("❌ Test FAILED")
    else:
        print("✅ Test PASSED")

if __name__ == "__main__":
    test_llm_connection()
