# backend_app/main.py

import json
import re
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime
import mysql.connector
import asyncio
import aiohttp # For actual async HTTP requests if Groq API were live

# --- Configuration ---
MYSQL_CONFIG = {
    "host": "sanika", # Replace with your MySQL host if different
    "user": "sanika",      # Replace with your MySQL username
    "password": "Sanu@1/17",  # Replace with your MySQL password
    "database": "hcp_db" # Ensure this database exists
}

# Conceptual Groq API Configuration
GROQ_API_KEY = "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" # Replace with your actual Groq API key for live calls
GROQ_API_URL_GEMMA = "https://api.groq.com/openai/v1/chat/completions" # Example, verify actual endpoint

# --- Database Setup and Utility ---
def get_db_connection():
    """Establishes a connection to the MySQL database."""
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Error connecting to MySQL: {err}")
        # In a real app, you might want to raise this or handle it more gracefully
        return None

def initialize_database():
    """Creates the hcp_interactions table if it doesn't exist."""
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to database for initialization.")
        return
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hcp_interactions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                hcp_name VARCHAR(255) NOT NULL,
                interaction_date DATE NOT NULL,
                products_discussed TEXT,
                key_discussion_points TEXT,
                sentiment ENUM('Positive', 'Neutral', 'Negative'),
                follow_up_actions TEXT,
                interaction_method ENUM('form', 'chat') NOT NULL,
                raw_chat_log TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        print("Database initialized successfully. `hcp_interactions` table checked/created.")
    except mysql.connector.Error as err:
        print(f"Error initializing database: {err}")
    finally:
        cursor.close()
        conn.close()

# --- Pydantic Models for Request/Response ---
class HCPInteractionBase(BaseModel):
    hcp_name: str = Field(..., min_length=1, example="Dr. Jane Doe")
    interaction_date: date = Field(..., example=date.today())
    products_discussed: Optional[str] = Field(None, example="ProductX, ProductY")
    key_discussion_points: Optional[str] = Field(None, example="Discussed new trial results for ProductX.")
    sentiment: Optional[str] = Field(None, example="Positive") # Positive, Neutral, Negative
    follow_up_actions: Optional[str] = Field(None, example="Send follow-up email with trial data.")

class HCPInteractionFormInput(HCPInteractionBase):
    pass

class HCPInteractionChatInput(BaseModel):
    message: str
    history: List[Dict[str, str]] = [] # List of {"role": "user/assistant", "content": "message"}
    current_extraction_data: Optional[Dict[str, Any]] = {} # To maintain state of extracted data during chat

class HCPInteractionOutput(HCPInteractionBase):
    id: int
    interaction_method: str
    raw_chat_log: Optional[str] = None
    created_at: datetime

class ChatResponse(BaseModel):
    ai_message: str
    is_complete: bool = False
    extracted_data: Optional[Dict[str, Any]] = None # Data extracted so far
    interaction_id: Optional[int] = None # If logged

# --- AI Service Mocks / Conceptual LangGraph & LLM Calls ---

async def call_groq_llm(prompt: str, model: str = "gemma2-9b-it", chat_history: List[Dict[str, str]] = None) -> str:
    """
    MOCK function to simulate a call to Groq's LLM API.
    In a real scenario, this would make an authenticated async HTTP request.
    """
    print(f"\n--- Mocking Groq LLM Call ({model}) ---")
    print(f"Prompt: {prompt}")
    if chat_history:
        print(f"History: {json.dumps(chat_history, indent=2)}")
    print("---------------------------------------\n")

    # Simulate some basic NLU and response generation
    # This is highly simplified. A real LLM would provide much richer responses.
    lower_prompt = prompt.lower()

    if "hello" in lower_prompt or "hi" in lower_prompt:
        return "Hello! How can I help you log an HCP interaction today?"
    if "log interaction" in lower_prompt or "record meeting" in lower_prompt:
        return "Okay, I can help with that. Who was the HCP you met with and on what date?"
    if "dr." in lower_prompt and ("date" in lower_prompt or "today" in lower_prompt or re.search(r'\d{4}-\d{2}-\d{2}', lower_prompt)):
        return "Great. What products were discussed and what were the key discussion points?"
    if ("product" in lower_prompt or "discussed" in lower_prompt) and "point" in lower_prompt:
        return "Understood. What was the overall sentiment (Positive, Neutral, Negative) and any follow-up actions?"
    if "sentiment" in lower_prompt and ("follow up" in lower_prompt or "action" in lower_prompt):
        return "Excellent. I think I have all the details. Should I try to log this interaction now? (Type 'yes' or 'log it')"
    if "yes" in lower_prompt or "log it" in lower_prompt or "correct" in lower_prompt:
        return "Understood. Attempting to log the interaction." # This will trigger logging in the calling function

    # Fallback for more complex LangGraph simulation
    # This is where LangGraph would manage a more complex flow, potentially calling different tools or LLMs.
    # For example, if gemma2-9b-it couldn't extract info, LangGraph might route to llama-3.3-70b-versatile for deeper analysis.
    # We simulate a generic "clarification" response.
    if len(prompt) > 10: # Arbitrary length to simulate some input
        return "Thanks for that information. Can you tell me a bit more about [a specific missing piece, e.g., the products discussed or key topics]?"
    
    return "I'm sorry, I didn't quite understand. Could you please rephrase or provide more details?"

    # --- Example of actual aiohttp call (conceptual, not run in this mock) ---
    # headers = {
    #     "Authorization": f"Bearer {GROQ_API_KEY}",
    #     "Content-Type": "application/json"
    # }
    # messages_payload = []
    # if chat_history:
    #     messages_payload.extend(chat_history)
    # messages_payload.append({"role": "user", "content": prompt})
    
    # payload = {
    #     "model": model,
    #     "messages": messages_payload
    # }
    # async with aiohttp.ClientSession() as session:
    #     try:
    #         async with session.post(GROQ_API_URL_GEMMA, headers=headers, json=payload) as response:
    #             response.raise_for_status() # Raise an exception for HTTP errors
    #             result = await response.json()
    #             return result.get("choices", [{}])[0].get("message", {}).get("content", "Error parsing LLM response.")
    #     except aiohttp.ClientError as e:
    #         print(f"Error calling Groq API: {e}")
    #         return f"Error communicating with AI service: {e}"
    #     except Exception as e:
    #         print(f"An unexpected error occurred during Groq API call: {e}")
    #         return "An unexpected error occurred while processing your request with the AI."


def extract_interaction_details_from_text(text: str, existing_data: Dict = None) -> Dict[str, Any]:
    """
    Rudimentary extraction of interaction details from text.
    A real LLM/NLU system (like one built with LangGraph) would be far more sophisticated.
    """
    if existing_data is None:
        existing_data = {}
    
    extracted = existing_data.copy()

    # HCP Name
    if not extracted.get("hcp_name"):
        match_hcp = re.search(r"(?:dr\.|doctor|hcp)\s*([A-Za-z\s]+?)(?:\s*(?:on|about|regarding|and|\.|$))", text, re.IGNORECASE)
        if match_hcp:
            extracted["hcp_name"] = match_hcp.group(1).strip().title()

    # Date
    if not extracted.get("interaction_date"):
        match_date = re.search(r"(\d{4}-\d{2}-\d{2})|today", text, re.IGNORECASE)
        if match_date:
            if match_date.group(1):
                extracted["interaction_date"] = match_date.group(1)
            elif match_date.group(0).lower() == "today":
                extracted["interaction_date"] = date.today().isoformat()
    
    # Products Discussed (very basic)
    if not extracted.get("products_discussed"):
        match_products = re.search(r"(?:products? discussed|talked about|mentioned)\s*(.*?)(?:\.|and key|and the main)", text, re.IGNORECASE)
        if match_products:
            extracted["products_discussed"] = match_products.group(1).strip()
        elif "producta" in text.lower() or "productb" in text.lower(): # simple keyword
             prods = []
             if "producta" in text.lower(): prods.append("ProductA")
             if "productb" in text.lower(): prods.append("ProductB")
             extracted["products_discussed"] = ", ".join(prods)


    # Key Discussion Points (very basic)
    if not extracted.get("key_discussion_points"):
        match_points = re.search(r"(?:key points?|discussion points|main point was)\s*(.*?)(?:\.|and sentiment|and follow-up)", text, re.IGNORECASE)
        if match_points:
            extracted["key_discussion_points"] = match_points.group(1).strip()
        elif "efficacy data" in text.lower(): # simple keyword
            extracted["key_discussion_points"] = "Efficacy data"


    # Sentiment
    if not extracted.get("sentiment"):
        if "positive" in text.lower(): extracted["sentiment"] = "Positive"
        elif "neutral" in text.lower(): extracted["sentiment"] = "Neutral"
        elif "negative" in text.lower(): extracted["sentiment"] = "Negative"

    # Follow-up Actions
    if not extracted.get("follow_up_actions"):
        match_follow_up = re.search(r"(?:follow-up actions?|next steps?|action items?)\s*(.*?)(?:\.|$)", text, re.IGNORECASE)
        if match_follow_up:
            extracted["follow_up_actions"] = match_follow_up.group(1).strip()
        elif "send publication" in text.lower(): # simple keyword
            extracted["follow_up_actions"] = "Send publication"
            
    return extracted


async def process_chat_with_langgraph_concept(user_message: str, chat_history: List[Dict[str, str]], current_extraction_data: Dict) -> ChatResponse:
    """
    Conceptual function simulating a LangGraph agent for chat interactions.
    LangGraph would define a graph of nodes (LLM calls, tool calls, conditional logic).
    """
    print(f"--- Conceptual LangGraph Processing ---")
    print(f"User Message: {user_message}")
    print(f"Chat History: {json.dumps(chat_history, indent=2)}")
    print(f"Current Extracted Data: {json.dumps(current_extraction_data, indent=2)}")
    print(f"------------------------------------")

    # 1. Combine current message with history for context (simplified)
    full_context_prompt = user_message
    # A real system would format this properly for the LLM.

    # 2. Call LLM (Groq gemma2-9b-it mocked) for NLU and response generation
    # LangGraph node: "understand_user_intent_and_extract"
    ai_raw_response = await call_groq_llm(full_context_prompt, model="gemma2-9b-it", chat_history=chat_history)

    # 3. Update extracted data based on LLM understanding (or direct extraction)
    # LangGraph node: "update_extracted_knowledge"
    # For this mock, we'll use our rudimentary extractor on the latest user message
    # and merge with existing data. An LLM could do this more intelligently.
    newly_extracted = extract_interaction_details_from_text(user_message, current_extraction_data)
    
    updated_extracted_data = {**current_extraction_data, **newly_extracted} # simple merge, LLM could be smarter

    # 4. Determine if interaction is complete and ready for logging
    # LangGraph node: "check_completeness_or_decide_next_step"
    is_complete_for_logging = False
    interaction_id_on_log = None

    required_fields = ["hcp_name", "interaction_date"] # Minimal for logging attempt
    all_fields_present = all(updated_extracted_data.get(field) for field in required_fields)

    if ("log it" in user_message.lower() or "yes" in user_message.lower() or "correct" in user_message.lower()) and all_fields_present:
        is_complete_for_logging = True
        ai_response_message = f"Okay, attempting to log the interaction with {updated_extracted_data.get('hcp_name', 'the HCP')}. One moment..."
        
        # Attempt to save to DB
        conn = get_db_connection()
        if not conn:
            return ChatResponse(ai_message="Error: Could not connect to the database to log interaction.", extracted_data=updated_extracted_data)
        
        cursor = conn.cursor()
        try:
            # Construct full chat log for storage
            full_chat_log_entries = chat_history + [{"role": "user", "content": user_message}, {"role": "assistant", "content": ai_response_message}]
            raw_chat_log_str = json.dumps(full_chat_log_entries)

            sql = """
                INSERT INTO hcp_interactions 
                (hcp_name, interaction_date, products_discussed, key_discussion_points, sentiment, follow_up_actions, interaction_method, raw_chat_log) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (
                updated_extracted_data.get("hcp_name"),
                updated_extracted_data.get("interaction_date"),
                updated_extracted_data.get("products_discussed"),
                updated_extracted_data.get("key_discussion_points"),
                updated_extracted_data.get("sentiment") if updated_extracted_data.get("sentiment") in ['Positive', 'Neutral', 'Negative'] else None,
                updated_extracted_data.get("follow_up_actions"),
                "chat",
                raw_chat_log_str
            )
            cursor.execute(sql, values)
            conn.commit()
            interaction_id_on_log = cursor.lastrowid
            ai_response_message = f"Successfully logged interaction (ID: {interaction_id_on_log}) with {updated_extracted_data.get('hcp_name', 'the HCP')}."
            # Reset extracted data after successful logging for a new interaction potentially
            updated_extracted_data = {} 
        except mysql.connector.Error as err:
            conn.rollback()
            print(f"DB Error logging chat interaction: {err}")
            ai_response_message = f"Error logging interaction to database: {err}"
            is_complete_for_logging = False # Keep it false so user might retry or clarify
        finally:
            cursor.close()
            conn.close()
    elif all_fields_present and not ("log it" in user_message.lower() or "yes" in user_message.lower()):
        # If we have key fields, confirm with user
        confirmation_details = []
        for key, val in updated_extracted_data.items():
            if val: confirmation_details.append(f"{key.replace('_', ' ').title()}: {val}")
        
        ai_response_message = f"Okay, I have the following details: {'; '.join(confirmation_details)}. Is this correct and shall I log it?"
    else:
        # Use the LLM's general response if not explicitly logging
        ai_response_message = ai_raw_response


    # 5. (Conceptual) LangGraph could use tools here, e.g., a calendar tool, or call another LLM (llama-3.3-70b-versatile) for complex summarization if needed.
    # For example: if 'gemma2-9b-it' response is vague, LangGraph could trigger a call to 'llama-3.3-70b-versatile' for deeper context analysis.
    # This is commented out as it's a conceptual step:
    # if "needs_deeper_analysis" in ai_raw_response_flags: # Fictional flag
    #     deeper_analysis_prompt = f"Original query: {user_message}. Context: {json.dumps(updated_extracted_data)}. Please provide a detailed understanding or summary."
    #     ai_response_message = await call_groq_llm(deeper_analysis_prompt, model="llama-3.3-70b-versatile") # Conceptual call

    return ChatResponse(
        ai_message=ai_response_message,
        is_complete=is_complete_for_logging,
        extracted_data=updated_extracted_data,
        interaction_id=interaction_id_on_log
    )

# --- FastAPI App Instance ---
app = FastAPI(title="AI-First CRM HCP Interaction Logger")

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], # Allows frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Endpoints ---
@app.on_event("startup")
async def startup_event():
    """Initializes the database when the application starts."""
    print("Application startup: Initializing database...")
    initialize_database()
    print("Database initialization complete.")

@app.post("/api/log_interaction_form", response_model=HCPInteractionOutput)
async def log_interaction_form_endpoint(interaction: HCPInteractionFormInput, request: Request):
    """Logs an interaction submitted via the structured form."""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database connection unavailable.")
    cursor = conn.cursor()
    try:
        # Optional: Process with AI for summarization/tagging if desired
        # For example, pass interaction.key_discussion_points to an AI summarizer
        # ai_summary = await process_text_with_ai(interaction.key_discussion_points, "summarize")

        sql = """
            INSERT INTO hcp_interactions 
            (hcp_name, interaction_date, products_discussed, key_discussion_points, sentiment, follow_up_actions, interaction_method) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            interaction.hcp_name,
            interaction.interaction_date,
            interaction.products_discussed,
            interaction.key_discussion_points,
            interaction.sentiment if interaction.sentiment in ['Positive', 'Neutral', 'Negative'] else None,
            interaction.follow_up_actions,
            "form"
        )
        cursor.execute(sql, values)
        conn.commit()
        interaction_id = cursor.lastrowid
        
        # Fetch the created record to return it (optional, but good practice)
        cursor.execute("SELECT * FROM hcp_interactions WHERE id = %s", (interaction_id,))
        new_interaction_record = cursor.fetchone()
        if not new_interaction_record:
             raise HTTPException(status_code=500, detail="Failed to retrieve interaction after saving.")

        # Map tuple to dict
        columns = [col[0] for col in cursor.description]
        created_interaction_dict = dict(zip(columns, new_interaction_record))
        
        return HCPInteractionOutput(**created_interaction_dict)

    except mysql.connector.Error as err:
        conn.rollback()
        print(f"Database error on form log: {err}")
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    except Exception as e:
        print(f"Unexpected error on form log: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
    finally:
        cursor.close()
        conn.close()

@app.post("/api/log_interaction_chat", response_model=ChatResponse)
async def log_interaction_chat_endpoint(chat_input: HCPInteractionChatInput, request: Request):
    """Handles a message from the chat interface and uses conceptual AI to process it."""
    
    # This is where the conceptual LangGraph flow is invoked.
    # It will try to understand the message, extract data, and decide on the next step.
    response = await process_chat_with_langgraph_concept(
        user_message=chat_input.message,
        chat_history=chat_input.history,
        current_extraction_data=chat_input.current_extraction_data or {}
    )
    return response

@app.get("/")
async def root():
    return {"message": "AI CRM Backend is running. Use /docs for API documentation."}

# To run (from backend_app directory): uvicorn main:app --reload --port 8000
