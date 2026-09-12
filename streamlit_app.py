import streamlit as st
from google import genai
from google.genai import types
from pypdf import PdfReader
from PIL import Image
import io

# ==========================================
# 1. VISUAL THEMING & GLASSMORPHISM DESIGN
# ==========================================
st.set_page_config(page_title="ClassroomBuddy AI - Portfolio Edition", page_icon="🎓", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #F4F7F9; }
    
    h1, h2, h3, h4, .stSubheader, p, label, .stMarkdown {
        color: #0A192F !important;
        font-family: 'Helvetica Neue', Arial, sans-serif;
    }
    
    /* Tarot Card Styling */
    .tarot-container {
        display: flex;
        justify-content: space-between;
        gap: 10px;
        margin-bottom: 20px;
    }
    .tarot-card {
        background: #FFFFFF;
        border: 2px solid #00B4D8;
        border-radius: 10px;
        width: 19%;
        padding: 15px;
        text-align: center;
        box-shadow: 0px 4px 8px rgba(0,0,0,0.05);
        transition: transform 0.3s ease, border-color 0.3s ease;
    }
    .tarot-card:hover {
        transform: translateY(-5px);
        border-color: #FF9F1C;
        background-color: #F0FDFA;
    }
    .tarot-title {
        font-family: 'Georgia', serif;
        font-weight: bold;
        color: #0A192F;
        font-size: 16px;
        border-bottom: 2px solid #FF9F1C;
        padding-bottom: 5px;
        margin-bottom: 8px;
    }
    .tarot-theory {
        font-size: 12px;
        color: #4A5568;
        font-style: italic;
    }
    
    /* USP Hero Badge */
    .usp-badge {
        background: linear-gradient(135deg, #00B4D8, #0A192F);
        color: #FFFFFF !important;
        padding: 15px 20px;
        border-radius: 12px;
        margin-bottom: 25px;
        box-shadow: 0 4px 15px rgba(0,180,216,0.2);
    }
    .usp-badge h4, .usp-badge p {
        color: #FFFFFF !important;
    }
    </style>
""", unsafe_allow_html=True)

# Master API Key Setup
MASTER_API_KEY = "AQ.Ab8RN6JlYyGu-acNDdSclsy-PYK4YtEPZ8bSOMeNPFMA7Eejgg"

# Initialize Session State Database
if "master_user_db" not in st.session_state:
    st.session_state.master_user_db = {
        "rasajna": "buddy2026",
        "megha": "gitam2026",
        "akshaya": "law2029"
    }

if "active_user" not in st.session_state: st.session_state.active_user = None
if "chat_history_vault" not in st.session_state: st.session_state.chat_history_vault = {}
if "selected_history_topic" not in st.session_state: st.session_state.selected_history_topic = "General Study Session"
if "quiz_sheet_cache" not in st.session_state: st.session_state.quiz_sheet_cache = None
if "exam_sheet_cache" not in st.session_state: st.session_state.exam_sheet_cache = None

# ==========================================
# 2. AUTHENTICATION GATEWAY
# ==========================================
if st.session_state.active_user is None:
    st.title("🎓 ClassroomBuddy AI")
    st.caption("Advanced Legal Engineering Platform — Portfolio Edition")
    
    auth_tab1, auth_tab2 = st.tabs(["🔒 Student Login", "📝 Dynamic Registration"])
    
    with auth_tab1:
        st.markdown("#### Enter Student Credentials")
        u_in = st.text_input("Username / Roll Number", key="login_user_field").lower().strip()
        p_in = st.text_input("Password", type="password", key="login_pass_field")
        if st.button("Authenticate Login", key="login_btn_submit"):
            if u_in in st.session_state.master_user_db and st.session_state.master_user_db[u_in] == p_in:
                st.session_state.active_user = u_in
                if u_in not in st.session_state.chat_history_vault:
                    st.session_state.chat_history_vault[u_in] = {"General Study Session": []}
                st.success("Authentication successful!")
                st.rerun()
            else:
                st.error("Invalid credentials. Please verify your details.")
            
    with auth_tab2:
        st.markdown("#### Create New Student Workspace")
        reg_username = st.text_input("New Username", placeholder="e.g., megha", key="reg_user_field").lower().strip()
        reg_password = st.text_input("Create Password", type="password", placeholder="••••••••", key="reg_pass_field")
        if st.button("Register Workspace", key="reg_btn_submit"):
            if not reg_username or not reg_password:
                st.error("All registration fields are required.")
            elif reg_username in st.session_state.master_user_db:
                st.error("Username already exists in the system.")
            else:
                st.session_state.master_user_db[reg_username] = reg_password
                st.success(f"Account for '{reg_username}' registered successfully! You can now log in.")
    st.stop()

# Ensure active user thread state
if st.session_state.active_user not in st.session_state.chat_history_vault:
    st.session_state.chat_history_vault[st.session_state.active_user] = {"General Study Session": []}

# ==========================================
# 3. SIDEBAR WORKSPACE CONTROL
# ==========================================
with st.sidebar:
    st.markdown(f"### 👤 Welcome back, {st.session_state.active_user.upper()}!")
    research_mode_active = st.toggle("Live Google Search Grounding", value=True)
    st.markdown("---")
    
    st.markdown("### 💬 Active Chat Threads")
    user_conversations = st.session_state.chat_history_vault[st.session_state.active_user]
    for topic_title in list(user_conversations.keys()):
        if st.sidebar.button(f"📄 {topic_title[:20]}", key=f"side_{topic_title}"):
            st.session_state.selected_history_topic = topic_title
            st.rerun()
            
    st.markdown("---")
    new_topic_field = st.sidebar.text_input("Initialize New Topic", placeholder="e.g., BNS Section Analysis")
    if st.sidebar.button("Add Topic", key="add_topic_side"):
        if new_topic_field and new_topic_field not in user_conversations:
            user_conversations[new_topic_field] = []
            st.session_state.selected_history_topic = new_topic_field
            st.rerun()
            
    st.markdown("---")
    if st.sidebar.button("🚪 Logout Node", key="logout_sidebar_btn"):
        st.session_state.active_user = None
        st.rerun()

# ==========================================
# 4. MULTIMODAL OCR & FILE PROCESSOR (NO WORD LIMIT)
# ==========================================
def extract_file_content_and_images(file_asset):
    if file_asset is None:
        return "", []
    
    extracted_text = ""
    image_parts = []
    
    file_type = file_asset.name.split(".")[-1].lower()
    
    if file_type == "pdf":
        try:
            pdf_reader = PdfReader(file_asset)
            for idx, page in enumerate(pdf_reader.pages):
                text = page.extract_text()
                if text:
                    extracted_text += f"\n[PDF Page {idx+1}]\n" + text
        except Exception as e:
            extracted_text = f"[PDF Parsing Error: {str(e)}]"
            
    elif file_type in ["png", "jpg", "jpeg"]:
        try:
            img = Image.open(file_asset)
            image_parts.append(img)
            extracted_text = f"[Uploaded Scanned Document Image: {file_asset.name}]"
        except Exception as e:
            extracted_text = f"[Image OCR Parsing Error: {str(e)}]"
            
    return extracted_text, image_parts

# ==========================================
# 5. CORE 6-TAB SUITE WITH USP ENGINE
# ==========================================
st.title("🎓 ClassroomBuddy AI")
st.caption("Institutional Legal Engineering Platform & Socratic Assistant")

# USP Banner Showcase
st.markdown("""
<div class="usp-badge">
    <h4>⚡ Unique Platform Advantage: Statutory Compliance & Vision OCR Engine</h4>
    <p>Automated verification against new criminal codes (BNS, BNSS, BSA) with full multimodal document OCR for scanned legal evidence and zero word limits.</p>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "💬 Ask Me Anything Legal", 
    "⚖️ Case Scenario Analyser", 
    "🏛️ Jurisprudence Scholar", 
    "🎯 Quiz Studio",
    "📝 Drafting Buddy",
    "🏛️ Competitive Exam Hub"
])

# --- TAB 1: ASK ME ANYTHING LEGAL ---
with tab1:
    st.subheader("Ask Me Anything Legal")
    t1_upload = st.file_uploader("Upload legal document context (PDF or Scanned Image):", type=["pdf", "png", "jpg", "jpeg"], key="t1_file")
    
    active_chat_log = st.session_state.chat_history_vault[st.session_state.active_user][st.session_state.selected_history_topic]
    for msg in active_chat_log:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])
            
    t1_prompt = st.chat_input("Query legal concepts, statutes, or ask about your uploaded document...")
    t1_audio = st.audio_input("Record audio query:", key="t1_audio_line")
    
    if t1_prompt:
        active_chat_log.append({"role": "user", "content": t1_prompt})
        st.rerun()
        
    if active_chat_log and active_chat_log[-1]["role"] == "user":
        with st.chat_message("assistant"):
            with st.spinner("Analyzing legal frameworks & OCR streams..."):
                try:
                    client = genai.Client(api_key=MASTER_API_KEY)
                    extracted_text, image_parts = extract_file_content_and_images(t1_upload)
                    
                    sys_instruction = (
                        "You are ClassroomBuddy AI, an elite legal engineering assistant. "
                        "CRITICAL LEGAL RULE: Prioritize Bharatiya Nyaya Sanhita (BNS, 2023), BNSS, and BSA. "
                        "Legacy IPC/CrPC sections are obsolete—flag any obsolete statutory references. "
                        f"\n\nExtracted Document Text:\n{extracted_text}"
                    )
                    
                    config = {"system_instruction": sys_instruction}
                    if research_mode_active:
                        config["tools"] = [{"google_search": {}}]
                        
                    contents = [active_chat_log[-1]["content"]] + image_parts
                    
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=contents,
                        config=types.GenerateContentConfig(**config)
                    )
                    
                    st.markdown(response.text)
                    active_chat_log.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.error(f"Engine connection exception: {str(e)}")

# --- TAB 2: CASE SCENARIO ANALYSER ---
with tab2:
    st.subheader("Hey, I am your Case Analyst!")
    t2_upload = st.file_uploader("Upload Case Facts / Scanned Brief (PDF, PNG, JPG):", type=["pdf", "png", "jpg", "jpeg"], key="t2_file")
    t2_text = st.text_area("Factual Matrix Input Pane", height=120, placeholder="Paste factual details here...")
    
    if st.button("Execute IRAC Analysis", key="t2_btn"):
        if t2_text or t2_upload:
            with st.spinner("Compiling IRAC Brief & Statutory Checks..."):
                try:
                    client = genai.Client(api_key=MASTER_API_KEY)
                    extracted_text, image_parts = extract_file_content_and_images(t2_upload)
                    
                    sys_instruction = (
                        "Perform a high-rigor legal evaluation using IRAC format: "
                        "1. ISSUE, 2. RULE (Prioritize BNS/BNSS over legacy IPC), 3. APPLICATION, 4. CONCLUSION. "
                        f"\n\nContext Document:\n{extracted_text}"
                    )
                    config = {"system_instruction": sys_instruction}
                    if research_mode_active:
                        config["tools"] = [{"google_search": {}}]
                        
                    contents = [t2_text if t2_text else "Analyze uploaded facts document."] + image_parts
                    response = client.models.generate_content(model='gemini-2.5-flash', contents=contents, config=types.GenerateContentConfig(**config))
                    st.markdown(response.text)
                except Exception as e:
                    st.error(str(e))

# --- TAB 3: JURISPRUDENCE SCHOLAR ---
with tab3:
    st.subheader("Jurisprudence Painkiller")
    
    st.markdown("""
    <div class='tarot-container'>
        <div class='tarot-card'><div class='tarot-title'>John Austin</div><div class='tarot-theory'>Imperative Theory: Command of Sovereign backed by Sanctions.</div></div>
        <div class='tarot-card'><div class='tarot-title'>John Salmond</div><div class='tarot-theory'>Analytical Realism: Principles applied by Courts in litigation.</div></div>
        <div class='tarot-card'><div class='tarot-title'>H.L.A. Hart</div><div class='tarot-theory'>Union of Primary & Secondary Rules; Rule of Recognition.</div></div>
        <div class='tarot-card'><div class='tarot-title'>Hans Kelsen</div><div class='tarot-theory'>Pure Theory of Law: Hierarchy tracing to the Grundnorm.</div></div>
        <div class='tarot-card'><div class='tarot-title'>Thomas Aquinas</div><div class='tarot-theory'>Natural Law: Ordinance of divine reason for the common good.</div></div>
    </div>
    """, unsafe_allow_html=True)
    
    t3_upload = st.file_uploader("Upload Jurisprudence Reading / Scanned Text (PDF, PNG, JPG):", type=["pdf", "png", "jpg", "jpeg"], key="t3_file")
    t3_text = st.text_input("Enter philosophy doctrine or legal theory prompt...", placeholder="e.g., Hart vs Austin on Legal Obligation")
    
    if st.button("Process Philosophical Analysis", key="t3_btn"):
        if t3_text or t3_upload:
            with st.spinner("Generating Socratic Matrix & Philosophical Evaluation..."):
                try:
                    client = genai.Client(api_key=MASTER_API_KEY)
                    extracted_text, image_parts = extract_file_content_and_images(t3_upload)
                    
                    sys_instruction = (
                        "You are an elite Socratic Jurisprudence Scholar. "
                        "Construct a comparative evolutionary matrix showing how legal schools evolved or challenged prior thinkers. "
                        f"\n\nText Context:\n{extracted_text}"
                    )
                    config = {"system_instruction": sys_instruction}
                    if research_mode_active:
                        config["tools"] = [{"google_search": {}}]
                        
                    contents = [t3_text if t3_text else "Analyze jurisprudence text."] + image_parts
                    response = client.models.generate_content(model='gemini-2.5-flash', contents=contents, config=types.GenerateContentConfig(**config))
                    st.markdown(response.text)
                except Exception as e:
                    st.error(str(e))

# --- TAB 4: QUIZ STUDIO ---
with tab4:
    st.subheader("🎯 Quiz Studio")
    t4_upload = st.file_uploader("Upload syllabus notes or readings (PDF, PNG, JPG):", type=["pdf", "png", "jpg", "jpeg"], key="t4_file")
    curriculum_domain = st.text_input("Target Subject Focus Area:", value="BNS Criminal Law")
    quiz_mode = st.selectbox("Select Assessment Format:", ["Multiple Choice Questions (MCQs)", "Real-World Scenario Problems", "Long Answer Question Sheets", "Short Analytical Questions", "Fill in the Blanks"])
    
    if st.button("Generate Test Sheet", key="t4_btn"):
        with st.spinner("Generating assessment suite..."):
            try:
                client = genai.Client(api_key=MASTER_API_KEY)
                extracted_text, image_parts = extract_file_content_and_images(t4_upload)
                
                prompt = f"Construct an evaluation test sheet using format '{quiz_mode}' for subject '{curriculum_domain}'. Prioritize BNS over legacy IPC. Include an Answer Key at the end.\n\nContext:\n{extracted_text}"
                contents = [prompt] + image_parts
                response = client.models.generate_content(model='gemini-2.5-flash', contents=contents)
                st.session_state.quiz_sheet_cache = response.text
            except Exception as e:
                st.error(str(e))
                
    if st.session_state.quiz_sheet_cache:
        st.markdown(st.session_state.quiz_sheet_cache)

# --- TAB 5: DRAFTING BUDDY ---
with tab5:
    st.markdown("### **Hello, I am your Drafting Buddy!**")
    t5_upload = st.file_uploader("Upload Sample Legal Template (PDF, PNG, JPG):", type=["pdf", "png", "jpg", "jpeg"], key="t5_file")
    target_instrument = st.text_input("Document Type to Draft:", placeholder="e.g., Legal Notice for Breach of Contract")
    factual_specs = st.text_area("Factual Parameters & Client Specifications:")
    
    if st.button("Generate Legal Draft", key="t5_btn"):
        with st.spinner("Drafting legal instrument..."):
            try:
                client = genai.Client(api_key=MASTER_API_KEY)
                extracted_text, image_parts = extract_file_content_and_images(t5_upload)
                
                prompt = f"Draft a professional legal document for '{target_instrument}' using specifications: {factual_specs}. Include a formal Vocabulary Guidance section.\n\nTemplate Context:\n{extracted_text}"
                contents = [prompt] + image_parts
                response = client.models.generate_content(model='gemini-2.5-flash', contents=contents)
                st.markdown(response.text)
            except Exception as e:
                st.error(str(e))

# --- TAB 6: COMPETITIVE EXAM HUB ---
with tab6:
    st.subheader("Exam Hub")
    t6_upload = st.file_uploader("Upload Past Exam Papers (PDF, PNG, JPG):", type=["pdf", "png", "jpg", "jpeg"], key="t6_file")
    target_stream = st.selectbox("Target Exam Stream:", ["Judiciary (PCS-J)", "JAG (Indian Army Officer Branch)", "Civil Services Law Optional Track"])
    focus_area = st.text_input("Syllabus Focus Area:", value="BNS and Constitutional Law Principles")
    
    if st.button("Generate Mock Paper", key="t6_btn"):
        with st.spinner("Analyzing exam patterns & generating mock paper..."):
            try:
                client = genai.Client(api_key=MASTER_API_KEY)
                extracted_text, image_parts = extract_file_content_and_images(t6_upload)
                
                prompt = f"Analyze past paper patterns for '{target_stream}' focusing on '{focus_area}'. Generate a realistic mock exam sheet with an Answer Key.\n\nPaper Context:\n{extracted_text}"
                contents = [prompt] + image_parts
                response = client.models.generate_content(model='gemini-2.5-flash', contents=contents)
                st.session_state.exam_sheet_cache = response.text
            except Exception as e:
                st.error(str(e))
                
    if st.session_state.exam_sheet_cache:
        st.markdown(st.session_state.exam_sheet_cache)
