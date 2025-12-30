# Changelog

## [Unreleased]
### Fixed
- Corrected malformed `git clone` command syntax in README.md.

# 🛠️ GPA Refactoring & Modernization Report

**Date:** December 30, 2025
**Status:** Major Refactoring Complete
**Version:** 2.0 (Stable / Multi-Provider / Secure)

---

## 1. 📂 Project Structure Architecture
**Goal:** Professionalize the codebase by separating application logic from test suites and configuration.

### **Before (Legacy)**
* **Structure:** "Flat" directory. All files (`main.py`, `utils.py`, `tests.py`, `.env`) lived in the root folder.
* **Problem:** As the project grew, it became cluttered. It was hard to distinguish between source code and test scripts. Imports were simple but disorganized.

### **After (Current)**
* **Structure:** Standard Python Project Layout.
    * `src/`: Contains all application logic (`main.py`, `llm_helper.py`, `google_utils.py`).
    * `tests/`: Contains all unit/integration tests (`test_auth.py`, `test_retry.py`).
    * **Root:** Only configuration files remain (`requirements.txt`, `.gitignore`, `README.md`, `.env`).
* **Technical Change:**
    * **Imports:** Updated `tests/` files to dynamically add `../src` to the system path to locate modules.
    * **Execution:** Run command changed from `streamlit run main.py` to `python -m streamlit run src/main.py`.

---

## 2. 🔐 Authentication & Security
**Goal:** Eliminate security vulnerabilities and support cloud deployment.

### **A. Token Storage (Pickle vs. JSON)**
* **Old Code:** Used `pickle` to serialize Google OAuth credentials.
    * *Risk:* `pickle` is insecure; loading a malicious pickle file can execute arbitrary code. It is also binary and opaque.
* **New Code:** Uses `token.json` via `creds.to_json()`.
    * *Benefit:* Secure, human-readable, and standard.
    * *File:* `src/google_utils.py`

### **B. OAuth Scope (Least Privilege)**
* **Old Code:** Requested `https://www.googleapis.com/auth/drive` (Full Access).
    * *Risk:* If the token leaked, the attacker had full control over the user's entire Google Drive.
* **New Code:** Downgraded to `https://www.googleapis.com/auth/drive.file`.
    * *Benefit:* The app can **only** access/edit files it created itself. It cannot touch the user's personal files.
    * *Evidence:* `SCOPES` definition in `src/google_utils.py`.

### **C. Cloud Deployment Support**
* **Old Code:** Relied exclusively on a local `credentials.json` file.
* **New Code:** Checks `st.secrets["google_oauth"]` first.
    * *Benefit:* Allows deployment to Streamlit Cloud without uploading sensitive JSON files.

---

## 3. 🤖 LLM Provider Abstraction
**Goal:** Remove vendor lock-in to the private NCKU API.

### **Old Code (Hardcoded)**
```python
# Legacy llm_helper.py
api_url = "[https://api-gateway.netdb.csie.ncku.edu.tw/api/chat](https://api-gateway.netdb.csie.ncku.edu.tw/api/chat)"
# Only worked for NCKU students
```

### **New Code (Multi-Provider)**
Refactored `src/llm_helper.py` to read `LLM_PROVIDER` from `.env`.
* **Supported Providers:**
    1.  **OpenAI** (Standard commercial use)
    2.  **Google Gemini** (High context window)
    3.  **Ollama** (Local/Private/Free)
    4.  **NCKU** (Legacy support maintained)
* **Implementation:** The `generate_project_plan` function now switches payload formatting based on the provider (e.g., `messages` for OpenAI vs. `contents` for Gemini).

---

## 4. 🛡️ Reliability & Robustness
**Goal:** Prevent crashes due to API timeouts or "chatty" LLM responses.

### **A. Retry Mechanism**
* **Old Code:** Single API call. If it timed out or failed (500 Error), the app crashed immediately.
* **New Code:** Implemented a `retries=3` loop with exponential backoff.
    * *Logic:* `for attempt in range(retries): ... time.sleep(2)`
    * *Benefit:* Transformed a fragile demo into a resilient tool.
    * *File:* `src/llm_helper.py`

### **B. Robust JSON Parsing**
* **Old Code:** `json_content.replace("```json", "")`
    * *Failure Mode:* If the LLM said *"Here is your JSON: [..."*, the parser failed because the string didn't start exactly as expected.
* **New Code:** Regex Extraction.
    * *Logic:* `re.search(r'\[.*\]', json_content, re.DOTALL)`
    * *Benefit:* Surgical extraction of the JSON array, ignoring all conversational filler text.
    * *File:* `src/google_utils.py`

### **C. Proper Error Handling**
* **Old Code:** Returned error strings like `"❌ Error: ..."` and checked for them in `main.py`.
    * *Problem:* "Stringly typed" errors are brittle and hard to debug.
* **New Code:** Introduced `class LLMGenerationError(Exception)`.
    * *Benefit:* `llm_helper.py` raises explicit exceptions, and `main.py` uses `try...except` blocks to handle them gracefully.

---

## 5. 📉 Dependency Optimization
**Goal:** Simplify installation.

* **Old Code:** Imported the `graphviz` Python library.
    * *Requirement:* Users had to install the Graphviz **system binary** (via `apt-get` or `brew`), which is a huge barrier for Windows users.
* **New Code:** Removed `graphviz` library.
    * *Solution:* We now generate a raw DOT string and use `st.graphviz_chart(dot_string)` which renders natively in the browser without backend dependencies.
    * *File:* `src/main.py`

---

## 6. ⚙️ Configuration
**Goal:** Make the tool generic, not NCKU-specific.

* **Email Domain:** Added `DEFAULT_EMAIL_DOMAIN` to `.env`.
    * The code now dynamically appends this domain (e.g., `@gmail.com`) if the user inputs a raw ID, instead of hardcoding `@gs.ncku.edu.tw`.
* **Environment Variables:**
    * `.env` is now loaded from the project root correctly, even though code is in `src/`.

---

## Summary of Files & Locations

| Component | Old Location | New Location | Key Changes |
| :--- | :--- | :--- | :--- |
| **Main App** | `main.py` | `src/main.py` | Graphviz removed, Exception handling added. |
| **LLM Logic** | `llm_helper.py` | `src/llm_helper.py` | Multi-provider support, Retry loops. |
| **Google Tools** | `google_utils.py` | `src/google_utils.py` | Regex JSON parsing, Secure Auth. |
| **Exceptions** | *Did not exist* | `src/custom_exceptions.py` | New dedicated error class. |
| **Tests** | *Mixed in root* | `tests/*.py` | Isolated, imports fixed with `sys.path`. |
| **Config** | `.env` | `.env` (Root) | Added `LLM_PROVIDER`, `DEFAULT_EMAIL_DOMAIN`. |
