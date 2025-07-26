# --- START OF FILE whatsapp_connector.py ---

import logging
import asyncio
import time

# Import the brain
import core_logic

try:
    from WPP_Whatsapp import Create
except ImportError as e:
    print(f"CRITICAL IMPORT ERROR for WPP_Whatsapp: {e}")
    exit(1)

logger = logging.getLogger("OllamaWhatsAppAssistant")

# --- GLOBAL STATE FOR WHATSAPP CONNECTOR ---
wpp_client = None
creator_instance = None
main_event_loop = None

# --- WHATSAPP SPECIFIC HELPER FUNCTIONS ---

async def get_wa_version_async(client_instance) -> str:
    """Gets the WhatsApp Web version."""
    if not client_instance or not hasattr(client_instance, 'getWAVersion'):
        return "N/A"
    try:
        version = await client_instance.getWAVersion()
        return str(version) if version else "N/A"
    except Exception as e:
        logger.warning("WhatsApp Connector: Could not retrieve WA version: %s", e)
        return "Error"

async def close_creator_async():
    """Safely closes the WPP creator instance."""
    global creator_instance, wpp_client
    if not creator_instance:
        return
    
    local_creator = creator_instance
    creator_instance = None # Set to None immediately to prevent reuse
    wpp_client = None

    logger.info("WhatsApp Connector: Attempting to close WPP creator instance...")
    try:
        if hasattr(local_creator, 'sync_close'):
            await asyncio.to_thread(local_creator.sync_close)
        elif hasattr(local_creator, 'close'):
            await local_creator.close()
        logger.info("WhatsApp Connector: WPP creator instance closed successfully.")
    except Exception as e:
        logger.error("WhatsApp Connector: Exception during creator close: %s", e, exc_info=True)

async def send_reply(chat_id: str, text: str):
    """Sends a text message to a chat ID on WhatsApp."""
    if not wpp_client:
        logger.error("WhatsApp Connector: Cannot send reply, wpp_client is not active.")
        return
    if not text:
        logger.warning("WhatsApp Connector: send_reply called with empty text for chat_id %s. Nothing sent.", chat_id)
        return
    try:
        wpp_client.sendText(chat_id, text)
        logger.info("WhatsApp Connector: Reply sent to chat_id %s.", chat_id)
    except Exception as e:
        logger.error("WhatsApp Connector: Failed to send message to chat_id %s: %s", chat_id, e, exc_info=True)

async def handle_platform_actions(actions: list):
    """Handles platform-specific actions for WhatsApp requested by core_logic."""
    global wpp_client, creator_instance
    if not actions:
        return
    
    logger.info("WhatsApp Connector: Received platform actions: %s", actions)
    for action in actions:
        action_type = action.get('action')
        if action_type in ['restart_whatsapp', 'open_whatsapp']:
            logger.info("WhatsApp Connector: Executing '%s' action.", action_type)
            # This is a complex action that requires tearing down and rebuilding the connection.
            # The main_async_logic loop handles this naturally.
            # Here, we can trigger the teardown. The loop will then handle the restart.
            await close_creator_async()
            # The main loop will now see that creator_instance is None and start a new connection attempt.
        elif action_type == 'close_whatsapp':
            logger.info("WhatsApp Connector: Executing '%s' action.", action_type)
            await close_creator_async()
            # The main loop needs to know not to restart automatically. We can use a flag for this.
            # This is an advanced feature to add later. For now, close will trigger a reconnect.

# --- MESSAGE HANDLER FOR WHATSAPP ---

async def on_new_message_received(message: dict):
    """Callback for new WhatsApp messages. Passes them to the core logic."""
    if not message or not isinstance(message, dict) or message.get("type") != "chat":
        return
    
    chat_id = message.get("from")
    body_content = message.get("body")
    
    if not chat_id or not body_content or not isinstance(body_content, str) or not body_content.strip():
        return
    
    sender_name = chat_id # Fallback
    if wpp_client:
        try:
            contact = await asyncio.to_thread(wpp_client.getContact, chat_id)
            if contact:
                sender_name = contact.get("name") or contact.get("pushname") or chat_id
        except Exception:
            pass # Ignore if contact can't be fetched

    logger.info("WhatsApp Connector: Passing message from '%s' (%s) to core logic.", sender_name, chat_id)
    
    # --- TODO: Implement Message Aggregation Here ---
    # For now, we process messages one by one for consistency with the Telegram connector.
    
    replies = await core_logic.process_message(
        platform="whatsapp",
        chat_id=chat_id,
        sender_name=sender_name,
        message_text=body_content.strip()
    )

    if not replies:
        logger.info("WhatsApp Connector: Core logic returned no replies for message from %s.", sender_name)
        return

    for reply in replies:
        target_id = reply.get('target_id')
        text_to_send = reply.get('text')
        platform_actions = reply.get('platform_actions', [])
        
        await send_reply(target_id, text_to_send)
        await handle_platform_actions(platform_actions)

# --- MAIN CONNECTION LOGIC FOR WHATSAPP ---

async def start_whatsapp_client(session_name: str, headless: bool, browser_args: list):
    """
    Initializes and runs the main connection and reconnection loop for WhatsApp.
    """
    global wpp_client, creator_instance, main_event_loop
    main_event_loop = asyncio.get_running_loop()

    # Reconnection settings from config (or use defaults)
    reconnect_settings = core_logic.g_admin_config.get("reconnection_settings", {
        "max_attempts": 5, "initial_delay": 20, "multiplier": 1.5, "max_delay": 180
    })
    
    reconnection_attempts = 0
    reconnect_delay = reconnect_settings["initial_delay"]
    
    while True:
        if creator_instance is not None:
            # This is the keep-alive check
            if creator_instance.state != 'CONNECTED':
                logger.warning("WhatsApp Connector: Connection lost! State is '%s'. Triggering reconnect.", creator_instance.state)
                await close_creator_async()
            else:
                await asyncio.sleep(30) # Wait 30s before next keep-alive check
                continue

        # If we are here, it means creator_instance is None, so we need to connect.
        logger.info("WhatsApp Connector: Starting new session attempt...")
        try:
            wpp_create_kwargs = {"session": session_name, "catchQR": True, "logQR": False, "headless": headless}
            if headless and browser_args:
                wpp_create_kwargs['args'] = browser_args
            
            creator_instance = Create(**wpp_create_kwargs)
            
            start_method = getattr(creator_instance, 'start', None)
            if not start_method: raise ConnectionError("WPP Creator missing 'start' method.")
            
            wpp_client = start_method()
            if not wpp_client: raise ConnectionError("WPP Client initialization failed.")

            # Wait for connection
            timeout = 180
            start_time = time.time()
            connected = False
            while time.time() - start_time < timeout:
                if creator_instance.state == 'CONNECTED':
                    wa_version = await get_wa_version_async(wpp_client)
                    logger.info("WhatsApp Connector: Successfully connected to WhatsApp Web v%s", wa_version)
                    
                    # Attach the message handler
                    def message_handler_wrapper(msg):
                        asyncio.run_coroutine_threadsafe(on_new_message_received(msg), main_event_loop)
                    
                    wpp_client.onMessage(message_handler_wrapper)
                    
                    reconnection_attempts = 0
                    reconnect_delay = reconnect_settings["initial_delay"]
                    connected = True
                    break
                await asyncio.sleep(3)
            
            if not connected:
                raise ConnectionError(f"Connection timeout after {timeout} seconds. Final state: {creator_instance.state}")

        except Exception as e:
            logger.error("WhatsApp Connector: Failed to connect: %s", e, exc_info=True)
            await close_creator_async() # Ensure cleanup
            
            reconnection_attempts += 1
            max_attempts = reconnect_settings["max_attempts"]
            if max_attempts != 0 and reconnection_attempts >= max_attempts:
                logger.critical("WhatsApp Connector: Maximum reconnection attempts reached. Shutting down WhatsApp connector.")
                break # Exit the while loop
            
            logger.info("WhatsApp Connector: Reconnecting in %d seconds...", reconnect_delay)
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * reconnect_settings["multiplier"], reconnect_settings["max_delay"])

# --- END OF FILE whatsapp_connector.py ---