# --- START OF FILE core_logic.py ---

import sys, logging, time, re, asyncio, requests, json, os
import pathlib
import aiofiles
from collections import deque

# This file contains all platform-agnostic logic.
# It does NOT import any whatsapp or telegram libraries.

logger = logging.getLogger("OllamaWhatsAppAssistant")

# --- STATE MANAGEMENT ---
g_admin_config: dict = {}
CHAT_HISTORIES: dict[str, deque] = {}
ACTIVE_OUTREACH_CONVERSATIONS: dict[str, dict] = {}
PREPARED_OUTREACHES: dict[str, dict] = {}
USER_MESSAGE_BUFFERS: dict[str, list[str]] = {}
USER_MESSAGE_TIMERS: dict[str, asyncio.Task] = {}
LAST_DISPLAYED_LISTS: dict[str, dict] = {}
g_next_prepared_id_counter: int = 1
g_outreach_prompts: dict[str, str] = {} # Loaded from a separate file for now

# Helper globals populated from g_admin_config
g_ollama_model_name: str = ""
g_max_chat_history_turns: int = 0
g_ollama_model_options: dict = {}
g_ollama_chat_endpoint: str = ""
g_ollama_request_timeout: int = 120
g_command_prefix: str = "$"
KNOWLEDGE_FILE_PATH: str = ""
ADMIN_CONFIG_FILE_PATH: str = "" # Set at startup

# --- KNOWLEDGE & CONFIG ---

def get_default_admin_config() -> dict:
    """Returns a dictionary with default admin configurations."""
    return {
        "admin_ids": {
            "whatsapp": "YOUR_WHATSAPP_NUMBER@c.us",
            "telegram": 123456789
        },
        "telegram_settings": {
            "bot_token": "YOUR_TELEGRAM_BOT_TOKEN_HERE"
        },
        "ai_is_active": True,
        "ai_toggle_passphrase": "ddont sspeak",
        "message_aggregation_delay_seconds": 10.0,
        "fixed_pre_ai_response_message": "<<<النص مولد عن طريق الذكاء الاصطناعي>>>",
        "fixed_post_ai_response_message": "<<<<(الخدمة قيد التطوير)>>>>",
        "ai_persona_prefix_message": "",
        "knowledge_file_path": "./hosam_knowledge_arabic.txt",
        "outreach_prompts_file_path": "./outreach_prompts.json",
        "interaction_logs_dir": "./interaction_logs/",
        "ollama_api_base_url": "http://localhost:11434",
        "ollama_model_name": "gemma3:4b",
        "ollama_request_timeout_seconds": 120,
        "max_chat_history_turns": 20,
        "ollama_model_options": {
            "num_ctx": 4096, "temperature": 0.4, "top_k": 40, "top_p": 0.9, "repeat_penalty": 1.1
        },
        "command_prefix": "$",
        "outreach_settings": { "notify_admin_on_reply": True, "approval_mode": "FIRST_ONLY" },
        "reactive_roles": {
            "default_assistant": "أنت مساعد آلي لوكالة إعلانات. مهمتك هي تقديم معلومات حول خدماتنا وأسعارنا. رد باللغة العربية."
        },
        "active_reactive_role": "default_assistant",
        "ai_goals": {},
        "active_goals": [],
        "ai_interaction_style": "friendly_professional",
        "gdrive_config_url": ""
    }

def load_admin_config(config_path: str):
    """Loads admin configurations from JSON file and updates globals."""
    global g_admin_config, g_ollama_model_name, g_max_chat_history_turns, g_ollama_model_options
    global g_ollama_chat_endpoint, g_ollama_request_timeout, g_command_prefix, KNOWLEDGE_FILE_PATH
    global ADMIN_CONFIG_FILE_PATH

    ADMIN_CONFIG_FILE_PATH = config_path
    defaults = get_default_admin_config()
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                g_admin_config = defaults.copy()
                g_admin_config.update(loaded_config) # Shallow merge is ok for top level
                for key in defaults: # Deep merge for nested dicts
                    if isinstance(defaults[key], dict) and key in loaded_config:
                        g_admin_config[key] = {**defaults[key], **loaded_config[key]}
                logger.info("Admin config loaded successfully from '%s'.", config_path)
        except (json.JSONDecodeError, Exception) as e:
            logger.error("Error loading admin config from '%s': %s. Using defaults.", config_path, e)
            g_admin_config = defaults
            save_admin_config()
    else:
        logger.info("Admin config file '%s' not found. Creating with defaults.", config_path)
        g_admin_config = defaults
        save_admin_config()

    KNOWLEDGE_FILE_PATH = g_admin_config.get("knowledge_file_path")
    ollama_base_url = g_admin_config.get("ollama_api_base_url")
    g_ollama_chat_endpoint = f"{ollama_base_url}/api/chat"
    g_ollama_model_name = g_admin_config.get("ollama_model_name")
    g_ollama_request_timeout = g_admin_config.get("ollama_request_timeout_seconds")
    g_max_chat_history_turns = g_admin_config.get("max_chat_history_turns")
    g_ollama_model_options = g_admin_config.get("ollama_model_options")
    g_command_prefix = g_admin_config.get("command_prefix")
    load_outreach_prompts_file() # Load outreach prompts using path from config

def save_admin_config():
    """Saves the current g_admin_config dictionary to the JSON file."""
    try:
        with open(ADMIN_CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(g_admin_config, f, indent=2, ensure_ascii=False)
        logger.info("Admin config saved successfully to '%s'.", ADMIN_CONFIG_FILE_PATH)
    except Exception as e:
        logger.error("Error saving admin config to '%s': %s", ADMIN_CONFIG_FILE_PATH, e)

def load_knowledge_from_file() -> str:
    """Loads knowledge content from the file path specified in the config."""
    filepath = KNOWLEDGE_FILE_PATH
    if not filepath or not os.path.exists(filepath): return ""
    try:
        with open(filepath, 'r', encoding='utf-8') as f: return f.read().strip()
    except Exception as e:
        logger.error("Knowledge loader: Error reading file '%s': %s", filepath, e)
        return ""

def load_outreach_prompts_file():
    """Loads outreach prompts from the file path specified in the config."""
    global g_outreach_prompts
    filepath = g_admin_config.get("outreach_prompts_file_path")
    if not filepath or not os.path.exists(filepath):
        g_outreach_prompts = {}
        return
    try:
        with open(filepath, 'r', encoding='utf-8') as f: g_outreach_prompts = json.load(f)
    except Exception as e:
        logger.error("Error loading outreach prompts from '%s': %s", filepath, e)
        g_outreach_prompts = {}

def save_outreach_prompts_file():
    """Saves outreach prompts to the file path specified in the config."""
    filepath = g_admin_config.get("outreach_prompts_file_path")
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(g_outreach_prompts, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error("Error saving outreach prompts to '%s': %s", filepath, e)

# --- OLLAMA INTERACTION ---
# (This function remains largely the same as before)
def query_ollama_chat(chat_id: str, user_prompt_text: str, knowledge_content: str, custom_system_prompt: str = None, specific_chat_history_deque: deque = None) -> str:
    """Queries Ollama. Returns AI's response string or an error message string."""
    base_system_prompt = g_admin_config.get("base_system_prompt_arabic", "")
    system_prompt_to_use = custom_system_prompt or base_system_prompt

    history_deque_to_update: deque
    is_outreach_context = specific_chat_history_deque is not None

    if is_outreach_context:
        history_deque_to_update = specific_chat_history_deque
    else:
        standard_maxlen = g_max_chat_history_turns * 2 if g_max_chat_history_turns > 0 else None
        if chat_id not in CHAT_HISTORIES:
            CHAT_HISTORIES[chat_id] = deque(maxlen=standard_maxlen)
        elif CHAT_HISTORIES[chat_id].maxlen != standard_maxlen:
            existing = list(CHAT_HISTORIES[chat_id])
            CHAT_HISTORIES[chat_id] = deque(existing, maxlen=standard_maxlen)
        history_deque_to_update = CHAT_HISTORIES[chat_id]

    effective_system_prompt = system_prompt_to_use
    if knowledge_content:
        effective_system_prompt = (
            f"المعلومات الأساسية وقاعدة المعرفة العامة:\n---\n{knowledge_content}\n---\n\n"
            f"مهمتك وتعليماتك الخاصة:\n{system_prompt_to_use}"
        )

    messages_payload_for_api = [{"role": "system", "content": effective_system_prompt}]
    messages_payload_for_api.extend(list(history_deque_to_update))
    messages_payload_for_api.append({"role": "user", "content": user_prompt_text})

    api_payload = { "model": g_ollama_model_name, "messages": messages_payload_for_api, "options": g_ollama_model_options, "stream": False }

    try:
        response = requests.post(g_ollama_chat_endpoint, json=api_payload, timeout=g_ollama_request_timeout)
        response.raise_for_status()
        response_data = response.json()
        assistant_response_text = response_data.get("message", {}).get("content", "").strip()

        if assistant_response_text:
            history_deque_to_update.append({"role": "user", "content": user_prompt_text})
            history_deque_to_update.append({"role": "assistant", "content": assistant_response_text})
            return assistant_response_text
        else:
            logger.error("Ollama chat: 'message.content' key not found in response: %s", response_data)
            return "خطأ: لم يتمكن مساعد الذكاء الاصطناعي من إنشاء رد صالح حاليًا."
    except requests.exceptions.Timeout:
        logger.error("Ollama chat: Request timed out after %d seconds.", g_ollama_request_timeout)
        return "خطأ: استغرق مساعد الذكاء الاصطناعي وقتًا طويلاً جدًا للرد."
    except Exception as e:
        logger.error("Ollama chat: Unexpected error during query: %s", e, exc_info=True)
        return "خطأ: حدثت مشكلة غير متوقعة أثناء معالجة طلبك."

# --- ADMIN COMMAND LOGIC ---
# (The full handle_admin_command function is moved here, returning strings instead of sending messages)
async def handle_admin_command(platform: str, chat_id: str, command_text: str) -> dict:
    # Logic returns a dictionary now: {'reply_text': str, 'platform_actions': list}
    # Platform actions can be {'action': 'restart_whatsapp'}
    
    global g_admin_config, LAST_DISPLAYED_LISTS, PREPARED_OUTREACHES, ACTIVE_OUTREACH_CONVERSATIONS
    global g_next_prepared_id_counter, g_outreach_prompts

    command_body = command_text[len(g_command_prefix):].strip()
    parts = command_body.split(" ", 1)
    command = parts[0].lower()
    args_str = parts[1].strip() if len(parts) > 1 else ""
    
    reply_message = f"Admin command '{command}' acknowledged."
    config_changed = False
    platform_actions = []

    # Browser/WPP Client Control Commands
    if command == "closebrowser":
        platform_actions.append({'action': 'close_whatsapp'})
        reply_message = "Attempting to close WhatsApp browser/WPP connection..."
    
    elif command == "openbrowser" or command == "restartbrowser":
        platform_actions.append({'action': 'restart_whatsapp'})
        reply_message = f"Attempting to {command} WhatsApp browser/WPP connection..."

    # ... (All other command logic from your AIaspects.py would be ported here)
    # For now, let's keep a few examples:
    elif command == "aistatus":
        ai_is_active = g_admin_config.get("ai_is_active", False)
        reply_message = f"Reactive AI is {'ACTIVE (ON)' if ai_is_active else 'INACTIVE (OFF)'}."
    
    elif command == "setmodel":
        model_to_set = args_str.strip() # Simplified for this example
        if model_to_set:
            g_admin_config["ollama_model_name"] = model_to_set
            config_changed = True
            reply_message = f"Ollama model set to '{model_to_set}'."
        else:
            reply_message = "Usage: $setmodel <model_name>"

    else:
        reply_message = f"Unknown admin command: '{command}'. Try {g_command_prefix}help."

    if config_changed:
        save_admin_config()
        load_admin_config(ADMIN_CONFIG_FILE_PATH)

    return {'reply_text': reply_message, 'platform_actions': platform_actions}


# --- MESSAGE PROCESSING LOGIC ---
# (The full process_aggregated_messages logic is moved and refactored here)
async def process_message(platform: str, chat_id: str, sender_name: str, message_text: str) -> list[dict]:
    """
    Main entry point for processing any message from any platform.
    Returns a list of messages to be sent back. Each message is a dict:
    {'target_id': str, 'text': str, 'platform_actions': list}
    """
    replies = []
    
    # Check if this user ID is an admin for this platform
    user_is_admin = str(g_admin_config.get("admin_ids", {}).get(platform)) == str(chat_id)

    # 1. Handle Admin Commands
    if user_is_admin and message_text.startswith(g_command_prefix):
        response_dict = await handle_admin_command(platform, chat_id, message_text)
        replies.append({
            'target_id': chat_id, 
            'text': response_dict['reply_text'],
            'platform_actions': response_dict['platform_actions']
        })
        return replies

    # 2. Handle AI Toggle
    toggle_pass = g_admin_config.get("ai_toggle_passphrase")
    if message_text.strip().lower() == toggle_pass.lower():
        current_state = g_admin_config.get("ai_is_active")
        g_admin_config["ai_is_active"] = not current_state
        save_admin_config()
        reply_text = f"المساعد الآلي الآن {'يعمل (نشط)' if not current_state else 'متوقف (غير نشط)'}."
        replies.append({'target_id': chat_id, 'text': reply_text, 'platform_actions': []})
        return replies

    # 3. Check for Active Outreach Reply
    if chat_id in ACTIVE_OUTREACH_CONVERSATIONS and ACTIVE_OUTREACH_CONVERSATIONS[chat_id].get("is_active"):
        outreach_data = ACTIVE_OUTREACH_CONVERSATIONS[chat_id]
        ai_response = query_ollama_chat(
            chat_id, message_text, "", 
            custom_system_prompt=outreach_data["system_prompt"],
            specific_chat_history_deque=outreach_data["history"]
        )
        replies.append({'target_id': chat_id, 'text': ai_response, 'platform_actions': []})
        return replies

    # 4. Handle Reactive Chat
    if g_admin_config.get("ai_is_active"):
        knowledge = load_knowledge_from_file()
        
        # Build effective system prompt (roles, goals, style)
        active_role_key = g_admin_config.get("active_reactive_role", "default_assistant")
        role_prompt = g_admin_config.get("reactive_roles", {}).get(active_role_key, "")
        # ... more logic here to add goals and style to the prompt ...
        
        ai_response = query_ollama_chat(chat_id, message_text, knowledge, custom_system_prompt=role_prompt)
        
        # Assemble final reply with pre/post messages
        final_reply = []
        if g_admin_config.get("fixed_pre_ai_response_message"):
            final_reply.append(g_admin_config.get("fixed_pre_ai_response_message"))
        final_reply.append(ai_response)
        if g_admin_config.get("fixed_post_ai_response_message"):
            final_reply.append(g_admin_config.get("fixed_post_ai_response_message"))
        
        replies.append({'target_id': chat_id, 'text': "\n".join(final_reply), 'platform_actions': []})

    return replies

# --- UTILITY HELPERS ---
# (sanitize_filename, _get_item_from_numbered_list, log_interaction_turn would also be ported here)

# --- END OF FILE core_logic.py ---