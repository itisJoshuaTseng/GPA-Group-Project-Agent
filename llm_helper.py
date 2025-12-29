import os
import json
import requests
from dotenv import load_dotenv
from pathlib import Path
from custom_exceptions import LLMGenerationError  # Import the new exception

# 1. Load .env
current_dir = Path(__file__).parent
env_path = current_dir / '.env'
load_dotenv(dotenv_path=env_path, override=True)

def generate_project_plan(course_name, members, assignment_text, current_date, due_date, output_format="Docs"):
    """
    Calls LLM API to generate project plan.
    Raises: LLMGenerationError on failure.
    """
    
    # --- Configuration ---
    provider = os.getenv("LLM_PROVIDER", "ncku").lower()
    api_key = os.getenv("API_KEY", "")
    
    default_models = {
        "openai": "gpt-4o",
        "gemini": "gemini-1.5-flash",
        "ollama": "llama3",
        "ncku": "gpt-oss:120b"
    }
    model_name = os.getenv("MODEL_NAME", default_models.get(provider, "gpt-4o"))
    
    # --- API URL & Headers Setup ---
    api_url = os.getenv("API_URL", "")
    headers = {"Content-Type": "application/json"}
    
    if provider == "openai":
        if not api_url: api_url = "https://api.openai.com/v1/chat/completions"
        headers["Authorization"] = f"Bearer {api_key}"
        
    elif provider == "ollama":
        if not api_url: api_url = "http://localhost:11434/api/chat"
        
    elif provider == "gemini":
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        
    else: # ncku
        if not api_url: api_url = "https://api-gateway.netdb.csie.ncku.edu.tw/api/chat"
        headers["Authorization"] = f"Bearer {api_key}"

    # --- Prompt Construction ---
    if output_format == "Slides":
            # (JSON Prompt - Unchanged)
            prompt = f"""
            You are a Project Manager.
            [Course]: {course_name}
            [Members]: {members}
            [Assignment]: {assignment_text}
            [Date]: Today is {current_date}, Due is {due_date}.
            
            Please generate a "Google Slides Outline" for this project.
            
            【STRICT FORMAT REQUIREMENTS】:
            1. Output a valid JSON Array.
            2. **First Slide (Cover)** must contain "title" (Main Title) and "subtitle" (Members).
            3. **Subsequent Slides** must contain "title" and "points" (Bullet points, separated by \\n).
            4. Do NOT use Markdown formatting (no ```json). Just raw JSON.
            5. Minimum 7 slides.

            【Example Format】:
            [
                {{"title": "{course_name} Final Project: [Topic]", "subtitle": "Members: {members}\\nDate: {current_date}"}},
                {{"title": "Project Goals", "points": "1. Goal A\\n2. Goal B"}},
                {{"title": "Task Allocation", "points": "• Alice: Frontend\\n• Bob: Backend"}}
            ]
            """
    else:
        # (Docs Prompt - Unchanged)
        prompt = f"""
        You are a professional Project Manager.
        [Course]: {course_name}
        [Members]: {members}
        [Assignment]: {assignment_text}
        [Date]: Today is {current_date}, Due is {due_date}.

        Please generate a comprehensive project proposal.

        【STRICT FORMAT - NO MARKDOWN TABLES】:
        1. **Plain Text Only**.
        2. **Do NOT use '|' characters**. Do NOT use Markdown tables.
        3. Use [Brackets] for headers.
        4. Task Allocation Format: "- [Task Name]: [Owner] (Deliverable: [Item])"

        【Example Output】:
        [1. Project Goal]
        The goal is to develop...

        [2. Tasks]
        - Crawler Dev: Alice (Deliverable: Python script)
        - Backend: Bob (Deliverable: API Docs)

        [3. Schedule]
        - 12/20: Arch Review
        """

    # --- Payload Construction ---
    payload = {}
    
    if provider == "gemini":
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
    elif provider == "openai":
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
    else: # ollama, ncku
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.7}
        }

    print(f"🚀 Sending request to {provider.upper()}...")

    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=(10, 300))
        
        if response.status_code != 200:
            # RAISE Exception instead of returning string
            raise LLMGenerationError(f"API Error ({response.status_code}): {response.text}")

        result_json = response.json()
        content = ""
        
        # --- Response Parsing ---
        if provider == "gemini":
            try:
                content = result_json["candidates"][0]["content"]["parts"][0]["text"]
            except KeyError:
                 raise LLMGenerationError(f"Gemini Parsing Error: {result_json}")
                 
        elif provider == "openai":
            if "choices" in result_json:
                content = result_json["choices"][0]["message"]["content"]
                
        elif provider == "ollama" or provider == "ncku":
            if "message" in result_json:
                content = result_json["message"]["content"]
            elif "response" in result_json:
                content = result_json["response"]
                
        if not content:
            raise LLMGenerationError(f"Unknown response format: {result_json.keys()}")
            
        # --- Cleaning ---
        clean_content = content.replace("**", "").replace("##", "").replace("###", "")
        clean_content = clean_content.replace("|---|", "").replace("|", "  ")
        
        return clean_content

    except requests.exceptions.Timeout:
        raise LLMGenerationError("Request Timed Out. Please try again.")
    except LLMGenerationError:
        raise # Re-raise known errors
    except Exception as e:
        raise LLMGenerationError(f"Unexpected Error: {str(e)}")

def extract_text_from_pdf(pdf_file):
    import pypdf
    try:
        pdf_reader = pypdf.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return f"Error reading PDF: {e}"
