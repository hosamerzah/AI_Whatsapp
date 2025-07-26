# --- START OF FILE telegram_connector.py ---

import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio 
# Import the brain
import core_logic

logger = logging.getLogger("OllamaWhatsAppAssistant")

# --- Telegram Specific Functions ---

def get_chat_id(update: Update) -> str:
    """Extracts the chat ID from a Telegram update."""
    return str(update.effective_chat.id)

def get_display_name(update: Update) -> str:
    """Extracts a display name from a Telegram update."""
    user = update.effective_user
    if user:
        if user.first_name and user.last_name:
            return f"{user.first_name} {user.last_name}"
        return user.first_name or user.username or "Telegram User"
    return "Unknown Telegram User"

async def send_reply(context: ContextTypes.DEFAULT_TYPE, chat_id: str, text: str):
    """Sends a text message to a chat ID on Telegram."""
    if not text:
        logger.warning("Telegram Connector: send_reply called with empty text for chat_id %s. Nothing sent.", chat_id)
        return
    try:
        await context.bot.send_message(chat_id=chat_id, text=text)
        logger.info("Telegram Connector: Reply sent to chat_id %s.", chat_id)
    except Exception as e:
        logger.error("Telegram Connector: Failed to send message to chat_id %s: %s", chat_id, e, exc_info=True)

async def handle_platform_actions(context: ContextTypes.DEFAULT_TYPE, chat_id: str, actions: list):
    """Handles platform-specific actions requested by core_logic."""
    # This is a placeholder for now. We don't have Telegram-specific actions yet.
    # But if core_logic returned something like {'action': 'send_telegram_sticker'}, we'd handle it here.
    if not actions:
        return
    logger.info("Telegram Connector: Received platform actions for chat_id %s: %s", chat_id, actions)
    # Example action handling:
    # for action in actions:
    #     if action.get('action') == 'some_telegram_action':
    #         await context.bot.send_sticker(chat_id=chat_id, sticker=action.get('sticker_id'))


# --- Message Handlers for Telegram ---

async def incoming_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming text messages and commands from Telegram."""
    message = update.message
    if not message or not message.text:
        return

    chat_id = get_chat_id(update)
    sender_name = get_display_name(update)
    raw_text = message.text

    # --- Command Conversion ---
    # Convert Telegram '/' commands to our internal '$' prefix format
    # This makes the core_logic handler completely platform-agnostic.
    processed_text = raw_text
    if raw_text.startswith('/'):
        # Check if user is a Telegram admin before processing as a command
        if core_logic.is_admin("telegram", chat_id):
            command_part = raw_text.split(' ')[0]
            # Convert `/command` to `$command`
            processed_text = core_logic.g_command_prefix + command_part[1:]
            # Re-join with arguments if any
            if ' ' in raw_text:
                processed_text += ' ' + ' '.join(raw_text.split(' ')[1:])
            logger.info("Telegram Connector: Converted Telegram command '%s' to internal format '%s'", raw_text, processed_text)
        else:
            # If a non-admin user tries to use a command, treat it as regular text
            logger.info("Telegram Connector: Non-admin user %s tried to use command '%s'. Treating as text.", sender_name, raw_text)

    # --- Pass to Core Logic for Processing ---
    logger.info("Telegram Connector: Passing message from '%s' (%s) to core logic.", sender_name, chat_id)
    
    # We will call a simplified process_message for now, without aggregation.
    # The aggregation timer logic would be more complex to implement here and is a good next step.
    replies = await core_logic.process_message(
        platform="telegram",
        chat_id=chat_id,
        sender_name=sender_name,
        message_text=processed_text
    )

    # --- Handle Replies from Core Logic ---
    if not replies:
        logger.info("Telegram Connector: Core logic returned no replies for message from %s.", sender_name)
        return

    for reply in replies:
        target_id = reply.get('target_id')
        text_to_send = reply.get('text')
        platform_actions = reply.get('platform_actions', [])

        await send_reply(context, target_id, text_to_send)
        await handle_platform_actions(context, target_id, platform_actions)


# (in telegram_connector.py)

async def start_telegram_bot():
    """Initializes and starts the Telegram bot listener in a non-blocking way."""
    logger.info("Telegram Connector: Starting bot...")
    
    bot_token = core_logic.g_admin_config.get("telegram_settings", {}).get("bot_token")
    if not bot_token or bot_token == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        logger.error("Telegram Connector: Bot token is missing. Bot will not start.")
        return

    application = Application.builder().token(bot_token).build()

# Use a simpler filter that just accepts any text or command that isn't an edit.
    application.add_handler(MessageHandler(filters.TEXT & ~filters.UpdateType.EDITED_MESSAGE, incoming_message_handler))
    
    # --- NON-BLOCKING STARTUP SEQUENCE ---
    try:
        # Add the debug handler with a low priority (high number) so it runs after our main handler
        application.add_handler(MessageHandler(filters.ALL, debug_all_updates), group=-1)
        await application.initialize()
        # Initialize the application (connects to Telegram, etc.)
        logger.info("Telegram Connector: Application initialized.")
        
        # Start fetching updates. This runs in the background.
        await application.start()
        logger.info("Telegram Connector: Polling for messages started.")
        
        # Keep the task alive indefinitely until it's cancelled from the outside.
        # This is crucial for our orchestrator in run.py
        while True:
            await asyncio.sleep(3600) # Sleep for a long time, can be interrupted by cancellation

    except asyncio.CancelledError:
        # This is the expected way to stop the bot when run.py shuts down
        logger.info("Telegram Connector: Task cancelled. Shutting down bot gracefully...")
    except Exception as e:
        logger.critical("Telegram Connector: A critical error occurred: %s", e, exc_info=True)
    finally:
        # Ensure cleanup happens
        if application.running:
            logger.info("Telegram Connector: Stopping polling...")
            await application.stop()
        logger.info("Telegram Connector: Shutting down application...")
        await application.shutdown()
        logger.info("Telegram Connector: Bot has been shut down.")


async def debug_all_updates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """A simple handler to log the raw JSON of any incoming update."""
    logger.debug(f"TELEGRAM DEBUG: Received an update of type {type(update)}:\n{update.to_json()}")