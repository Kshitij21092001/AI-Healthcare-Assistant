# app.py
import os
import json
import gradio as gr
from dotenv import load_dotenv

# Project modules (assumed present in project)
from pipeline import analyze_medical_report
from memory_engine import init_memory_db, add_message, get_recent
from email_engine import send_report_email
from openai import AzureOpenAI 

load_dotenv()
init_memory_db()  # ensure memory DB/table exists

# Initialize Client
client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version="2024-02-15-preview" 
)

DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT")

# Conversation state template
def new_state():
    return {
        "mode": "idle",          # idle | await_email_confirm | ask_user_email | sending
        "last_report_path": None,
        "last_doctor_email": None,
        "last_findings_md": None,
        "user_email": None,
        "last_findings_list": [],  
        "last_ai_rationale": ""
    }

# Helpers
def format_findings_table_md(findings):
    if not findings:
        return "No findings extracted."
    header = "| Test | Value | Unit | Range | Interpretation |\n|---|---:|---|---|---|\n"
    rows = ""
    for f in findings:
        name = f.get("name") or f.get("test") or ""
        value = f.get("value", "")
        unit = f.get("unit") or ""
        low = f.get("ref_low") or ""
        high = f.get("ref_high") or ""
        rng = f"{low}–{high}" if low or high else ""
        interp = f.get("interpretation", "")
        rows += f"| {name} | {value} | {unit} | {rng} | {interp} |\n"
    return header + rows

def compose_assistant_message(result):
    findings = result.get("findings", [])
    llm = result.get("llm_output", {})
    doctors = result.get("doctors", [])
    risk = result.get("risk", {})

    table_md = format_findings_table_md(findings)

    msg = "### 🔬 Extracted Lab Findings\n" + table_md + "\n\n"
    msg += "### 🩺 AI Clinical Evaluation\n"
    msg += f"- **Decision:** {llm.get('decision', 'unknown')}\n"
    msg += f"- **Confidence:** {llm.get('confidence', '')}\n"
    msg += f"- **Rationale:** {llm.get('rationale', '')}\n\n"

    if risk:
        msg += f"### ⚠️ Risk Score: {risk.get('score', 0)}/100\n"
        for flag in risk.get("flags", []):
            msg += f"- {flag.get('test')}: {flag.get('flag')}\n"
        for ins in risk.get("insights", []):
            msg += f"- Insight: {ins}\n"
        msg += "\n"

    msg += "### 👨‍⚕️ Suggested Doctors\n"
    if doctors:
        for d in doctors:
            msg += f"- **{d.get('name')}** ({d.get('specialty')}) — {d.get('contact')}\n"
    else:
        msg += "- No matching doctors found.\n"

    msg += "\nWould you like me to email this summary to the suggested doctor?"
    return msg, table_md

# --- NEW: GENERAL CHAT FUNCTION (Fixed for o1 models) ---
def generate_chat_response(user_text, state):
    """
    Handles general medical queries using the LLM.
    If a report is in history, it uses that as context.
    """
    findings_context = state.get("last_findings_md")
    
    # Build a context-aware prompt
    system_instruction = """
    You are a helpful, empathetic medical AI assistant.
    
    Guidelines:
    1. Answer the user's health questions clearly and simply.
    2. If the user asks for advice on lifestyle, diet, or improvement, give actionable steps.
    3. IMPORTANT: You are NOT a doctor. Do not give definitive diagnoses or prescribe medication. Always advise consulting a professional for serious issues.
    4. Keep responses concise (max 3-4 paragraphs).
    """

    if findings_context:
        system_instruction += f"\n\nCONTEXT: The user recently uploaded a lab report with these findings:\n{findings_context}\n\nUse these findings to personalize your advice if relevant (e.g., if Vitamin D is low, suggest sunlight/supplements)."
    else:
        system_instruction += "\n\nCONTEXT: The user has NOT uploaded a report yet. Answer generally."

    try:
        response = client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_text}
            ]
            # REMOVED: temperature=0.7 (Not supported by o1 models)
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"I'm having trouble connecting to my knowledge base right now. Error: {e}"


# --- MAIN LOGIC ---

def handle_upload_and_analyze(file_obj, user_text, state):
    if file_obj is None:
        return "No file uploaded.", state

    file_path = file_obj.name
    try:
        result = analyze_medical_report(file_path)
    except Exception as e:
        err = f"Error analyzing document: {e}"
        add_message("assistant", err)
        return err, state

    if "error" in result:
        msg = f"Could not extract findings: {result.get('error')}"
        add_message("assistant", msg)
        return msg, state

    assistant_msg, table_md = compose_assistant_message(result)

    state["last_report_path"] = file_path
    
    doctors = result.get("doctors", [])
    if doctors:
        state["last_doctor_email"] = doctors[0].get("contact")
    else:
        state["last_doctor_email"] = os.getenv("DOCTOR_DEFAULT_EMAIL")

    state["last_findings_md"] = table_md
    state["mode"] = "await_email_confirm"

    state["last_findings_list"] = result.get("findings", [])

    llm = result.get("llm_output", {})
    decision = llm.get("decision", "Unknown").upper()
    rationale = llm.get("rationale", "No rationale provided.")
    state["last_ai_rationale"] = f"<strong>Decision:</strong> {decision}<br><strong>Rationale:</strong> {rationale}"

    add_message("user", f"Uploaded file: {os.path.basename(file_path)}")
    add_message("assistant", assistant_msg)

    return assistant_msg, state


def classify_user_intent(user_text):
    text = user_text.lower().strip()
    
    if text in ["yes", "y", "sure", "ok", "please", "go ahead", "confirm"]:
        return "CONFIRM"
    if text in ["no", "n", "nope", "cancel", "stop", "don't"]:
        return "DENY"

    print(f"DEBUG: Asking LLM to classify -> '{user_text}'")
    
    system_prompt = """
    You are a classifier for a healthcare bot.
    The bot asked: "Would you like me to email this summary?"
    
    Classify the User's response into exactly one category:
    1. CONFIRM (User agrees, e.g., "please send the email", "email it", "do it")
    2. DENY (User refuses, e.g., "don't send", "not now")
    3. OTHER (Unrelated questions or gibberish)
    
    Return ONLY the category word: CONFIRM, DENY, or OTHER.
    """
    
    try:
        response = client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ]
            # REMOVED: temperature=0.0 (Not supported by o1 models)
        )
        intent = response.choices[0].message.content.strip().upper()
        print(f"DEBUG: LLM Response -> {intent}")
        
        if "CONFIRM" in intent: return "CONFIRM"
        if "DENY" in intent: return "DENY"
        return "OTHER"
        
    except Exception as e:
        print(f"Intent Error: {e}")
        return "OTHER"


def handle_user_message(user_text, file_obj, state):
    text = (user_text or "").strip()
    add_message("user", text or "[no-text]")

    if file_obj is not None:
        return handle_upload_and_analyze(file_obj, text, state)

    mode = state.get("mode", "idle")

    # 1. Handle Email Confirmation Flow
    if mode == "await_email_confirm":
        intent = classify_user_intent(text)

        if intent == "CONFIRM":
            state["mode"] = "ask_user_email"
            resp = "Okay — please provide the email address you'd like me to share with the doctor."
            add_message("assistant", resp)
            return resp, state
            
        elif intent == "DENY":
            state["mode"] = "idle"
            resp = "Understood. I will not send the email. Is there anything else I can help you with regarding your health?"
            add_message("assistant", resp)
            return resp, state
        
        state["mode"] = "idle" 


    # 2. Handle Email Address Input
    if mode == "ask_user_email":
        candidate = text
        if "@" in candidate and "." in candidate:
            state["user_email"] = candidate
            state["mode"] = "sending"
            resp = f"Thanks — sending the report summary to the doctor now (to {state.get('last_doctor_email')})."
            add_message("assistant", resp)
            send_resp, state = perform_send_email(state)
            return send_resp, state
        else:
            resp = "That doesn't look like a valid email address. Please enter a valid email (example: you@example.com)."
            add_message("assistant", resp)
            return resp, state

    # 3. Handle General Chat (The Upgrade!)
    print("DEBUG: Generating general chat response...")
    ai_response = generate_chat_response(text, state)
    add_message("assistant", ai_response)
    return ai_response, state

from email_engine import send_report_email
import os

def generate_professional_email_html(user_email, findings_list, ai_rationale):
    rows_html = ""
    for f in findings_list:
        interp = str(f.get("interpretation", "")).lower()
        bg_color = "#ffe6e6" if "high" in interp or "low" in interp else "#ffffff"
        
        name = f.get('name') or f.get('test') or "Unknown Test"
        val = f.get('value', '')
        unit = f.get('unit', '')
        flag = f.get('interpretation', '')

        rows_html += f"""
        <tr style="background-color: {bg_color}; border-bottom: 1px solid #ddd;">
            <td style="padding: 10px; border: 1px solid #ddd;">{name}</td>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">{val}</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{unit}</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{flag}</td>
        </tr>
        """

    html_body = f"""
    <div style="font-family: Arial, sans-serif; color: #333; max-width: 600px; border: 1px solid #eee; padding: 20px;">
        <h2 style="color: #0056b3; margin-top: 0;">🩺 Patient Consultation Request</h2>
        <p>Hello Doctor,</p>
        <p>A patient has requested a review of their recent lab report. Please find the summary below.</p>
        
        <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #0056b3; margin: 20px 0;">
            <strong>Patient Contact:</strong> <a href="mailto:{user_email}">{user_email}</a>
        </div>

        <h3 style="border-bottom: 2px solid #0056b3; padding-bottom: 5px; color: #444;">🔬 Extracted Lab Findings</h3>
        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 14px;">
            <thead>
                <tr style="background-color: #0056b3; color: white;">
                    <th style="padding: 10px; border: 1px solid #ddd;">Test</th>
                    <th style="padding: 10px; border: 1px solid #ddd;">Value</th>
                    <th style="padding: 10px; border: 1px solid #ddd;">Unit</th>
                    <th style="padding: 10px; border: 1px solid #ddd;">Flag</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>

        <h3 style="border-bottom: 2px solid #0056b3; padding-bottom: 5px; margin-top: 25px; color: #444;">🤖 AI Clinical Analysis</h3>
        <div style="background-color: #fff3cd; padding: 15px; border: 1px solid #ffeeba; border-radius: 4px;">
            {ai_rationale}
        </div>

        <p style="margin-top: 30px; font-size: 12px; color: #777; border-top: 1px solid #eee; padding-top: 10px;">
            <em>Note: This summary was generated by an AI assistant. Please review the full clinical context before making a diagnosis.</em>
        </p>
    </div>
    """
    return html_body


def perform_send_email(state):
    doctor_contact = state.get("last_doctor_email")
    if doctor_contact and "@" in str(doctor_contact):
        to_email = doctor_contact
    else:
        to_email = os.getenv("DOCTOR_DEFAULT_EMAIL", "kshitijphotos1@gmail.com")

    user_email = state.get("user_email") or os.getenv("DEFAULT_USER_EMAIL", "patient@example.com")
    
    findings_list = state.get("last_findings_list", [])
    ai_rationale = state.get("last_ai_rationale", "No analysis available.")
    
    body_html = generate_professional_email_html(user_email, findings_list, ai_rationale)
    
    subject = "Patient Report Review: Action Required"

    ok, info = send_report_email(to_email=to_email, subject=subject, body=body_html, attachments=None)

    if ok:
        msg = f"✅ Email sent successfully to {to_email}. The doctor will reach out to you at {user_email} if they are available."
        add_message("assistant", msg)
        add_message("assistant", f"Email metadata: to={to_email}, subject={subject}")
        state["mode"] = "idle"
        return msg, state
    else:
        msg = f"❌ Failed to send email: {info}. Please try again or provide a different contact email."
        add_message("assistant", msg)
        state["mode"] = "idle"
        return msg, state


# ==========================================
#  MODERN UI IMPLEMENTATION
# ==========================================

theme = gr.themes.Ocean(
    primary_hue="blue",
    neutral_hue="slate",
    text_size="lg",
    spacing_size="md",
    radius_size="lg"
)

custom_css = """
footer {visibility: hidden}
.gradio-container {
    margin: 0 !important; 
    padding: 0 !important; 
    width: 100% !important; 
    max-width: 100% !important;
}
#chatbot {
    height: 75vh !important; 
    overflow-y: auto;
}
"""

with gr.Blocks(title="Healthcare Assistant", fill_height=True) as demo:

    with gr.Row():
        gr.Markdown(
            """
            # 🏥 Healthcare Assistant
            ### AI-Powered Medical Report Analyzer & Doctor Connect
            """
        )

    # Chat Interface
    chatbot = gr.Chatbot(
        elem_id="chatbot",
        label="Chat Session",
        avatar_images=(None, "https://cdn-icons-png.flaticon.com/512/3774/3774299.png")
    )

    state = gr.State(new_state())

    # Multimodal Input
    chat_input = gr.MultimodalTextbox(
        interactive=True,
        file_count="single",
        placeholder="Type a message or upload a report...",
        show_label=False,
        scale=7
    )

    class FileWrapper:
        def __init__(self, path):
            self.name = path

    def on_send(message, chat_history, state_obj):
        user_text = message.get("text", "").strip()
        files = message.get("files", [])

        st = state_obj or new_state()

        # Sticky File Check
        current_file_path = files[0] if files else None
        last_processed_path = st.get("last_report_path")
        
        is_fresh_file = current_file_path and (current_file_path != last_processed_path)

        file_obj = None
        if is_fresh_file:
            file_obj = FileWrapper(current_file_path)

        try:
            if file_obj:
                print("DEBUG: New file upload detected via Multimodal Input.")
                assistant_text, new_state = handle_upload_and_analyze(file_obj, user_text, st)
            else:
                print(f"DEBUG: Handling text message: '{user_text}' (Mode: {st.get('mode')})")
                assistant_text, new_state = handle_user_message(user_text, None, st)
                
        except Exception as e:
            print(f"ERROR: {e}")
            assistant_text = f"Internal error: {e}"
            new_state = st

        user_msg_content = user_text
        
        if is_fresh_file:
            filename = os.path.basename(current_file_path)
            if user_msg_content:
                user_msg_content += f"\n(Attached: {filename})"
            else:
                user_msg_content = f"Uploaded file: {filename}"
        
        chat_history.append({"role": "user", "content": user_msg_content})
        chat_history.append({"role": "assistant", "content": assistant_text})

        return chat_history, new_state

    chat_input.submit(
        on_send, 
        inputs=[chat_input, chatbot, state], 
        outputs=[chatbot, state]
    )

    with gr.Accordion("Debug Memory", open=False):
        mem_btn = gr.Button("Show recent memory")
        mem_out = gr.Textbox(label="Recent memory", lines=6)
        
        def show_memory():
            recent = get_recent(10)
            s = "\n\n".join([f"{r['role']}: {r['content']}" for r in recent])
            return s
        mem_btn.click(show_memory, inputs=None, outputs=mem_out)

if __name__ == "__main__":
    demo.launch(theme=theme, css=custom_css)