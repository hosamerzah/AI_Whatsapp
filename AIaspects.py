# --- START OF MODIFIED Outreach.py ---

# -----------------------------------------------------------------------------
# WPP_Ollama_Chat_Assistant_V_ROADMAP_Outreach_Part1_Integrate
#
# Description:
# - Script Header, Imports, Core Configuration Constants.
# - NEW: Paths for admin config and interaction logs.
# - NEW: Import aiofiles.
#
# Version: ROADMAP_INTEGRATION_P1
# -----------------------------------------------------------------------------

print("WPP_Ollama_Chat_Assistant_V_ROADMAP_Outreach_Part1_Integrate: Script execution begins.")
import sys, logging, time, re, asyncio, requests, json, os
import pathlib # NEW: For easier path manipulation
import aiofiles # NEW: For asynchronous file I/O
from collections import deque
try:
    from WPP_Whatsapp import Create
    print("WPP_Ollama_Chat_Assistant_V_ROADMAP_Outreach_Part1_Integrate: WPP_Whatsapp.Create imported.")
except ImportError as e: print(f"CRITICAL IMPORT ERROR for WPP_Whatsapp: {e}"); sys.exit(1)
except Exception as e: print(f"CRITICAL GENERIC IMPORT ERROR for WPP_Whatsapp: {e}"); sys.exit(1)

# -----------------------------------------------------------------------------
# --- ⚙️ CONFIGURATION SECTION (MOSTLY UNCHANGED, DEFAULTS FOR NEW CONFIG FILE) ⚙️ ---
# Some of these will become defaults if not found in admin_config.json
# -----------------------------------------------------------------------------

# --- WhatsApp Connection Settings ---
YOUR_SESSION_NAME: str = "listener_test_session_v4" # Consider a new session name
WPP_HEADLESS_MODE: bool = False

# --- Headless Browser Arguments ---
WPP_HEADLESS_BROWSER_ARGS: list[str] = [
    '--no-sandbox', '--disable-setuid-sandbox', '--disable-infobars',
    '--disable-dev-shm-usage', '--disable-browser-side-navigation', '--disable-gpu',
    '--disable-features=site-per-process', '--window-size=1920,1080',
    '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    '--disable-blink-features=AutomationControlled', '--lang=en-US,en;q=0.9',
]

# --- Ollama LLM Settings (Defaults for admin_config.json) ---
DEFAULT_OLLAMA_API_BASE_URL: str = "http://localhost:11434"
DEFAULT_OLLAMA_CHAT_ENDPOINT: str = f"{DEFAULT_OLLAMA_API_BASE_URL}/api/chat"
DEFAULT_OLLAMA_MODEL_NAME: str = "gemma3:4b"
DEFAULT_OLLAMA_REQUEST_TIMEOUT_SECONDS: int = 1200000

# --- AI Behavior Settings (Defaults for admin_config.json) ---
DEFAULT_AI_TOGGLE_PASSPHRASE: str = "ddont sspeak"
DEFAULT_AI_STARTS_ACTIVE: bool = True
DEFAULT_MESSAGE_AGGREGATION_DELAY_SECONDS: float = 10.0

# --- Fixed Response Messages (Defaults for admin_config.json) ---
DEFAULT_FIXED_PRE_AI_RESPONSE_MESSAGE: str = "<<<النص مولد عن طريق الذكاء الاصطناعي>>>"
DEFAULT_FIXED_POST_AI_RESPONSE_MESSAGE: str = "<<<<(الخدمة قيد التطوير)>>>>"
DEFAULT_AI_PERSONA_PREFIX_MESSAGE: str = "" # e.g., "مساعد أحمد الرقمي يقول: " 

# --- System Prompt and Knowledge Base (Knowledge path remains, system prompt in config) ---
DEFAULT_AI_SYSTEM_PROMPT_ARABIC: str = ("أنت مساعد آلي لوكالة إعلانات بسطويسي واولاده ماعدا الابن العاق حمني. موظفونا غير متوفرين حاليًا."
"مهمتك هي تقديم معلومات حول خدماتنا وأسعارنا بناءً على قاعدة البيانات المقدمه لك فقط."
"الرجاء الرد باللغة العربية. إذا كان السؤال خارج نطاق المعلومات المتوفرة، أجب بأدب أنك لا تملك المعلومة."
"لا تقدم أي معلومات غير موجودة في قاعدة المعرفة."
"إذا كان السؤال يتعلق بموضوعات خارج نطاق خدماتنا، أجب بأدب أنك لا تستطيع المساعدة في ذلك."
)
KNOWLEDGE_FILE_PATH: str = "./hosam_knowledge_arabic.txt" # This can also be moved to config if desired

# --- Initial AI Context & Model Parameter Settings (Defaults for admin_config.json) ---
DEFAULT_INITIAL_MAX_CHAT_HISTORY_TURNS: int = 20
DEFAULT_INITIAL_OLLAMA_MODEL_OPTIONS: dict = {
    "num_ctx": 4096,
    "temperature": 0.4,
    "top_k": 40,
    "top_p": 0.9,
    "repeat_penalty": 1.1
}

# --- Logging Settings ---
SCRIPT_LOG_LEVEL = logging.DEBUG
WPP_LIB_LOG_LEVEL = logging.INFO

# --- Admin and Command Configuration (Admin ID critical, prefix default for config) ---
ADMIN_CHAT_ID: str = "967774361616@c.us"  # <<< CRITICAL: Set your WhatsApp number
DEFAULT_COMMAND_PREFIX: str = "$"
DEFAULT_MAX_INTERACTION_LOG_SIZE: int = 20 # For the in-memory INTERACTION_LOG deque

# --- Reconnection Settings ---
MAX_RECONNECTION_ATTEMPTS: int = 5
INITIAL_RECONNECTION_DELAY_SECONDS: int = 20
RECONNECTION_DELAY_MULTIPLIER: float = 1.5
MAX_RECONNECTION_DELAY_SECONDS: int = 180

# --- NEW: Paths for Persistent Data ---
ADMIN_CONFIG_FILE_PATH: str = "./admin_config.json"
INTERACTION_LOGS_DIR: str = "./interaction_logs/" # Directory for .jsonl chat logs
OUTREACH_PROMPTS_FILE: str = "./outreach_prompts.json" # Retained for existing outreach prompt management

# -----------------------------------------------------------------------------
# --- END OF CONFIGURATION SECTION (PART 1 MODIFIED) ---
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Part 2: Global Variables and Logger Setup
# - NEW: g_admin_config, PREPARED_OUTREACHES, LAST_DISPLAYED_LISTS
# - Modified: Globals for AI settings will now be populated from g_admin_config
# -----------------------------------------------------------------------------
print("WPP_Ollama_Chat_Assistant_V_ROADMAP_Outreach_Part2_Integrate: Initializing globals and logger.")
wpp_client = None
MAIN_EVENT_LOOP = None

# --- NEW: Global dictionary for all admin-configurable settings ---
g_admin_config: dict = {}

# --- Globals that will be populated from g_admin_config at startup ---
# These act as placeholders until load_admin_config is called.
AI_IS_ACTIVE: bool = DEFAULT_AI_STARTS_ACTIVE
g_ai_toggle_passphrase: str = DEFAULT_AI_TOGGLE_PASSPHRASE
g_message_aggregation_delay: float = DEFAULT_MESSAGE_AGGREGATION_DELAY_SECONDS
g_fixed_pre_ai_response_message: str = DEFAULT_FIXED_PRE_AI_RESPONSE_MESSAGE
g_fixed_post_ai_response_message: str = DEFAULT_FIXED_POST_AI_RESPONSE_MESSAGE
g_ai_persona_prefix_message: str = DEFAULT_AI_PERSONA_PREFIX_MESSAGE
g_system_prompt: str = DEFAULT_AI_SYSTEM_PROMPT_ARABIC # Base system prompt
g_ollama_api_base_url: str = DEFAULT_OLLAMA_API_BASE_URL
g_ollama_chat_endpoint: str = DEFAULT_OLLAMA_CHAT_ENDPOINT
g_ollama_model_name: str = DEFAULT_OLLAMA_MODEL_NAME
g_ollama_request_timeout: int = DEFAULT_OLLAMA_REQUEST_TIMEOUT_SECONDS
g_max_chat_history_turns: int = DEFAULT_INITIAL_MAX_CHAT_HISTORY_TURNS
g_ollama_model_options: dict = DEFAULT_INITIAL_OLLAMA_MODEL_OPTIONS.copy()
g_command_prefix: str = DEFAULT_COMMAND_PREFIX
g_max_interaction_log_size: int = DEFAULT_MAX_INTERACTION_LOG_SIZE # For in-memory deque

# --- Chat Histories and Buffers (Remain in-memory for performance) ---
CHAT_HISTORIES: dict[str, deque] = {}
USER_MESSAGE_BUFFERS: dict[str, list[str]] = {}
USER_MESSAGE_TIMERS: dict[str, asyncio.Task] = {}
INTERACTION_LOG: deque = deque(maxlen=g_max_interaction_log_size) # In-memory quick log

# --- Outreach Related Globals ---
g_outreach_prompts: dict[str, str] = {} # Loaded from outreach_prompts.json
ACTIVE_OUTREACH_CONVERSATIONS: dict[str, dict] = {} # For active, ongoing outreach
PREPARED_OUTREACHES: dict[str, dict] = {} # NEW: For outreach awaiting admin approval {prepared_id: details}
g_next_prepared_id_counter: int = 1 # NEW: To generate unique prepared_id

# --- Admin Command Helper ---
LAST_DISPLAYED_LISTS: dict[str, dict] = {} # NEW: For numbered command interaction {list_key: {number: item_id}}

try:
    logger = logging.getLogger("OllamaWhatsAppAssistant")
    logger.setLevel(SCRIPT_LOG_LEVEL)
    console_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)')
    console_handler.setFormatter(formatter)
    if not logger.handlers: logger.addHandler(console_handler)
    logger.propagate = False
    logging.getLogger("WPP_Whatsapp").setLevel(WPP_LIB_LOG_LEVEL)
    logger.info("Logger setup complete. Application log level: %s", logging.getLevelName(logger.level))
except Exception as e_log_setup: print(f"CRITICAL ERROR: Logger setup failed: {e_log_setup}"); sys.exit(1)
# --- END OF GLOBAL VARIABLES AND LOGGER SETUP (PART 2 MODIFIED) ---

# -----------------------------------------------------------------------------
# Part 10 (Outreach Prompt Management - from original script) - Keep as is for now
# We might integrate outreach_prompts into admin_config.json later.
# -----------------------------------------------------------------------------
print("WPP_Ollama_Chat_Assistant_V_ROADMAP_Outreach_Part10_Integrate: Defining outreach prompt management.")
def load_outreach_prompts_file(): # Renamed to avoid conflict if we make a generic loader
    global g_outreach_prompts
    if os.path.exists(OUTREACH_PROMPTS_FILE):
        try:
            with open(OUTREACH_PROMPTS_FILE, 'r', encoding='utf-8') as f:
                loaded_prompts = json.load(f)
                if isinstance(loaded_prompts, dict):
                    g_outreach_prompts = loaded_prompts
                    logger.info("Outreach Prompt Mgmt: Successfully loaded %d outreach prompts from '%s'.",
                                len(g_outreach_prompts), OUTREACH_PROMPTS_FILE)
                else:
                    logger.error("Outreach Prompt Mgmt: Content of '%s' is not a dictionary. Using empty prompts.", OUTREACH_PROMPTS_FILE)
                    g_outreach_prompts = {}
        except json.JSONDecodeError:
            logger.error("Outreach Prompt Mgmt: Error decoding JSON from '%s'. Using empty prompts.", OUTREACH_PROMPTS_FILE)
            g_outreach_prompts = {}
        except Exception as e_load:
            logger.error("Outreach Prompt Mgmt: Error loading outreach prompts from '%s': %s", OUTREACH_PROMPTS_FILE, e_load)
            g_outreach_prompts = {}
    else:
        logger.info("Outreach Prompt Mgmt: Outreach prompts file '%s' not found. Starting with no custom outreach prompts.", OUTREACH_PROMPTS_FILE)
        g_outreach_prompts = {}

def save_outreach_prompts_file(): # Renamed
    global g_outreach_prompts
    try:
        with open(OUTREACH_PROMPTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(g_outreach_prompts, f, indent=2, ensure_ascii=False)
        logger.info("Outreach Prompt Mgmt: Successfully saved %d outreach prompts to '%s'.",
                    len(g_outreach_prompts), OUTREACH_PROMPTS_FILE)
    except Exception as e_save:
        logger.error("Outreach Prompt Mgmt: Error saving outreach prompts to '%s': %s", OUTREACH_PROMPTS_FILE, e_save)
# --- END OF OUTREACH PROMPT MANAGEMENT FUNCTIONS (PART 10 MODIFIED SLIGHTLY) ---


# -----------------------------------------------------------------------------
# Part 3: Core Helper Functions
# - NEW: load_admin_config, save_admin_config
# - NEW: sanitize_filename, log_interaction_turn
# - NEW: _get_item_from_numbered_list (admin helper)
# - Knowledge loader remains. WPP helpers remain.
# -----------------------------------------------------------------------------
print("WPP_Ollama_Chat_Assistant_V_ROADMAP_Outreach_Part3_Integrate: Defining core helper functions.")

def get_default_admin_config() -> dict:
    """Returns a dictionary with default admin configurations."""
    return {
        "ai_is_active": DEFAULT_AI_STARTS_ACTIVE,
        "ai_toggle_passphrase": DEFAULT_AI_TOGGLE_PASSPHRASE,
        "message_aggregation_delay_seconds": DEFAULT_MESSAGE_AGGREGATION_DELAY_SECONDS,
        "fixed_pre_ai_response_message": DEFAULT_FIXED_PRE_AI_RESPONSE_MESSAGE,
        "fixed_post_ai_response_message": DEFAULT_FIXED_POST_AI_RESPONSE_MESSAGE,
        "ai_persona_prefix_message": DEFAULT_AI_PERSONA_PREFIX_MESSAGE,
        "base_system_prompt_arabic": DEFAULT_AI_SYSTEM_PROMPT_ARABIC, # This will be combined with role prompts
        "ollama_api_base_url": DEFAULT_OLLAMA_API_BASE_URL,
        # "ollama_chat_endpoint" will be derived from base_url
        "ollama_model_name": DEFAULT_OLLAMA_MODEL_NAME,
        "ollama_request_timeout_seconds": DEFAULT_OLLAMA_REQUEST_TIMEOUT_SECONDS,
        "max_chat_history_turns": DEFAULT_INITIAL_MAX_CHAT_HISTORY_TURNS,
        "ollama_model_options": DEFAULT_INITIAL_OLLAMA_MODEL_OPTIONS.copy(),
        "command_prefix": DEFAULT_COMMAND_PREFIX,
        "max_interaction_log_size": DEFAULT_MAX_INTERACTION_LOG_SIZE, # For in-memory deque
        "outreach_settings": {
            "notify_admin_on_reply": True,
            "approval_mode": "FIRST_ONLY" # Or "ALL_REPLIES"
        },
        "reactive_roles": { # Example structure, admin will add more
            "default_assistant": DEFAULT_AI_SYSTEM_PROMPT_ARABIC # Initial default role
        },
        "active_reactive_role": "default_assistant",
        "ai_goals": {}, # Example: {"goal_key": "instruction"}
        "active_goals": [],
        "ai_interaction_style": "friendly_professional", # Default style key or custom string
        # Add more settings as needed
    }

def load_admin_config():
    """Loads admin configurations from JSON file into g_admin_config and updates relevant globals."""
    global g_admin_config, AI_IS_ACTIVE, g_ai_toggle_passphrase, g_message_aggregation_delay
    global g_fixed_pre_ai_response_message, g_fixed_post_ai_response_message, g_ai_persona_prefix_message
    global g_system_prompt, g_ollama_api_base_url, g_ollama_chat_endpoint, g_ollama_model_name
    global g_ollama_request_timeout, g_max_chat_history_turns, g_ollama_model_options
    global g_command_prefix, g_max_interaction_log_size, INTERACTION_LOG

    defaults = get_default_admin_config()
    if os.path.exists(ADMIN_CONFIG_FILE_PATH):
        try:
            with open(ADMIN_CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                # Merge loaded config with defaults to ensure all keys are present
                g_admin_config = {**defaults, **loaded_config}
                # Ensure nested dictionaries are also merged, e.g., ollama_model_options
                if 'ollama_model_options' in loaded_config and isinstance(loaded_config['ollama_model_options'], dict):
                    g_admin_config['ollama_model_options'] = {**defaults['ollama_model_options'], **loaded_config['ollama_model_options']}
                if 'outreach_settings' in loaded_config and isinstance(loaded_config['outreach_settings'], dict):
                    g_admin_config['outreach_settings'] = {**defaults['outreach_settings'], **loaded_config['outreach_settings']}

                logger.info("Admin config loaded successfully from '%s'.", ADMIN_CONFIG_FILE_PATH)
        except json.JSONDecodeError:
            logger.error("Error decoding JSON from '%s'. Using default configurations and attempting to save.", ADMIN_CONFIG_FILE_PATH)
            g_admin_config = defaults
            save_admin_config() # Save defaults if file is corrupt
        except Exception as e:
            logger.error("Error loading admin config from '%s': %s. Using default configurations.", ADMIN_CONFIG_FILE_PATH, e)
            g_admin_config = defaults
    else:
        logger.info("Admin config file '%s' not found. Creating with default configurations.", ADMIN_CONFIG_FILE_PATH)
        g_admin_config = defaults
        save_admin_config()

    # Populate global variables from the loaded/defaulted g_admin_config
    AI_IS_ACTIVE = g_admin_config.get("ai_is_active", DEFAULT_AI_STARTS_ACTIVE)
    g_ai_toggle_passphrase = g_admin_config.get("ai_toggle_passphrase", DEFAULT_AI_TOGGLE_PASSPHRASE)
    g_message_aggregation_delay = g_admin_config.get("message_aggregation_delay_seconds", DEFAULT_MESSAGE_AGGREGATION_DELAY_SECONDS)
    g_fixed_pre_ai_response_message = g_admin_config.get("fixed_pre_ai_response_message", DEFAULT_FIXED_PRE_AI_RESPONSE_MESSAGE)
    g_fixed_post_ai_response_message = g_admin_config.get("fixed_post_ai_response_message", DEFAULT_FIXED_POST_AI_RESPONSE_MESSAGE)
    g_ai_persona_prefix_message = g_admin_config.get("ai_persona_prefix_message", DEFAULT_AI_PERSONA_PREFIX_MESSAGE)
    
    # System prompt construction will be more dynamic later with roles
    active_role_key = g_admin_config.get("active_reactive_role", "default_assistant")
    g_system_prompt = g_admin_config.get("reactive_roles", {}).get(active_role_key, DEFAULT_AI_SYSTEM_PROMPT_ARABIC)

    g_ollama_api_base_url = g_admin_config.get("ollama_api_base_url", DEFAULT_OLLAMA_API_BASE_URL)
    g_ollama_chat_endpoint = f"{g_ollama_api_base_url}/api/chat" # Derived
    g_ollama_model_name = g_admin_config.get("ollama_model_name", DEFAULT_OLLAMA_MODEL_NAME)
    g_ollama_request_timeout = g_admin_config.get("ollama_request_timeout_seconds", DEFAULT_OLLAMA_REQUEST_TIMEOUT_SECONDS)
    g_max_chat_history_turns = g_admin_config.get("max_chat_history_turns", DEFAULT_INITIAL_MAX_CHAT_HISTORY_TURNS)
    g_ollama_model_options = g_admin_config.get("ollama_model_options", DEFAULT_INITIAL_OLLAMA_MODEL_OPTIONS.copy())
    g_command_prefix = g_admin_config.get("command_prefix", DEFAULT_COMMAND_PREFIX)
    
    new_max_log_size = g_admin_config.get("max_interaction_log_size", DEFAULT_MAX_INTERACTION_LOG_SIZE)
    if INTERACTION_LOG.maxlen != new_max_log_size:
        logger.info("Updating in-memory INTERACTION_LOG maxlen from %s to %s", INTERACTION_LOG.maxlen, new_max_log_size)
        current_log_items = list(INTERACTION_LOG)
        INTERACTION_LOG = deque(current_log_items, maxlen=new_max_log_size)
    g_max_interaction_log_size = new_max_log_size


def save_admin_config():
    """Saves the current g_admin_config dictionary to the JSON file."""
    global g_admin_config
    try:
        # Ensure base URL is saved, endpoint is derived
        if 'ollama_chat_endpoint' in g_admin_config:
            del g_admin_config['ollama_chat_endpoint'] # Should not be saved as it's derived

        with open(ADMIN_CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(g_admin_config, f, indent=2, ensure_ascii=False)
        logger.info("Admin config saved successfully to '%s'.", ADMIN_CONFIG_FILE_PATH)
    except Exception as e:
        logger.error("Error saving admin config to '%s': %s", ADMIN_CONFIG_FILE_PATH, e)

def sanitize_filename(name: str) -> str:
    """Sanitizes a string to be used as a filename or directory name."""
    # Remove common problematic characters for filenames
    # Keep alphanumeric, underscore, hyphen. Replace others.
    name = re.sub(r'[^\w\-\.]', '_', name)
    # Remove leading/trailing underscores/dots that might cause issues
    name = name.strip('._')
    return name if name else "unnamed_chat"

async def log_interaction_turn(chat_id: str, interaction_type: str, turn_data: dict):
    """
    Asynchronously logs an interaction turn to a .jsonl file.
    interaction_type: "outreach" or "reactive"
    turn_data: dict containing timestamp, role, content, and other relevant metadata.
    """
    if not chat_id:
        logger.warning("Log interaction: chat_id is empty, cannot log turn.")
        return

    sanitized_chat_id = sanitize_filename(chat_id)
    log_dir_path = pathlib.Path(INTERACTION_LOGS_DIR)
    user_log_dir_path = log_dir_path / sanitized_chat_id

    try:
        # Create base logs directory if it doesn't exist
        if not await asyncio.to_thread(log_dir_path.is_dir):
            await asyncio.to_thread(log_dir_path.mkdir, parents=True, exist_ok=True)
            logger.info("Created interaction logs directory: %s", log_dir_path)

        # Create user-specific log directory if it doesn't exist
        if not await asyncio.to_thread(user_log_dir_path.is_dir):
            await asyncio.to_thread(user_log_dir_path.mkdir, parents=True, exist_ok=True)
            logger.info("Created user log directory: %s", user_log_dir_path)

        log_file_name = f"{interaction_type}_history.jsonl"
        log_file_path = user_log_dir_path / log_file_name

        # Ensure essential fields are in turn_data
        if "timestamp_iso" not in turn_data:
            turn_data["timestamp_iso"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        if "role" not in turn_data:
            turn_data["role"] = "unknown"
        if "content" not in turn_data:
            turn_data["content"] = ""

        # Add llm model and other context if available globally (or pass them in turn_data)
        turn_data.setdefault("llm_model_used", g_ollama_model_name)
        # turn_data.setdefault("system_prompt_key_active", g_admin_config.get("active_reactive_role"))
        # turn_data.setdefault("outreach_campaign_key", "N/A" if interaction_type != "outreach" else "some_key")


        async with aiofiles.open(log_file_path, mode='a', encoding='utf-8') as f:
            await f.write(json.dumps(turn_data, ensure_ascii=False) + '\n')
        
        logger.debug("Logged turn to %s for chat_id %s. Data: %s...", log_file_path, chat_id, str(turn_data)[:100])

    except Exception as e:
        logger.error("Error logging interaction turn for chat_id %s to %s: %s",
                     chat_id, user_log_dir_path / (log_file_name if 'log_file_name' in locals() else 'unknown_file'), e, exc_info=False)


def _get_item_from_numbered_list(list_key: str, identifier: str, pop_list: bool = True) -> str | None:
    """
    Helper to resolve an identifier (number or string) against a previously displayed numbered list.
    Returns the actual item ID (e.g., a chat_id or role_name) or None if not found.
    If pop_list is True, the list is cleared from LAST_DISPLAYED_LISTS after lookup.
    """
    global LAST_DISPLAYED_LISTS
    if list_key not in LAST_DISPLAYED_LISTS:
        return identifier # Assume it's already an ID if no list was stored

    stored_list = LAST_DISPLAYED_LISTS.get(list_key, {})
    item_id = None

    if identifier.isdigit():
        num = int(identifier)
        item_id = stored_list.get(num)
        if not item_id:
            logger.warning("Numbered list resolver: Number %d not found in list '%s'.", num, list_key)
            return None # Explicitly None if number not in list
    else:
        item_id = identifier # Assume it's an ID string

    if pop_list and list_key in LAST_DISPLAYED_LISTS:
        # If we are using the list for a one-time selection, clear it.
        # For lists that might be referred to multiple times before refresh, set pop_list=False.
        del LAST_DISPLAYED_LISTS[list_key]
        logger.debug("Cleared numbered list cache for key: %s", list_key)
        
    return item_id if item_id else identifier # Fallback to identifier if lookup failed but was string


# --- Existing WPP Helpers (get_wa_version_async, close_creator_async) - UNCHANGED ---
async def get_wa_version_async(client_instance) -> str:
    logger.debug("Async helper: get_wa_version_async called.")
    if not client_instance: logger.debug("Async helper: get_wa_version_async - client_instance is None."); return "N/A (No client)"
    try:
        if hasattr(client_instance, 'getWAVersion'):
            get_version_method = client_instance.getWAVersion
            version = await get_version_method() if asyncio.iscoroutinefunction(get_version_method) else get_version_method()
            logger.debug("Async helper: get_wa_version_async - Retrieved version: %s", version)
            return str(version) if version else "N/A (Empty version)"
        else: logger.warning("Async helper: get_wa_version_async - client_instance has no 'getWAVersion' attribute."); return "N/A (No method)"
    except Exception as e: logger.warning("Async helper: get_wa_version_async - Could not retrieve WA version: %s", e)
    return "Error fetching version"

async def close_creator_async(creator):
    logger.debug("Async helper: close_creator_async called for creator: %s", creator)
    if not creator: logger.debug("Async helper: close_creator_async - No creator instance provided."); return
    close_method_name, is_method_async = (None, False)
    if hasattr(creator, 'sync_close'):
        close_method_name = 'sync_close'; is_method_async = asyncio.iscoroutinefunction(getattr(creator, 'sync_close'))
    elif hasattr(creator, 'close'):
        close_method_name = 'close'; is_method_async = asyncio.iscoroutinefunction(getattr(creator, 'close'))
    if close_method_name:
        logger.info("Async helper: Attempting to call creator.%s() %s", close_method_name, '(asynchronously)' if is_method_async else '(synchronously)')
        try:
            if is_method_async: await getattr(creator, close_method_name)()
            else: getattr(creator, close_method_name)()
            logger.info("Async helper: Creator method %s() called successfully.", close_method_name)
        except RuntimeError as e_rt_close:
            if "Event loop is closed" in str(e_rt_close) and is_method_async: logger.warning("Async helper: Async close error for %s (loop closed): %s", close_method_name, e_rt_close)
            else: logger.error("Async helper: RuntimeError during creator.%s(): %s", close_method_name, e_rt_close)
        except Exception as e_close: logger.error("Async helper: Exception during creator.%s(): %s", close_method_name, e_close, exc_info=True)
    else: logger.warning("Async helper: Creator instance has no recognized 'close' or 'sync_close' method.")

# --- Existing Knowledge Loader - UNCHANGED for now ---
def load_knowledge_from_file(filepath: str) -> str:
    if not filepath: logger.debug("Knowledge loader: No knowledge filepath provided."); return ""
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f: knowledge = f.read().strip()
            if knowledge: logger.info("Knowledge loader: Loaded from '%s'. Length: %d chars.", filepath, len(knowledge))
            else: logger.info("Knowledge loader: File '%s' exists but is empty.", filepath)
            return knowledge
        else: logger.warning("Knowledge loader: File not found at '%s'. No knowledge used.", filepath); return ""
    except Exception as e_load_knowledge: logger.error("Knowledge loader: Error reading file '%s': %s", filepath, e_load_knowledge); return ""
# --- END OF CORE HELPER FUNCTIONS (PART 3 MODIFIED) ---
    


# ... (previous code from Part 1, 2, 10, 3) ...

# -----------------------------------------------------------------------------
# Part 4: Ollama Interaction Function (query_ollama_chat)
# - Now uses globally configured g_ollama_model_name, g_ollama_chat_endpoint, etc.
# - Logging of interaction turn (user prompt + AI response) will be done by the calling function
#   (e.g., process_aggregated_messages) AFTER this function returns, so it can include AI response.
# -----------------------------------------------------------------------------
print("WPP_Ollama_Chat_Assistant_V_ROADMAP_Outreach_Part4_Integrate: Defining Ollama interaction function.")

def query_ollama_chat(
    chat_id: str,
    user_prompt_text: str,
    knowledge_content: str,
    custom_system_prompt: str = None, # For outreach or specific tasks
    specific_chat_history_deque: deque = None # For outreach or specific tasks
    ) -> str:
    """
    Queries Ollama /api/chat. Uses global defaults or custom prompts/history.
    Updates the provided history deque (either global CHAT_HISTORIES[chat_id] or specific_chat_history_deque).
    Returns AI's response string or an error message string.
    """
    # These globals are now populated from g_admin_config
    global g_system_prompt, g_ollama_model_name, g_max_chat_history_turns, g_ollama_model_options
    global g_ollama_chat_endpoint, g_ollama_request_timeout
    global CHAT_HISTORIES, INTERACTION_LOG # For in-memory log

    # Determine system prompt to use
    # If a custom_system_prompt is provided (e.g., for outreach), it takes precedence.
    # Otherwise, g_system_prompt (which is loaded from config, potentially including role-specific parts) is used.
    system_prompt_to_use = custom_system_prompt if custom_system_prompt is not None else g_system_prompt
    
    history_deque_to_update: deque
    is_outreach_context = False

    if specific_chat_history_deque is not None:
        history_deque_to_update = specific_chat_history_deque
        is_outreach_context = True
        # Maxlen for outreach history deques is set when they are created
        logger.info("Ollama chat (Outreach Context): Using specific history for chat_id '%s'. Model: '%s'. Deque maxlen: %s.",
                    chat_id, g_ollama_model_name, history_deque_to_update.maxlen)
    else: # Standard reactive chat
        # Ensure maxlen is derived from g_max_chat_history_turns (from admin_config)
        standard_maxlen = g_max_chat_history_turns * 2 if g_max_chat_history_turns > 0 else None
        if chat_id not in CHAT_HISTORIES:
            CHAT_HISTORIES[chat_id] = deque(maxlen=standard_maxlen)
            logger.debug("Ollama chat (Reactive Context): New history deque for chat_id '%s', maxlen: %s.",
                         chat_id, standard_maxlen)
        elif CHAT_HISTORIES[chat_id].maxlen != standard_maxlen: # Maxlen changed via admin command
            logger.info("Ollama chat (Reactive Context): Max history turns changed for chat_id '%s'. Recreating deque.", chat_id)
            existing_messages = list(CHAT_HISTORIES[chat_id])
            CHAT_HISTORIES[chat_id] = deque(existing_messages, maxlen=standard_maxlen)
        history_deque_to_update = CHAT_HISTORIES[chat_id]
        logger.info("Ollama chat (Reactive Context): Using standard history for chat_id '%s'. Model: '%s'. Max turns for history: %d.",
                    chat_id, g_ollama_model_name, g_max_chat_history_turns)

    current_chat_history_list_for_api = list(history_deque_to_update)

    effective_system_prompt = system_prompt_to_use
    if knowledge_content: # Append general knowledge if provided and relevant
        effective_system_prompt = (
            f"المعلومات الأساسية وقاعدة المعرفة العامة (استخدمها إذا كانت ذات صلة بسؤال المستخدم):\n---\n{knowledge_content}\n---\n\n"
            f"مهمتك وتعليماتك الخاصة (System Prompt):\n{system_prompt_to_use}"
        )
    
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Ollama chat: Effective system prompt for chat '%s' (is_outreach: %s, first 150 chars): %s...", 
                     chat_id, is_outreach_context, effective_system_prompt)

    messages_payload_for_api = [{"role": "system", "content": effective_system_prompt}]
    messages_payload_for_api.extend(current_chat_history_list_for_api)
    messages_payload_for_api.append({"role": "user", "content": user_prompt_text})
    
    if logger.isEnabledFor(logging.DEBUG):
        try:
            messages_preview = [{"role": m['role'], "content_preview": m['content'] + ('...' if len(m['content']) > 100 else '')} for m in messages_payload_for_api]
            debug_payload = {"model": g_ollama_model_name, "messages_preview": messages_preview, "options": g_ollama_model_options}
            logger.debug("Ollama chat: API Request Payload Preview (chat '%s', outreach: %s):\n%s...", 
                         chat_id, is_outreach_context, json.dumps(debug_payload, indent=2, ensure_ascii=False)[:1000])
        except Exception as e_json_dbg: logger.debug("Ollama chat: Could not serialize payload for debug: %s", e_json_dbg)

    api_payload = { "model": g_ollama_model_name, "messages": messages_payload_for_api, "options": g_ollama_model_options, "stream": False }

    try:
        response = requests.post(g_ollama_chat_endpoint, json=api_payload, timeout=g_ollama_request_timeout)
        response.raise_for_status()
        response_data = response.json()

        if "message" in response_data and "content" in response_data["message"]:
            assistant_response_text = response_data["message"]["content"].strip()
            logger.info("Ollama chat: Assistant response received for '%s' (outreach: %s, first 100 chars): '%s...'", 
                        chat_id, is_outreach_context, assistant_response_text)

            # Append to the correct history deque (user prompt and AI response)
            history_deque_to_update.append({"role": "user", "content": user_prompt_text})
            history_deque_to_update.append({"role": "assistant", "content": assistant_response_text})
            logger.debug("Ollama chat: Chat history (type: %s) updated for '%s'. New deque length: %d.", 
                         "outreach" if is_outreach_context else "reactive", chat_id, len(history_deque_to_update))
            
            # Add to the in-memory quick log (persistent .jsonl logging is handled by the caller)
            INTERACTION_LOG.append({
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "chat_id": chat_id,
                "user_message": user_prompt_text, "ai_reply": assistant_response_text,
                "outreach_context": is_outreach_context,
                "model_used": g_ollama_model_name
            })
            return assistant_response_text
        else:
            logger.error("Ollama chat: 'message.content' key not found in Ollama response for '%s'. Full response: %s", chat_id, response_data)
            return "خطأ: لم يتمكن مساعد الذكاء الاصطناعي من إنشاء رد صالح حاليًا." # AI Error Message
    except requests.exceptions.Timeout:
        logger.error("Ollama chat: Request to Ollama timed out for '%s' after %d seconds.", chat_id, g_ollama_request_timeout)
        return "خطأ: استغرق مساعد الذكاء الاصطناعي وقتًا طويلاً جدًا للرد هذه المرة." # AI Error Message
    except requests.exceptions.RequestException as e_req:
        logger.error("Ollama chat: API request to Ollama failed for '%s': %s", chat_id, e_req)
        return f"خطأ: هناك مشكلة في الاتصال بخدمة مساعد الذكاء الاصطناعي الآن." # AI Error Message
    except json.JSONDecodeError:
        resp_text = response.text if 'response' in locals() and hasattr(response, 'text') else "N/A"
        logger.error("Ollama chat: Error decoding JSON response from Ollama for '%s'. Response text: %s", chat_id, resp_text)
        return "خطأ: تم استلام رد بتنسيق غير صالح من مساعد الذكاء الاصطناعي." # AI Error Message
    except Exception as e_ollama_unexpected:
        logger.error("Ollama chat: Unexpected error during Ollama query for '%s': %s", chat_id, e_ollama_unexpected, exc_info=True)
        return "خطأ: حدثت مشكلة غير متوقعة أثناء محاولة معالجة طلبك." # AI Error Message
    
    return "خطأ عام: لم يتمكن مساعد الذكاء الاصطناعي من معالجة الطلب حاليًا." # Fallback AI Error Message
# -----------------------------------------------------------------------------
# --- END OF OLLAMA INTERACTION FUNCTION (PART 4 MODIFIED) ---
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Part 5: Admin Command Handler function
# - Heavily revised for admin_config.json integration.
# - New outreach approval commands.
# - Numbered list interaction for some commands.
# - System power commands.
# -----------------------------------------------------------------------------
print("WPP_Ollama_Chat_Assistant_V_ROADMAP_Outreach_Part5_Integrate: Defining Admin Command Handler.")

# (Located in what was originally Part 5 of the script)

async def handle_admin_command(admin_chat_id: str, command_text: str):
    """Handles admin commands, now interacts with g_admin_config."""
    global g_admin_config, AI_IS_ACTIVE, INTERACTION_LOG, wpp_client
    global g_system_prompt, g_ollama_model_name, g_max_chat_history_turns, g_ollama_model_options
    global g_outreach_prompts, ACTIVE_OUTREACH_CONVERSATIONS, PREPARED_OUTREACHES, g_next_prepared_id_counter
    global LAST_DISPLAYED_LISTS

    # --- DEBUG LOGGING FOR COMMAND PARSING ---
    logger.debug(f"Admin Command Handler: Received raw command_text: '[{command_text}]'")
    logger.debug(f"Admin Command Handler: Using g_command_prefix: '[{g_command_prefix}]'")
    # --- END DEBUG LOGGING ---

    if not command_text.startswith(g_command_prefix):
        logger.warning("Admin cmd handler: Text does not start with prefix '%s'. Command: '%s'", g_command_prefix, command_text)
        return

    command_body = command_text[len(g_command_prefix):].strip()
    # --- DEBUG LOGGING FOR COMMAND PARSING ---
    logger.debug(f"Admin Command Handler: command_body after strip: '[{command_body}]'")
    # --- END DEBUG LOGGING ---

    parts = command_body.split(" ", 1)
    # --- DEBUG LOGGING FOR COMMAND PARSING ---
    logger.debug(f"Admin Command Handler: parts after split: {parts}")
    # --- END DEBUG LOGGING ---
    
    command = parts[0].lower()
    # --- DEBUG LOGGING FOR COMMAND PARSING ---
    logger.debug(f"Admin Command Handler: extracted command: '[{command}]'")
    # --- END DEBUG LOGGING ---

    args_str = parts[1].strip() if len(parts) > 1 else ""
    # --- DEBUG LOGGING FOR COMMAND PARSING ---
    logger.debug(f"Admin Command Handler: extracted args_str: '[{args_str}]'")
    # --- END DEBUG LOGGING ---
    
    reply_message = f"Admin command '{command}' acknowledged." # Default reply
    config_changed = False # Flag to trigger saving admin_config.json

    # --- Config Management Commands ---
    if command == "setconfig":
        key_path_str, value_str = args_str.split(" ", 1) if " " in args_str else (args_str, None)
        if key_path_str and value_str is not None:
            try:
                value = json.loads(value_str)
            except json.JSONDecodeError:
                value = value_str
            
            keys = key_path_str.split('.')
            conf_ref = g_admin_config
            try:
                for i, key_part in enumerate(keys[:-1]):
                    if key_part not in conf_ref or not isinstance(conf_ref[key_part], dict):
                        conf_ref[key_part] = {}
                    conf_ref = conf_ref[key_part]
                
                if isinstance(conf_ref, dict):
                    conf_ref[keys[-1]] = value
                    reply_message = f"Config '{key_path_str}' set to: {value_str}"
                    config_changed = True
                    load_admin_config() 
                else:
                    reply_message = f"Error: Path '{'.'.join(keys[:-1])}' is not a dictionary in config."
            except Exception as e_setconf:
                reply_message = f"Error setting config '{key_path_str}': {e_setconf}"
        else:
            reply_message = f"Usage: {g_command_prefix}setconfig <key_path> <json_value>"
    
    elif command == "getconfig":
        key_path_str = args_str
        if not key_path_str:
            reply_message = f"Current Admin Config:\n{json.dumps(g_admin_config, indent=2, ensure_ascii=False)}"
        else:
            keys = key_path_str.split('.')
            conf_ref = g_admin_config
            try:
                for key_part in keys:
                    if isinstance(conf_ref, dict):
                        conf_ref = conf_ref[key_part]
                    else: 
                        if key_part.isdigit() and isinstance(conf_ref, list):
                           conf_ref = conf_ref[int(key_part)]
                        else:
                            raise KeyError(f"Part '{key_part}' not found or path invalid.")
                reply_message = f"Config '{key_path_str}':\n{json.dumps(conf_ref, indent=2, ensure_ascii=False)}"
            except (KeyError, IndexError, TypeError) as e_getconf:
                reply_message = f"Error getting config '{key_path_str}': Key or path not found or invalid ({e_getconf})."

    elif command == "saveconfig": 
        save_admin_config()
        reply_message = "Admin config explicitly saved."
    
    elif command == "loadconfig":
        load_admin_config()
        reply_message = "Admin config explicitly reloaded."

    elif command == "aistatus":
        reply_message = f"Reactive AI is {'ACTIVE (ON)' if AI_IS_ACTIVE else 'INACTIVE (OFF)'}."
    
    elif command == "setprompt": 
        if args_str:
            g_admin_config["base_system_prompt_arabic"] = args_str
            config_changed = True
            load_admin_config() 
            reply_message = f"Base Reactive AI system prompt updated. Preview: '{g_system_prompt}...'"
        else: reply_message = f"Usage: {g_command_prefix}setprompt <new_prompt_text>"
    elif command == "getprompt": reply_message = f"Current Base Reactive AI System Prompt:\n{g_system_prompt}"

    elif command == "setmodel":
        model_to_set = _get_item_from_numbered_list("available_models", args_str.strip())
        if model_to_set:
            g_admin_config["ollama_model_name"] = model_to_set
            config_changed = True
            load_admin_config()
            reply_message = f"Ollama model set to '{g_ollama_model_name}'. (Ollama server may need reload for new files)."
        else: reply_message = f"Usage: {g_command_prefix}setmodel <model_name_or_number_from_listmodels>"
    elif command == "getmodel": reply_message = f"Current Ollama model: {g_ollama_model_name}"
    
    elif command == "listmodels": 
        try:
            response = requests.get(f"{g_ollama_api_base_url}/api/tags", timeout=10)
            response.raise_for_status()
            models_data = response.json()
            if models_data and "models" in models_data:
                model_list_msgs = ["Available Ollama Models:"]
                LAST_DISPLAYED_LISTS['available_models'] = {}
                for i, model_info in enumerate(models_data["models"]):
                    model_name = model_info.get("name", "Unknown Model")
                    model_list_msgs.append(f"{i+1}. {model_name}")
                    LAST_DISPLAYED_LISTS['available_models'][i+1] = model_name
                model_list_msgs.append(f"\nUse {g_command_prefix}setmodel <number_or_name> to select.")
                reply_message = "\n".join(model_list_msgs)
            else:
                reply_message = "No models found or unexpected response from Ollama /api/tags."
        except Exception as e_list_models:
            reply_message = f"Error fetching models from Ollama: {e_list_models}"

    elif command == "gethistory": 
        if not INTERACTION_LOG: reply_message = "In-memory interaction log is empty."
        else:
            history_lines = [f"In-Memory Interaction Log (last {len(INTERACTION_LOG)} of max {g_max_interaction_log_size}):"]
            log_copy = list(INTERACTION_LOG)
            for entry in log_copy:
                chat_id_entry = entry.get("chat_id", "Unknown")
                user_msg_short = entry.get('user_message', "N/A").replace('\n', ' ')[:70]
                ai_reply_short = entry.get('ai_reply', "N/A").replace('\n', ' ')[:70]
                outreach_tag = "(Outreach)" if entry.get("outreach_context") else ""
                model_tag = f"(Model: {entry.get('model_used', 'N/A')})"
                history_lines.append(f"[{entry.get('timestamp', 'N/A')}] From: {chat_id_entry} {outreach_tag} {model_tag}\n  U: {user_msg_short}...\n  A: {ai_reply_short}...")
            reply_message = "\n---\n".join(history_lines) + f"\n\n[Admin Note: In-memory log not cleared by this command. Use {g_command_prefix}clearhistory for that, or {g_command_prefix}viewlog for persistent logs.]"
    elif command == "clearhistory": INTERACTION_LOG.clear(); reply_message = "In-memory interaction log cleared."

    elif command == "sethistoryturns":
        try:
            turns = int(args_str)
            if turns >= 0:
                g_admin_config["max_chat_history_turns"] = turns
                config_changed = True; load_admin_config()
                reply_message = f"Reactive AI max history turns set to {g_max_chat_history_turns}."
            else: reply_message = "Error: History turns must be non-negative."
        except ValueError: reply_message = f"Usage: {g_command_prefix}sethistoryturns <number>"
    elif command == "gethistoryturns": reply_message = f"Current Reactive AI max history turns: {g_max_chat_history_turns}"

    elif command == "setctx":
        try:
            ctx = int(args_str)
            if ctx > 0:
                g_admin_config.setdefault("ollama_model_options", {})["num_ctx"] = ctx
                config_changed = True; load_admin_config()
                reply_message = f"Ollama num_ctx set to {g_ollama_model_options.get('num_ctx')}."
            else: reply_message = "Error: num_ctx must be positive."
        except ValueError: reply_message = f"Usage: {g_command_prefix}setctx <number>"
    elif command == "getctx": reply_message = f"Current Ollama num_ctx: {g_ollama_model_options.get('num_ctx', 'Default')}"

    elif command == "settemp":
        try:
            temp = float(args_str)
            if 0.0 <= temp <= 2.0:
                g_admin_config.setdefault("ollama_model_options", {})["temperature"] = temp
                config_changed = True; load_admin_config()
                reply_message = f"Ollama temperature set to {g_ollama_model_options.get('temperature'):.2f}."
            else: reply_message = "Error: Temperature typically 0.0-2.0."
        except ValueError: reply_message = f"Usage: {g_command_prefix}settemp <float>"
    elif command == "gettemp": reply_message = f"Current Ollama temperature: {g_ollama_model_options.get('temperature', 'Default')}"
    
    elif command == "getoptions": reply_message = f"Current Ollama Options (from config):\n{json.dumps(g_ollama_model_options, indent=2)}"

    elif command == "addoutreachprompt":
        prompt_key_val = args_str.split(" ", 1)
        if len(prompt_key_val) == 2:
            key, text = prompt_key_val[0].strip().lower(), prompt_key_val[1].strip()
            if key and text:
                g_outreach_prompts[key] = text; save_outreach_prompts_file()
                reply_message = f"Outreach prompt for key '{key}' added/updated in outreach_prompts.json."
            else: reply_message = "Error: Outreach prompt key and text cannot be empty."
        else: reply_message = f"Usage: {g_command_prefix}addoutreachprompt <key_name> <full_prompt_text>"
    elif command == "listoutreachprompts":
        if not g_outreach_prompts: reply_message = "No custom outreach prompts defined in outreach_prompts.json."
        else:
            prompt_list_msgs = ["Available Outreach Prompt Keys (from outreach_prompts.json):"]
            LAST_DISPLAYED_LISTS['outreach_prompts'] = {}
            for i, key_name in enumerate(g_outreach_prompts.keys()):
                prompt_list_msgs.append(f"{i+1}. {key_name}")
                LAST_DISPLAYED_LISTS['outreach_prompts'][i+1] = key_name
            prompt_list_msgs.append(f"\nUse {g_command_prefix}getoutreachprompt <number_or_key> or for outreach cmd.")
            reply_message = "\n".join(prompt_list_msgs)
    elif command == "getoutreachprompt":
        key_to_get = _get_item_from_numbered_list("outreach_prompts", args_str.strip().lower())
        if key_to_get and key_to_get in g_outreach_prompts:
            reply_message = f"Outreach Prompt '{key_to_get}':\n{g_outreach_prompts[key_to_get]}"
        else: reply_message = f"Error: Outreach prompt key '{key_to_get or args_str}' not found."
    elif command == "deloutreachprompt":
        key_to_del = _get_item_from_numbered_list("outreach_prompts", args_str.strip().lower())
        if key_to_del and key_to_del in g_outreach_prompts:
            del g_outreach_prompts[key_to_del]; save_outreach_prompts_file()
            reply_message = f"Outreach prompt '{key_to_del}' deleted from outreach_prompts.json."
        else: reply_message = f"Error: Outreach prompt key '{key_to_del or args_str}' not found."

    elif command == "prepareoutreach":
        outreach_args_list = [] 
        temp_arg = ""; in_quote = False
        for char_ in args_str:
            if char_ == '"': in_quote = not in_quote
            elif char_ == ' ' and not in_quote:
                if temp_arg: outreach_args_list.append(temp_arg); temp_arg = ""
            else: temp_arg += char_
        if temp_arg: outreach_args_list.append(temp_arg)

        if len(outreach_args_list) < 2:
            reply_message = f"Usage: {g_command_prefix}prepareoutreach <target_id> <prompt_key_or_\"initial_message\"> [\"custom_system_prompt\"]"
        else:
            target_chat_id = outreach_args_list[0].strip()
            if not (target_chat_id.endswith(("@c.us", "@g.us")) and target_chat_id.split('@')[0].isdigit()):
                 reply_message = "Error: Invalid target ID format (must be number@c.us or group_id@g.us)."
            else:
                prompt_key_or_initial_msg_arg = outreach_args_list[1].strip()
                prompt_key_or_initial_msg = _get_item_from_numbered_list("outreach_prompts", prompt_key_or_initial_msg_arg, pop_list=False) or prompt_key_or_initial_msg_arg
                outreach_task_custom_system_prompt_arg = outreach_args_list[2].strip() if len(outreach_args_list) > 2 else None
                outreach_final_system_prompt_to_use = outreach_task_custom_system_prompt_arg
                task_description_for_log = ""
                
                if prompt_key_or_initial_msg in g_outreach_prompts: 
                    task_description_for_log = f"Outreach using prompt key: {prompt_key_or_initial_msg}"
                    if not outreach_final_system_prompt_to_use: 
                        outreach_final_system_prompt_to_use = g_outreach_prompts[prompt_key_or_initial_msg]
                    logger.info("Admin cmd: Preparing outreach for '%s' using prompt key '%s'. System prompt for AI generation: '%s...'",
                                target_chat_id, prompt_key_or_initial_msg, str(outreach_final_system_prompt_to_use))
                    initiator_prompt_for_ai_to_start = "ابدأ المحادثة الآن بناءً على تعليماتك." 
                else: 
                    task_description_for_log = f"Outreach with direct initial message by AI: {prompt_key_or_initial_msg}..."
                    if not outreach_final_system_prompt_to_use: 
                        outreach_final_system_prompt_to_use = g_system_prompt 
                    logger.info("Admin cmd: Preparing outreach for '%s' with AI to send direct message. System prompt for AI generation: '%s...'",
                                target_chat_id, str(outreach_final_system_prompt_to_use))
                    initiator_prompt_for_ai_to_start = prompt_key_or_initial_msg

                temp_outreach_history = deque(maxlen=g_max_chat_history_turns * 2 if g_max_chat_history_turns > 0 else None)
                proposed_ai_message = query_ollama_chat(
                    target_chat_id, 
                    initiator_prompt_for_ai_to_start,
                    "", 
                    custom_system_prompt=outreach_final_system_prompt_to_use,
                    specific_chat_history_deque=temp_outreach_history
                )

                if proposed_ai_message and not proposed_ai_message.startswith("خطأ:") and not proposed_ai_message.startswith("Error:"):
                    g_next_prepared_id_counter += 1
                    prepared_id = f"p{g_next_prepared_id_counter}"
                    PREPARED_OUTREACHES[prepared_id] = {
                        "target_chat_id": target_chat_id,
                        "proposed_message": proposed_ai_message,
                        "system_prompt": outreach_final_system_prompt_to_use,
                        "task_description": task_description_for_log,
                        "timestamp": time.time()
                    }
                    reply_message = (
                        f"Prepared outreach for {target_chat_id} (ID: {prepared_id}).\n"
                        f"Task: {task_description_for_log}\n"
                        f"AI proposes: '{proposed_ai_message}...'\n\n"
                        f"Actions:\n"
                        f"1. Send As Is\n"
                        f"2. Edit & Send\n"
                        f"3. Cancel\n"
                        f"Reply with: {g_command_prefix}approveoutreach {prepared_id} <action_number> [\"edited_text_if_action_2\"]"
                    )
                    logger.info("Admin cmd: Outreach proposal '%s' created for '%s'. Admin notified.", prepared_id, target_chat_id)
                else:
                    reply_message = f"Error: Could not generate proposed AI message for outreach to {target_chat_id}. LLM response: {proposed_ai_message}"
                    logger.error("Admin cmd: Failed to get valid proposed AI message for '%s'. LLM response: %s", target_chat_id, proposed_ai_message)

    elif command == "listpreparedoutreach":
        if not PREPARED_OUTREACHES:
            reply_message = "No outreach proposals currently awaiting approval."
        else:
            prepared_list_msgs = ["Pending Outreach Approvals:"]
            LAST_DISPLAYED_LISTS['prepared_outreaches'] = {}
            idx = 1
            for prep_id, details in PREPARED_OUTREACHES.items():
                target = details.get("target_chat_id", "N/A")
                snippet = details.get("proposed_message", "N/A")
                task = details.get("task_description", "N/A")
                prepared_list_msgs.append(f"{idx}. ID: {prep_id}, Target: {target}, Task: {task}..., AI: '{snippet}...'")
                LAST_DISPLAYED_LISTS['prepared_outreaches'][idx] = prep_id
                idx +=1
            prepared_list_msgs.append(f"\nUse {g_command_prefix}approveoutreach <ID_or_Number> <action_number> ...")
            reply_message = "\n".join(prepared_list_msgs)

    elif command == "approveoutreach":
        args_parts = args_str.split(" ", 2) 
        if len(args_parts) < 2:
            reply_message = f"Usage: {g_command_prefix}approveoutreach <prepared_id_or_number> <action_number> [\"edited_text\"]"
        else:
            prep_id_arg = args_parts[0]
            action_num_str = args_parts[1]
            edited_text = args_parts[2].strip('"') if len(args_parts) > 2 else None
            prep_id = _get_item_from_numbered_list('prepared_outreaches', prep_id_arg)

            if not prep_id or prep_id not in PREPARED_OUTREACHES:
                reply_message = f"Error: Prepared outreach ID '{prep_id_arg}' not found or invalid."
            elif not action_num_str.isdigit() or not (1 <= int(action_num_str) <= 3):
                reply_message = "Error: Action number must be 1 (Send), 2 (Edit & Send), or 3 (Cancel)."
            else:
                action_num = int(action_num_str)
                details = PREPARED_OUTREACHES[prep_id]
                target_chat_id = details["target_chat_id"]
                final_message_to_send = ""

                if action_num == 1: 
                    final_message_to_send = details["proposed_message"]
                    reply_message = f"Outreach '{prep_id}' approved for {target_chat_id}. Sending proposed message."
                elif action_num == 2: 
                    if edited_text is None:
                        reply_message = "Error: Action 2 (Edit & Send) requires edited text."
                    else:
                        final_message_to_send = edited_text
                        reply_message = f"Outreach '{prep_id}' approved with edits for {target_chat_id}. Sending your message."
                elif action_num == 3: 
                    del PREPARED_OUTREACHES[prep_id]
                    reply_message = f"Prepared outreach '{prep_id}' for {target_chat_id} cancelled."
                    logger.info("Admin cmd: Prepared outreach '%s' cancelled.", prep_id)
                    if wpp_client: wpp_client.sendText(admin_chat_id, reply_message) # REMOVED await
                    return 

                if final_message_to_send: 
                    if wpp_client:
                        try:
                            wpp_client.sendText(target_chat_id, final_message_to_send) # REMOVED await
                            logger.info("Admin cmd: Outreach message sent to '%s' for approved task '%s'.", target_chat_id, prep_id)
                            await log_interaction_turn(target_chat_id, "outreach", {
                                "role": "assistant", "content": final_message_to_send,
                                "outreach_campaign_key": details.get("task_description"), 
                                "system_prompt_used": details["system_prompt"] + "..." 
                            })
                            ACTIVE_OUTREACH_CONVERSATIONS[target_chat_id] = {
                                "system_prompt": details["system_prompt"],
                                "task_description": details["task_description"],
                                "history": deque([{"role": "assistant", "content": final_message_to_send}],
                                                 maxlen=g_max_chat_history_turns * 2 if g_max_chat_history_turns > 0 else None),
                                "is_active": True,
                                "start_time": time.time(),
                                "prepared_id_source": prep_id
                            }
                            del PREPARED_OUTREACHES[prep_id] 
                            reply_message += f"\nOutreach to {target_chat_id} is now active."
                            logger.info("Admin cmd: Outreach state for '%s' (from prep_id '%s') activated. Task: %s", target_chat_id, prep_id, details["task_description"])
                        except Exception as e_send_outreach:
                            reply_message = f"Error sending approved outreach message to {target_chat_id}: {e_send_outreach}"
                            logger.error("Admin cmd: Error sending approved outreach to '%s': %s", target_chat_id, e_send_outreach)
                    else:
                        reply_message = "Error: WPP client not ready for sending outreach."

    elif command == "cancelprepared": 
        prep_id_arg = args_str.strip()
        prep_id = _get_item_from_numbered_list('prepared_outreaches', prep_id_arg)
        if prep_id and prep_id in PREPARED_OUTREACHES:
            del PREPARED_OUTREACHES[prep_id]
            reply_message = f"Prepared outreach '{prep_id}' cancelled."
        else: reply_message = f"Error: Prepared outreach ID '{prep_id_arg}' not found."
                
    elif command == "listactiveoutreach":
        if not ACTIVE_OUTREACH_CONVERSATIONS:
            reply_message = "No outreach conversations currently marked active."
        else:
            active_list_msgs = ["Currently Active Outreach Conversations:"]
            LAST_DISPLAYED_LISTS['active_outreaches'] = {}
            idx = 1
            active_found = False
            for cid, data in ACTIVE_OUTREACH_CONVERSATIONS.items():
                if data.get("is_active"):
                    active_found = True
                    task_desc = data.get('task_description','N/A')
                    active_list_msgs.append(f"{idx}. Target: {cid}, Task: {task_desc}...")
                    LAST_DISPLAYED_LISTS['active_outreaches'][idx] = cid
                    idx += 1
            if not active_found:
                 reply_message = "No outreach conversations currently marked active."
            else:
                active_list_msgs.append(f"\nUse {g_command_prefix}getoutreachdetails <Number_or_TargetID> or {g_command_prefix}endoutreach <Number_or_TargetID>.")
                reply_message = "\n".join(active_list_msgs)

    elif command == "getoutreachdetails":
        target_id_arg = args_str.strip()
        target_id = _get_item_from_numbered_list('active_outreaches', target_id_arg) or \
                    _get_item_from_numbered_list('prepared_outreaches', target_id_arg, pop_list=False) 

        details_to_show = None
        source = ""
        if target_id in ACTIVE_OUTREACH_CONVERSATIONS:
            details_to_show = ACTIVE_OUTREACH_CONVERSATIONS[target_id]
            source = "Active Outreach"
        elif target_id in PREPARED_OUTREACHES: 
            details_to_show = PREPARED_OUTREACHES[target_id]
            source = "Prepared Outreach Proposal"

        if details_to_show:
            history_msgs = [f"Details for {source}: {target_id}"]
            history_msgs.append(f"Task: {details_to_show.get('task_description', 'N/A')}")
            history_msgs.append(f"System Prompt Used (Initial): {str(details_to_show.get('system_prompt', 'N/A'))}...")
            if 'proposed_message' in details_to_show: 
                 history_msgs.append(f"Proposed AI Message: {details_to_show['proposed_message']}")
            
            conversation_turns = []
            if 'history' in details_to_show and isinstance(details_to_show['history'], deque):
                conversation_turns = list(details_to_show['history']) 
                history_msgs.append("\n--- Conversation History (In-Memory) ---")

            if source == "Active Outreach": 
                log_path = pathlib.Path(INTERACTION_LOGS_DIR) / sanitize_filename(target_id) / "outreach_history.jsonl"
                # Use await asyncio.to_thread for os.path.exists or pathlib.exists()
                if await asyncio.to_thread(log_path.exists):
                    history_msgs.append(f"\n--- Conversation History (Persistent Log: {log_path.name}) ---")
                    try:
                        async with aiofiles.open(log_path, 'r', encoding='utf-8') as f:
                            lines_read = 0
                            async for line in f: 
                                if lines_read >= 50: 
                                    history_msgs.append("... (log truncated for display, more in file)")
                                    break
                                try:
                                    turn = json.loads(line)
                                    role = turn.get("role", "??").upper()
                                    content = turn.get("content", "") 
                                    history_msgs.append(f"[{turn.get('timestamp_iso', 'N/A')}] {role}: {content}")
                                    lines_read += 1
                                except json.JSONDecodeError:
                                    history_msgs.append(f"[RAW_LOG_LINE_ERROR]: {line}")
                        if not lines_read and not conversation_turns: 
                             history_msgs.append("No conversation turns found in persistent log yet.")
                    except Exception as e_readlog:
                        history_msgs.append(f"Error reading persistent log: {e_readlog}")
                elif not conversation_turns : 
                     history_msgs.append("No conversation turns found (in-memory or persistent log).")

            elif conversation_turns: 
                for turn in conversation_turns:
                    role = turn.get("role", "??").upper()
                    content = turn.get("content", "")
                    history_msgs.append(f"{role}: {content}")
            reply_message = "\n".join(history_msgs)
        else:
            reply_message = f"Error: No active or prepared outreach found for ID '{target_id_arg}'."

    elif command == "endoutreach":
        target_id_arg = args_str.strip()
        target_id = _get_item_from_numbered_list('active_outreaches', target_id_arg)
        if target_id and target_id in ACTIVE_OUTREACH_CONVERSATIONS:
            ACTIVE_OUTREACH_CONVERSATIONS[target_id]["is_active"] = False
            await log_interaction_turn(target_id, "outreach", {
                "role": "system_event", "content": f"Admin ended outreach. Task: {ACTIVE_OUTREACH_CONVERSATIONS[target_id].get('task_description')}"
            })
            reply_message = f"Outreach with {target_id} marked inactive. Will revert to default AI on next message."
            logger.info("Admin cmd handler: Outreach for '%s' marked inactive by admin.", target_id)
        else: reply_message = f"Error: No active outreach found for {target_id_arg}."

    elif command == "systemsleep":
        if sys.platform == "win32":
            logger.info("Admin cmd: Attempting to put system to sleep.")
            reply_message = "Attempting to put the system to sleep. Connection will be lost."
            if wpp_client: wpp_client.sendText(admin_chat_id, reply_message) # REMOVED await
            await asyncio.sleep(1) 
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        else: reply_message = "System sleep command is only configured for Windows."
    
    elif command == "systemhibernate":
        if sys.platform == "win32":
            logger.info("Admin cmd: Attempting to put system to hibernate.")
            reply_message = "Attempting to put the system to hibernate. Connection will be lost."
            if wpp_client: wpp_client.sendText(admin_chat_id, reply_message) # REMOVED await
            await asyncio.sleep(1)
            os.system("rundll32.exe powrprof.dll,SetSuspendState Hibernate") 
        else: reply_message = "System hibernate command is only configured for Windows."

    elif command == "help":
        reply_message = (
            f"Admin Commands ({g_command_prefix}):\n"
            f"--- Config & State ---\n"
            f"- setconfig <key.path> <json_value>\n- getconfig [key.path]\n"
            f"- saveconfig | loadconfig\n"
            f"- aistatus | setprompt <text> | getprompt\n"
            f"- setmodel <name_or_num> | getmodel | listmodels\n"
            f"--- History & Logging ---\n"
            f"- gethistory | clearhistory (in-memory)\n"
            f"- viewlog <chatID_or_num> <outreach/reactive> [last_N]\n" # To be added later
            f"--- LLM Params ---\n"
            f"- sethistoryturns <num> | gethistoryturns\n"
            f"- setctx <num> | getctx | settemp <float> | gettemp | getoptions\n"
            f"--- Outreach Prompts (outreach_prompts.json) ---\n"
            f"- addoutreachprompt <key> <text>\n"
            f"- listoutreachprompts | getoutreachprompt <key_or_num> | deloutreachprompt <key_or_num>\n"
            f"--- Outreach Execution & Approval ---\n"
            f"- prepareoutreach <target> <prompt_key_or_\"msg\"> [\"sys_prompt\"]\n"
            f"- listpreparedoutreach\n"
            f"- approveoutreach <prepID_or_num> <1-3> [\"edited_text_for_action_2\"]\n"
            f"- (1:SendAsIs, 2:Edit&Send, 3:Cancel)\n"
            f"- cancelprepared <prepID_or_num>\n"
            f"- listactiveoutreach | getoutreachdetails <targetID_or_num>\n"
            f"- endoutreach <targetID_or_num>\n"
            f"--- System Power (Windows Only) ---\n"
            f"- systemsleep | systemhibernate\n"
            f"- help [command_name_for_details]"
        )
    else:
        reply_message = f"Unknown admin command: '{command}'. Try {g_command_prefix}help."

    if config_changed:
        save_admin_config()

    try:
        if wpp_client and reply_message: 
             wpp_client.sendText(admin_chat_id, reply_message) # REMOVED await
        elif not wpp_client:
             logger.error("Admin cmd handler: wpp_client None, cannot send reply to admin '%s'.", admin_chat_id)
    except Exception as e_admin_reply:
        logger.error("Admin cmd handler: Exception sending reply to admin '%s': %s", admin_chat_id, e_admin_reply, exc_info=True)# --- END OF ADMIN COMMAND HANDLER (PART 5 HEAVILY MODIFIED) ---
# -----------------------------------------------------------------------------
        

# ... (previous code from Parts 1, 2, 10, 3, 4, 5) ...

# -----------------------------------------------------------------------------
# Part 6: Message Processing and Aggregation Logic
# - Revised for strict outreach vs. reactive context separation.
# - Integrates persistent .jsonl logging via log_interaction_turn.
# -----------------------------------------------------------------------------
print("WPP_Ollama_Chat_Assistant_V_ROADMAP_Outreach_Part6_Integrate: Defining message processing logic.")

# (Located in what was originally Part 6 of the script)

async def process_aggregated_messages(chat_id: str, sender_display_name: str):
    """
    Processes aggregated messages. Routes to admin, active outreach, or reactive AI.
    Logs interactions to persistent .jsonl files.
    """
    global USER_MESSAGE_BUFFERS, AI_IS_ACTIVE, wpp_client, INTERACTION_LOG
    global ACTIVE_OUTREACH_CONVERSATIONS, g_admin_config 

    if chat_id not in USER_MESSAGE_BUFFERS or not USER_MESSAGE_BUFFERS[chat_id]:
        logger.debug("Process aggregated: No messages in buffer for chat_id '%s'. Nothing to process.", chat_id)
        return

    aggregated_prompt = "\n".join(USER_MESSAGE_BUFFERS[chat_id]).strip()
    USER_MESSAGE_BUFFERS[chat_id] = [] 
    
    logger.info("Process aggregated: Processing for '%s' (chat_id: '%s'). Aggregated prompt (first 100 chars): '%s...'", 
                sender_display_name, chat_id, aggregated_prompt)

    is_admin_sender = (chat_id == ADMIN_CHAT_ID)
    
    current_interaction_type = "reactive"
    outreach_campaign_key_for_log = None
    current_outreach_system_prompt = None # For logging
    if chat_id in ACTIVE_OUTREACH_CONVERSATIONS and ACTIVE_OUTREACH_CONVERSATIONS[chat_id].get("is_active", False):
        current_interaction_type = "outreach"
        outreach_data_for_log = ACTIVE_OUTREACH_CONVERSATIONS[chat_id]
        outreach_campaign_key_for_log = outreach_data_for_log.get("task_description", "UnknownCampaign")
        current_outreach_system_prompt = outreach_data_for_log.get("system_prompt","N/A")+"..."


    await log_interaction_turn(chat_id, current_interaction_type, {
        "role": "user", "content": aggregated_prompt,
        "sender_display_name": sender_display_name, 
        "outreach_campaign_key": outreach_campaign_key_for_log,
        "system_prompt_used": current_outreach_system_prompt if current_interaction_type == "outreach" else g_admin_config.get("reactive_roles", {}).get(g_admin_config.get("active_reactive_role"),"N/A")+"..."
    })

    if is_admin_sender and aggregated_prompt.startswith(g_command_prefix): 
        logger.info("Process aggregated: Detected admin command from '%s'. Routing to admin handler.", chat_id)
        await handle_admin_command(chat_id, aggregated_prompt)
        return

    if aggregated_prompt.strip().lower() == g_ai_toggle_passphrase.lower():
        new_ai_state = not AI_IS_ACTIVE
        g_admin_config["ai_is_active"] = new_ai_state 
        save_admin_config() 
        load_admin_config() 

        status_reply_msg = f"المساعد الآلي الآن {'يعمل (نشط)' if AI_IS_ACTIVE else 'متوقف (غير نشط)'}."
        logger.info("Process aggregated: AI state toggled by '%s' (ID: '%s') via passphrase. New state: %s",
                    sender_display_name, chat_id, 'ACTIVE' if AI_IS_ACTIVE else 'INACTIVE')
        if wpp_client:
            try: wpp_client.sendText(chat_id, status_reply_msg) # REMOVED await
            except Exception as e_send_status: logger.error("Process aggregated: Error sending AI toggle status: %s", e_send_status)
        
        await log_interaction_turn(chat_id, "reactive", { 
            "role": "system_event", "content": f"AI Toggled to {AI_IS_ACTIVE} by user passphrase.",
            "sender_display_name": sender_display_name
        })
        return

    if chat_id in ACTIVE_OUTREACH_CONVERSATIONS and ACTIVE_OUTREACH_CONVERSATIONS[chat_id].get("is_active", False):
        logger.info("Process aggregated: Message from '%s' is part of an active outreach. Using outreach context.", chat_id)
        outreach_data = ACTIVE_OUTREACH_CONVERSATIONS[chat_id]
        llm_response = "" 

        outreach_approval_mode = g_admin_config.get("outreach_settings", {}).get("approval_mode", "FIRST_ONLY")
        
        if outreach_approval_mode == "ALL_REPLIES" and not outreach_data.get("prepared_id_source"): # Only if NOT the very first message
            # This logic for ALL_REPLIES approval for ongoing chats needs to be more robust
            # and tied into a system similar to PREPARED_OUTREACHES or a new command like $sendnextreply.
            # For now, this just generates and notifies admin.
            proposed_ai_reply = query_ollama_chat(
                chat_id=chat_id, user_prompt_text=aggregated_prompt, knowledge_content="",
                custom_system_prompt=outreach_data["system_prompt"],
                specific_chat_history_deque=outreach_data["history"]
            )
            if proposed_ai_reply and not proposed_ai_reply.startswith("خطأ:"):
                admin_notification = (
                    f"Outreach Target '{sender_display_name}' ({chat_id}) replied: '{aggregated_prompt}...'\n"
                    f"AI proposes reply (ALL_REPLIES mode): '{proposed_ai_reply}...'\n"
                    f"(Admin action required to send - TBD command)"
                )
                if wpp_client: wpp_client.sendText(ADMIN_CHAT_ID, admin_notification) # REMOVED await
                logger.info("Process aggregated (Outreach ALL_REPLIES): Proposed AI reply sent to admin for approval.")
                return 
            else:
                llm_response = proposed_ai_reply 
        else: 
            llm_response = query_ollama_chat(
                chat_id=chat_id, user_prompt_text=aggregated_prompt, knowledge_content="",
                custom_system_prompt=outreach_data["system_prompt"],
                specific_chat_history_deque=outreach_data["history"]
            )

        outreach_data["last_interaction_time"] = time.time()
        # Clear the prepared_id_source after the first user reply has been processed to enable ALL_REPLIES for subsequent messages.
        if "prepared_id_source" in outreach_data:
            del outreach_data["prepared_id_source"]


        if llm_response and not llm_response.startswith("خطأ:") and not llm_response.startswith("Error:"):
            if wpp_client:
                try:
                    wpp_client.sendText(chat_id, llm_response) # REMOVED await
                    logger.info("Process aggregated (Outreach Context): AI Reply sent to '%s'.", chat_id)
                    await log_interaction_turn(chat_id, "outreach", { 
                        "role": "assistant", "content": llm_response,
                        "outreach_campaign_key": outreach_campaign_key_for_log, # Already defined
                        "system_prompt_used": outreach_data["system_prompt"]+"..."
                    })
                except Exception as e_outreach_reply:
                    logger.error("Process aggregated (Outreach Context): Error sending AI reply to '%s': %s", chat_id, e_outreach_reply)
        else: 
            logger.warning("Process aggregated (Outreach Context): LLM error/no valid response for '%s'. LLM output: %s", chat_id, llm_response)
            if wpp_client and llm_response: 
                 try: wpp_client.sendText(chat_id, llm_response) # REMOVED await
                 except Exception: pass
            await log_interaction_turn(chat_id, "outreach", { 
                "role": "assistant", "content": llm_response or "Error: No response from LLM",
                "outreach_campaign_key": outreach_campaign_key_for_log, "is_error": True, # Already defined
                "system_prompt_used": outreach_data["system_prompt"]+"..."
            })
        return

    if AI_IS_ACTIVE: 
        logger.info("Process aggregated (Reactive Context): AI IS ACTIVE. Querying LLM for '%s' (chat_id: '%s').", 
                    sender_display_name, chat_id)
        
        current_knowledge = load_knowledge_from_file(KNOWLEDGE_FILE_PATH)
        
        active_role_key = g_admin_config.get("active_reactive_role", "default_assistant")
        role_prompt_fragment = g_admin_config.get("reactive_roles", {}).get(active_role_key, "")
        effective_reactive_system_prompt = g_admin_config.get("base_system_prompt_arabic", DEFAULT_AI_SYSTEM_PROMPT_ARABIC)
        if role_prompt_fragment and role_prompt_fragment != effective_reactive_system_prompt:
            effective_reactive_system_prompt += f"\n\nتعليمات الدور الإضافية ({active_role_key}):\n{role_prompt_fragment}"

        active_goal_keys = g_admin_config.get("active_goals", [])
        if active_goal_keys:
            goal_instructions = []
            for goal_key in active_goal_keys:
                goal_desc = g_admin_config.get("ai_goals", {}).get(goal_key)
                if goal_desc: goal_instructions.append(f"- {goal_desc} ({goal_key})")
            if goal_instructions:
                effective_reactive_system_prompt += "\n\nالأهداف النشطة حاليًا:\n" + "\n".join(goal_instructions)
        
        style_desc = g_admin_config.get("ai_interaction_style", "")
        if style_desc:
            effective_reactive_system_prompt += f"\n\nأسلوب التفاعل المطلوب: {style_desc}"

        llm_response = query_ollama_chat(
                            chat_id, 
                            aggregated_prompt, 
                            current_knowledge,
                            custom_system_prompt=effective_reactive_system_prompt
                        )
        
        current_system_prompt_for_log = effective_reactive_system_prompt[:200]+"..."


        final_reply_parts = []
        if g_fixed_pre_ai_response_message: final_reply_parts.append(g_fixed_pre_ai_response_message)
        
        actual_llm_content = ""
        if llm_response and not llm_response.startswith("خطأ:") and not llm_response.startswith("Error:"):
             actual_llm_content = llm_response
             if g_ai_persona_prefix_message: final_reply_parts.append(g_ai_persona_prefix_message + actual_llm_content)
             else: final_reply_parts.append(actual_llm_content)
        elif llm_response: 
            final_reply_parts.append(llm_response) 
        else: 
            logger.warning("Process aggregated (Reactive Context): LLM response None/empty for '%s'. Generic fallback.", chat_id)
            final_reply_parts.append("لم أتمكن من معالجة طلبك في الوقت الحالي.") 

        if g_fixed_post_ai_response_message: final_reply_parts.append(g_fixed_post_ai_response_message)
        final_reply_to_send = "\n".join(filter(None, final_reply_parts)).strip()

        if final_reply_to_send:
            if wpp_client:
                try:
                    wpp_client.sendText(chat_id, final_reply_to_send) # REMOVED await
                    logger.info("Process aggregated (Reactive Context): Final reply sent to '%s'.", chat_id)
                    await log_interaction_turn(chat_id, "reactive", { 
                        "role": "assistant", "content": final_reply_to_send, 
                        "llm_raw_response": llm_response, 
                        "system_prompt_used": current_system_prompt_for_log
                    })
                except Exception as e_send_reply:
                    logger.error("Process aggregated (Reactive Context): EXCEPTION sending reply to '%s': %s", sender_display_name, chat_id, e_send_reply)
            else:
                 logger.error("Process aggregated (Reactive Context): wpp_client None. Cannot send reply to '%s'.", sender_display_name, chat_id)
        else: 
            logger.info("Process aggregated (Reactive Context): No content in final_reply_to_send for '%s'. Nothing sent.", sender_display_name, chat_id)
            await log_interaction_turn(chat_id, "reactive", { 
                "role": "assistant", "content": "[No Reply Sent / LLM Error Handled]",
                "llm_raw_response": llm_response, "is_error": True if llm_response and llm_response.startswith("خطأ:") else False,
                "system_prompt_used": current_system_prompt_for_log
            })
            
    else: 
        logger.info("Process aggregated (Reactive Context): AI IS INACTIVE. Message from '%s' logged but not processed by LLM.", sender_display_name, chat_id)
        await log_interaction_turn(chat_id, "reactive", {
            "role": "system_event", "content": "AI Inactive - Message not processed by LLM.",
            "sender_display_name": sender_display_name
        })



async def delayed_message_processor(chat_id: str, sender_display_name: str, delay: float):
    """
    Waits for a specified delay, then calls process_aggregated_messages.
    """
    try:
        await asyncio.sleep(delay)
        # CORRECTED LOG LINE: Added chat_id to the format string
        logger.info("Delayed processor: Timer of %.1fs expired for '%s' (chat_id: '%s'). Processing buffered messages.", delay, sender_display_name, chat_id)
        await process_aggregated_messages(chat_id, sender_display_name)
    except asyncio.CancelledError:
        # CORRECTED LOG LINE: Added chat_id to the format string
        logger.info("Delayed processor: Aggregation timer for '%s' (chat_id: '%s') cancelled (new message or toggle).", sender_display_name, chat_id)
    except Exception as e_delayed_proc:
        logger.error("Delayed processor: Unexpected error for '%s' (chat_id: '%s'): %s", 
                     sender_display_name, chat_id, e_delayed_proc, exc_info=True) # Added chat_id here too for consistency
    finally:
        if chat_id in USER_MESSAGE_TIMERS:
            del USER_MESSAGE_TIMERS[chat_id]# --- END OF MESSAGE PROCESSING AND AGGREGATION LOGIC (PART 6 MODIFIED) ---

# -----------------------------------------------------------------------------
# Part 7: Main WhatsApp Message Callback (on_new_message_received)
# - Minor change for AI toggle to use global config and persist.
# -----------------------------------------------------------------------------
print("WPP_Ollama_Chat_Assistant_V_ROADMAP_Outreach_Part7_Integrate: Defining WhatsApp message callback.")

# (Located in what was originally Part 7 of the script)

async def on_new_message_received(message: dict):
    """
    Asynchronous callback for new messages. Handles filtering, AI toggle, admin passthrough,
    and message buffering.
    """
    global wpp_client, AI_IS_ACTIVE, USER_MESSAGE_BUFFERS, USER_MESSAGE_TIMERS, MAIN_EVENT_LOOP
    global g_ai_toggle_passphrase, g_admin_config # For AI toggle

    if not message or not isinstance(message, dict):
        logger.warning("Callback new_msg: Invalid or empty message object. Type: %s.", type(message))
        return

    chat_id = message.get("from")
    body_content = message.get("body") 
    message_type = message.get("type", "unknown")
    is_group_msg = message.get("isGroupMsg", False)
    is_from_me = message.get("fromMe", False)

    sender_display_name = chat_id 
    if wpp_client and chat_id: 
        try:
            contact_info = await asyncio.to_thread(wpp_client.getContact, chat_id) 
            if contact_info and isinstance(contact_info, dict):
                name_from_contact = contact_info.get("name") or \
                                    contact_info.get("formattedName") or \
                                    contact_info.get("pushname") or \
                                    contact_info.get("shortName")
                if name_from_contact: sender_display_name = name_from_contact
        except Exception as e_get_contact:
            logger.warning("Callback new_msg: Could not get contact name for '%s': %s. Using chat_id.", chat_id, e_get_contact)

    logger.info("Callback new_msg: From '%s' (ID: '%s'). Type: '%s'. Group: %s. FromMe: %s. Body: '%.50s...'",
                sender_display_name, chat_id, message_type, is_group_msg, is_from_me, str(body_content))

    if isinstance(body_content, str) and body_content.strip().lower() == g_ai_toggle_passphrase.lower():
        if chat_id in USER_MESSAGE_TIMERS and USER_MESSAGE_TIMERS[chat_id] and not USER_MESSAGE_TIMERS[chat_id].done():
            USER_MESSAGE_TIMERS[chat_id].cancel() 

        new_ai_state = not AI_IS_ACTIVE 
        g_admin_config["ai_is_active"] = new_ai_state 
        save_admin_config() 
        load_admin_config() 

        status_reply_msg = f"المساعد الآلي الآن {'يعمل (نشط)' if AI_IS_ACTIVE else 'متوقف (غير نشط)'}."
        logger.info("Callback new_msg: AI state toggled by '%s'. New state: %s. Persisted.",
                    sender_display_name, 'ACTIVE' if AI_IS_ACTIVE else 'INACTIVE')
        if wpp_client:
            try: wpp_client.sendText(chat_id, status_reply_msg) # REMOVED await
            except Exception as e_send_status: logger.error("Callback new_msg: Error sending AI toggle status: %s", e_send_status)
        
        await log_interaction_turn(chat_id, "reactive", {
            "role": "system_event", "content": f"AI Toggled to {AI_IS_ACTIVE} by user passphrase in on_new_message.",
            "sender_display_name": sender_display_name
        })
        return 

    is_admin_command_from_self_or_admin = (chat_id == ADMIN_CHAT_ID and isinstance(body_content, str) and body_content.strip().startswith(g_command_prefix))
    if is_from_me and not is_admin_command_from_self_or_admin:
         logger.debug("Callback new_msg: Ignoring self-message from '%s' (not an admin command).", chat_id)
         return
    if is_group_msg:
        logger.debug("Callback new_msg: Ignoring group message from group_id '%s'.", chat_id)
        return
    if not chat_id or ("@c.us" not in chat_id and "@g.us" not in chat_id):
        logger.debug("Callback new_msg: Ignoring message from non-standard chat ID: '%s'", chat_id)
        return
    if not is_admin_command_from_self_or_admin: 
        if message_type != "chat":
            logger.info("Callback new_msg: Ignoring non-'chat' type (type: '%s') from '%s'.", message_type, chat_id)
            return
        if not isinstance(body_content, str) or not body_content.strip():
            logger.info("Callback new_msg: Ignoring empty/non-string body from '%s'.", chat_id)
            return

    if chat_id not in USER_MESSAGE_BUFFERS: USER_MESSAGE_BUFFERS[chat_id] = []
    current_message_part_to_buffer = body_content if isinstance(body_content, str) else str(body_content) 
    USER_MESSAGE_BUFFERS[chat_id].append(current_message_part_to_buffer)

    if chat_id in USER_MESSAGE_TIMERS and USER_MESSAGE_TIMERS[chat_id] and not USER_MESSAGE_TIMERS[chat_id].done():
        USER_MESSAGE_TIMERS[chat_id].cancel()

    if MAIN_EVENT_LOOP:
        USER_MESSAGE_TIMERS[chat_id] = MAIN_EVENT_LOOP.create_task(
            delayed_message_processor(chat_id, sender_display_name, g_message_aggregation_delay) 
        )
    else:
        logger.critical("Callback new_msg: MAIN_EVENT_LOOP is None! Cannot schedule delayed processor for '%s'.", chat_id)
# --- END OF MAIN WHATSAPP MESSAGE CALLBACK (PART 7 MODIFIED) ---

# -----------------------------------------------------------------------------
# Part 8: Main Asynchronous Application Logic (main_async_logic)
# - Calls load_admin_config() and load_outreach_prompts_file() at startup.
# - Ensures INTERACTION_LOGS_DIR exists.
# -----------------------------------------------------------------------------
print("WPP_Ollama_Chat_Assistant_V_ROADMAP_Outreach_Part8_Integrate: Defining main async logic.")

async def main_async_logic():
    global wpp_client, AI_IS_ACTIVE, MAIN_EVENT_LOOP
    global g_admin_config # Other globals are populated by load_admin_config

    # --- Initial Load of Configurations ---
    load_admin_config() # This populates all g_admin_config dependent globals
    load_outreach_prompts_file() # For separate outreach_prompts.json

    # --- Ensure interaction logs directory exists ---
    try:
        log_dir_path = pathlib.Path(INTERACTION_LOGS_DIR)
        if not log_dir_path.is_dir():
            log_dir_path.mkdir(parents=True, exist_ok=True)
            logger.info("Created base directory for interaction logs: %s", INTERACTION_LOGS_DIR)
    except Exception as e_mkdir:
        logger.error("CRITICAL: Could not create interaction logs directory '%s': %s. Persistent logging may fail.", INTERACTION_LOGS_DIR, e_mkdir)
        # Decide if this is fatal enough to exit: sys.exit(1)

    logger.info("Main async: Initializing Assistant. Session: '%s', Headless Mode: %s", YOUR_SESSION_NAME, WPP_HEADLESS_MODE)
    logger.info("Main async: AI configured to start as %s. Toggle: '%s'. Aggregation Delay: %.1fs.",
                'ACTIVE' if AI_IS_ACTIVE else 'INACTIVE', g_ai_toggle_passphrase, g_message_aggregation_delay)
    logger.info("Main async: Ollama Model: '%s'. Endpoint: '%s'. Timeout: %ds.",
                g_ollama_model_name, g_ollama_chat_endpoint, g_ollama_request_timeout)
    logger.info("Main async: Base System Prompt (first 50 chars): '%s...'", g_system_prompt[:50])
    logger.info("Main async: Max Chat History Turns: %d. Ollama Options: %s.", g_max_chat_history_turns, g_ollama_model_options)
    logger.info("Main async: Admin Chat ID: '%s'. Command Prefix: '%s'.", ADMIN_CHAT_ID, g_command_prefix)
    if ADMIN_CHAT_ID == "967774361616@c.us" and ADMIN_CHAT_ID == "YOUR_WHATSAPP_NUMBER@c.us": # Check placeholder
         logger.warning("Main async: CRITICAL - ADMIN_CHAT_ID is not set correctly! Update constant.")
    # ... (Rest of the logging from original Part 8 main_async_logic) ...

    MAIN_EVENT_LOOP = asyncio.get_running_loop()
    if not MAIN_EVENT_LOOP:
        logger.critical("Main async: CRITICAL - Failed to get running asyncio event loop! Cannot proceed."); return
    logger.info("Main async: Main asyncio event loop captured: %s", MAIN_EVENT_LOOP)

    startup_knowledge = load_knowledge_from_file(KNOWLEDGE_FILE_PATH) # Check knowledge file
    if KNOWLEDGE_FILE_PATH and not startup_knowledge:
        logger.warning("Main async: Knowledge file '%s' configured but empty/unreadable.", KNOWLEDGE_FILE_PATH)

    logger.info("Main async: Initialized/Loaded %d custom outreach prompts (from file).", len(g_outreach_prompts))
    logger.info("Main async: Admin config loaded. Current AI Active State: %s", AI_IS_ACTIVE)


    reconnection_attempts_count = 0
    current_reconnect_delay_seconds = float(INITIAL_RECONNECTION_DELAY_SECONDS)

    try:
        while True: # Main operational loop with reconnection
            wpp_client = None; creator_instance = None
            try:
                logger.info("Main async: Starting WPP session attempt #%d...", reconnection_attempts_count + 1)
                # ... (WPP_Whatsapp.Create and client start logic - largely unchanged from original Part 8) ...
                # Example:
                wpp_create_kwargs = { "session": YOUR_SESSION_NAME, "catchQR": True, "logQR": False, "headless": WPP_HEADLESS_MODE }
                if WPP_HEADLESS_MODE and WPP_HEADLESS_BROWSER_ARGS:
                    wpp_create_kwargs['args'] = WPP_HEADLESS_BROWSER_ARGS
                creator_instance = Create(**wpp_create_kwargs)
                
                start_method_to_call = getattr(creator_instance, 'start', getattr(creator_instance, 'start_', None))
                if not start_method_to_call: raise ConnectionError("WPP Creator missing start method.")
                
                if asyncio.iscoroutinefunction(start_method_to_call): wpp_client = await start_method_to_call()
                else: wpp_client = start_method_to_call()
                if not wpp_client: raise ConnectionError("WPP Client init failed.")

                # ... (Connection state checking loop - largely unchanged) ...
                # Example:
                connection_establishment_timeout = 180; connection_wait_start_time = time.time(); is_wpp_connected = False
                logger.info("Main async: Waiting up to %ds for WPP client 'CONNECTED' state...", connection_establishment_timeout)
                while (time.time() - connection_wait_start_time) < connection_establishment_timeout:
                    current_wpp_state = creator_instance.state if creator_instance else "STATE_UNKNOWN"
                    if current_wpp_state == 'CONNECTED':
                        logger.info("Main async: WPP Client 'CONNECTED'!")
                        is_wpp_connected = True; reconnection_attempts_count = 0; current_reconnect_delay_seconds = float(INITIAL_RECONNECTION_DELAY_SECONDS); break
                    # Add other state checks (QRCODE, TIMEOUT, etc.)
                    await asyncio.sleep(3)
                if not is_wpp_connected:
                    raise ConnectionError(f"WPP Connection Timeout. Final state: {creator_instance.state if creator_instance else 'N/A'}")

                retrieved_wa_version = await get_wa_version_async(wpp_client)
                logger.info("Main async: Connected to WhatsApp Web version: '%s'", retrieved_wa_version)
                
                if MAIN_EVENT_LOOP and wpp_client:
                    def message_handler_wrapper(msg_dict_from_wpp):
                        # This wrapper ensures on_new_message_received runs in the main event loop
                        future = asyncio.run_coroutine_threadsafe(on_new_message_received(msg_dict_from_wpp), MAIN_EVENT_LOOP)
                        try: future.result(timeout=30) # Optional: Add a timeout for the callback processing itself
                        except Exception as e_future_exc: logger.error("Main Loop Callback: EXCEPTION in on_new_message_received: %s", e_future_exc, exc_info=True)
                    
                    wpp_client.onMessage(message_handler_wrapper)
                    logger.info("--- Main async: Ollama Outreach Assistant IS LIVE! Listening for messages... ---")
                else:
                    raise Exception("Critical setup: Event loop or WPP client not available for onMessage.")

                # --- Main Keep-Alive and Connection Monitoring Loop ---
                while True:
                    await asyncio.sleep(30)
                    current_wpp_state_monitoring = creator_instance.state if creator_instance else "N/A_NO_CREATOR"
                    logger.debug("Main async: Keep-alive. AI Active: %s. WPP State: '%s'. Model: '%s'.", AI_IS_ACTIVE, current_wpp_state_monitoring, g_ollama_model_name)
                    if not creator_instance or current_wpp_state_monitoring != 'CONNECTED':
                        logger.warning("Main async: WhatsApp connection lost or creator invalid! State: '%s'. Reconnecting.", current_wpp_state_monitoring)
                        raise ConnectionAbortedError("WhatsApp connection lost during operation.")
            
            except (ConnectionError, ConnectionAbortedError) as e_conn:
                logger.error("Main async: Connection issue (Attempt #%d): %s. Retrying.", reconnection_attempts_count + 1, e_conn)
            except Exception as e_inner_unexpected:
                logger.error("Main async: UNEXPECTED ERROR in WPP setup/monitor (Attempt #%d): %s. Retrying.", reconnection_attempts_count + 1, e_inner_unexpected, exc_info=True)
            
            if wpp_client: wpp_client = None
            if creator_instance: await close_creator_async(creator_instance); creator_instance = None
            
            reconnection_attempts_count += 1
            if MAX_RECONNECTION_ATTEMPTS != 0 and reconnection_attempts_count >= MAX_RECONNECTION_ATTEMPTS:
                logger.critical("Main async: Max reconnection attempts (%d) reached. Terminating.", MAX_RECONNECTION_ATTEMPTS)
                break # Exit main operational loop

            logger.info("Main async: Reconnection attempt #%d/%s in %d seconds...",
                        reconnection_attempts_count, MAX_RECONNECTION_ATTEMPTS if MAX_RECONNECTION_ATTEMPTS !=0 else "infinite",
                        int(current_reconnect_delay_seconds))
            await asyncio.sleep(current_reconnect_delay_seconds)
            current_reconnect_delay_seconds = min(current_reconnect_delay_seconds * RECONNECTION_DELAY_MULTIPLIER, float(MAX_RECONNECTION_DELAY_SECONDS))

    except KeyboardInterrupt:
        logger.info("Main async: KeyboardInterrupt. Shutting down.")
    except Exception as e_main_fatal:
        logger.error("Main async: FATAL UNEXPECTED ERROR: %s", e_main_fatal, exc_info=True)
    finally:
        logger.info("Main async: Final cleanup process initiated...")
        # ... (Timer cancellation logic from original Part 8) ...
        active_timer_tasks_to_cancel = [task for task in USER_MESSAGE_TIMERS.values() if task and not task.done()]
        if active_timer_tasks_to_cancel:
            logger.info("Main async: Cancelling %d outstanding message timers...", len(active_timer_tasks_to_cancel))
            for task in active_timer_tasks_to_cancel: task.cancel()
            await asyncio.gather(*active_timer_tasks_to_cancel, return_exceptions=True)
            logger.info("Main async: Message timers cancellation processed.")

        if 'creator_instance' in locals() and creator_instance:
            logger.info("Main async: Final attempt to close WPP creator instance...")
            await close_creator_async(creator_instance)
        logger.info("--- Main async: Ollama Outreach Assistant Terminated ---")
# -----------------------------------------------------------------------------
# --- END OF MAIN ASYNCHRONOUS APPLICATION LOGIC (PART 8 MODIFIED) ---
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Part 9: Script Entry Point (__main__)
# - Largely UNCHANGED.
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    current_script_name = os.path.basename(sys.argv[0] if sys.argv and sys.argv[0] else __file__)
    print(f"Starting script: {current_script_name} at {time.ctime()}.")
    try:
        # Ensure INTERACTION_LOGS_DIR exists before asyncio.run, as logging might happen early
        # Though main_async_logic also checks, this is an earlier check.
        pathlib.Path(INTERACTION_LOGS_DIR).mkdir(parents=True, exist_ok=True)
        asyncio.run(main_async_logic())
    except KeyboardInterrupt:
        print(f"{current_script_name}: Application terminated by user (KeyboardInterrupt in __main__) at {time.ctime()}.")
    except Exception as e_fatal_top_level:
        print(f"{current_script_name}: FATAL UNHANDLED ERROR at top level: {e_fatal_top_level}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"{current_script_name}: Script __main__ block finished at {time.ctime()}.")
# -----------------------------------------------------------------------------
# --- END OF SCRIPT ENTRY POINT (PART 9 UNCHANGED) ---
# --- END OF SCRIPT ---
# -----------------------------------------------------------------------------


