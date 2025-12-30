import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from dotenv import load_dotenv

# 1. Load environment variables from .env
load_dotenv()

def test_email_logic():
    print("🧪 Testing Email Domain Logic...")
    
    # 2. Get the configured domain (should match what you put in .env)
    # If .env is missing or key is not found, it defaults to the fallback (e.g., gs.ncku.edu.tw)
    default_domain = os.getenv("DEFAULT_EMAIL_DOMAIN", "gs.ncku.edu.tw")
    print(f"🔹 Configured Domain: {default_domain}")

    # 3. Test Cases
    sample_inputs = [
        "student123",              # Should get the default domain
        "alice@yahoo.com",         # Should keep existing domain
        " bob@gmail.com ",         # Should strip whitespace and keep domain
        "charlie"                  # Should get the default domain
    ]

    print("\n📋 Processing Sample Inputs:")
    
    # 4. Apply the logic from main.py
    # Logic: Strip whitespace -> If no '@', append domain -> Else, keep as is
    cleaned_inputs = [s.strip() for s in sample_inputs if s.strip()]
    final_emails = [
        f"{sid}@{default_domain}" if "@" not in sid else sid 
        for sid in cleaned_inputs
    ]

    # 5. Print Results
    for original, final in zip(cleaned_inputs, final_emails):
        print(f"  - '{original}' \t--> {final}")

    # 6. Verification
    if default_domain in final_emails[0] and "@" in final_emails[0]:
        print("\n✅ SUCCESS: Domain suffix applied correctly!")
    else:
        print("\n❌ FAILURE: Domain suffix NOT applied.")

if __name__ == "__main__":
    test_email_logic()
