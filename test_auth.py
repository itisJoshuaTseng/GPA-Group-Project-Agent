import streamlit as st
from google_utils import get_google_creds

st.title("🔐 Auth Logic Test")

st.info("Attempting to retrieve credentials...")

# Call the function in isolation
creds = get_google_creds()

if creds and creds.valid:
    st.success("✅ **Success!** Valid credentials retrieved.")
    st.json({
        "Scopes": creds.scopes,
        "Token Valid": creds.valid,
        "Expired": creds.expired
    })
    
    # Verify the Scope Fix (Issue #9)
    if "https://www.googleapis.com/auth/drive.file" in creds.scopes:
        st.write("🛡️ Security Check: **PASSED** (Using restricted `drive.file` scope)")
    else:
        st.warning("⚠️ Security Check: **FAILED** (Still using full `drive` scope?)")
        
else:
    st.error("❌ Failed to retrieve credentials.")
