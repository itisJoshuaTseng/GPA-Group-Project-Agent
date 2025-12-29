import os
import json
import base64
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import streamlit as st

# Fixes Issue #9: Downgraded 'drive' to 'drive.file' for security and easier verification
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/presentations'
]

def get_google_creds():
    """
    Retrieves Google Cloud credentials using a sustainable hierarchy:
    1. Streamlit Secrets (Production/Cloud Deployment)
    2. Local 'token.json' (Local Development)
    3. OAuth Flow (First-time Local Setup)
    """
    creds = None
    
    # Strategy 1: Production - Check Streamlit Secrets
    # This fixes Issue #1 by allowing server-side config without file upload
    # FIXED: Added try-except because accessing st.secrets crashes if no file exists
    try:
        if "google_oauth" in st.secrets:
            try:
                # Reconstruct credentials from dictionary in secrets
                creds = Credentials.from_authorized_user_info(
                    info=st.secrets["google_oauth"], 
                    scopes=SCOPES
                )
            except Exception as e:
                st.error(f"⚠️ Error loading credentials from secrets: {e}")
    except Exception:
        # StreamlitSecretNotFoundError or FileNotFoundError will be caught here
        # We silently pass to allow fallback to local strategies
        pass

    # Strategy 2: Local Development - Check token.json
    # Fixes Issue #4: Replaces insecure 'pickle' with standard JSON
    if not creds and os.path.exists('token.json'):
        try:
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        except Exception as e:
            st.warning(f"⚠️ Corrupt token.json found. You may need to re-login. Error: {e}")

    # Validation & Refresh
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                st.error(f"❌ Session expired and refresh failed: {e}")
                creds = None

        # Strategy 3: Local Setup - Interactive Login
        # Only runs if no valid secrets or tokens exist
        if not creds:
            if not os.path.exists('credentials.json'):
                st.error("❌ 'credentials.json' not found. Please download it from Google Cloud Console and place it in the root directory.")
                return None
            
            try:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
                
                # Save the new token as JSON (Sustainable & Secure)
                with open('token.json', 'w') as token:
                    token.write(creds.to_json())
            except Exception as e:
                st.error(f"❌ Authentication failed: {e}")
                return None

    return creds

def get_google_service():
    """Builds and returns the Google Workspace service objects."""
    creds = get_google_creds()
    
    if not creds:
        return None, None, None, None

    try:
        return (
            build('gmail', 'v1', credentials=creds),
            build('drive', 'v3', credentials=creds),
            build('docs', 'v1', credentials=creds),
            build('slides', 'v1', credentials=creds) 
        )
    except Exception as e:
        st.error(f"❌ Failed to connect to Google Services: {e}")
        return None, None, None, None

def create_doc_with_content(service_docs, service_drive, title, content):
    """建立 Google Doc 並寫入 LLM 產生的內容"""
    try:
        doc = service_docs.documents().create(body={'title': title}).execute()
        doc_id = doc.get('documentId')
        
        requests = [
            {'insertText': {'location': {'index': 1}, 'text': content}}
        ]
        service_docs.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
        
        file_info = service_drive.files().get(fileId=doc_id, fields='webViewLink').execute()
        return doc_id, file_info.get('webViewLink')
    except Exception as e:
        st.error(f"建立文件失敗: {e}")
        return None, None

def create_slides_presentation(service_slides, service_drive, title, json_content):
    """
    建立 Google Slides (自動刪除預設空白頁 + 修正版型 + 🟢 調整封面字體大小)
    """
    try:
        # A. 解析 JSON
        clean_json = json_content.replace("```json", "").replace("```", "").strip()
        slides_data = json.loads(clean_json)
    except json.JSONDecodeError:
        return None, "❌ JSON 解析失敗，請檢查 LLM 輸出格式"

    try:
        # B. 建立簡報
        body = {'title': title}
        presentation = service_slides.presentations().create(body=body).execute()
        presentation_id = presentation.get('presentationId')
        
        # 取得預設空白頁 ID
        default_slide_id = presentation.get('slides')[0].get('objectId')
        
        # C. 準備請求
        requests = []
        
        for i, slide in enumerate(slides_data):
            slide_id = f"gen_slide_{i}"
            
            # --- 封面頁 (第一頁) ---
            if i == 0:
                layout = 'TITLE' 
                title_id = f"gen_title_{i}"
                subtitle_id = f"gen_subtitle_{i}"
                
                requests.append({
                    'createSlide': {
                        'objectId': slide_id,
                        'slideLayoutReference': {'predefinedLayout': layout},
                        'placeholderIdMappings': [
                            {'layoutPlaceholder': {'type': 'CENTERED_TITLE', 'index': 0}, 'objectId': title_id},
                            {'layoutPlaceholder': {'type': 'SUBTITLE', 'index': 0}, 'objectId': subtitle_id}
                        ]
                    }
                })
                
                slide_title = slide.get('title', title)
                slide_subtitle = slide.get('subtitle', slide.get('points', ''))
                
                if slide_title:
                    # 1. 先填入文字
                    requests.append({'insertText': {'objectId': title_id, 'text': slide_title}})
                    
                    # 🟢 【新增功能】 2. 緊接著修改字體大小
                    requests.append({
                        'updateTextStyle': {
                            'objectId': title_id,
                            'style': {
                                'fontSize': {
                                    'magnitude': 42, 
                                    'unit': 'PT'
                                }
                            },
                            'fields': 'fontSize'
                        }
                    })

                if slide_subtitle:
                    requests.append({'insertText': {'objectId': subtitle_id, 'text': str(slide_subtitle)}})
            
            # --- 內頁 (其他頁) ---
            else:
                layout = 'TITLE_AND_BODY'
                title_id = f"gen_title_{i}"
                body_id = f"gen_body_{i}"

                requests.append({
                    'createSlide': {
                        'objectId': slide_id,
                        'slideLayoutReference': {'predefinedLayout': layout},
                        'placeholderIdMappings': [
                            {'layoutPlaceholder': {'type': 'TITLE', 'index': 0}, 'objectId': title_id},
                            {'layoutPlaceholder': {'type': 'BODY', 'index': 0}, 'objectId': body_id}
                        ]
                    }
                })

                if 'title' in slide and slide['title']:
                     requests.append({'insertText': {'objectId': title_id, 'text': slide['title']}})
                
                content_text = slide.get('points', '')
                if isinstance(content_text, list):
                    content_text = "\n".join([f"• {item}" for item in content_text])
                
                if content_text:
                    requests.append({'insertText': {'objectId': body_id, 'text': str(content_text)}})

        # 刪除預設空白頁
        if requests:
            requests.append({'deleteObject': {'objectId': default_slide_id}})

        # D. 執行批次更新
        if requests:
            service_slides.presentations().batchUpdate(
                presentationId=presentation_id, 
                body={'requests': requests}
            ).execute()
            
        file_info = service_drive.files().get(fileId=presentation_id, fields='webViewLink').execute()
        return presentation_id, file_info.get('webViewLink')

    except Exception as e:
        error_msg = str(e)
        return None, None
    
def share_file_permissions(service_drive, file_id, emails):
    """將檔案權限分享給組員 (Writer)"""
    for email in emails:
        user_permission = {
            'type': 'user',
            'role': 'writer',
            'emailAddress': email.strip()
        }
        try:
            service_drive.permissions().create(
                fileId=file_id,
                body=user_permission,
                fields='id',
                sendNotificationEmail=False
            ).execute()
        except Exception as e:
            st.warning(f"⚠️ 無法分享給 {email}: {e}")

def send_gmail(service_gmail, to_emails, subject, content):
    """寄送 Email 給組員 (回傳成功與失敗名單)"""
    success_list = []
    failed_list = []

    for email in to_emails:
        try:
            message = MIMEText(content)
            message['to'] = email
            message['subject'] = subject
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            body = {'raw': raw}
            service_gmail.users().messages().send(userId='me', body=body).execute()
            success_list.append(email)
            
        except Exception as e:
            failed_list.append((email, str(e)))
            
    return success_list, failed_list
