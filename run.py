# --- START OF FILE run.py ---

import asyncio
import logging
import sys
import os
import pathlib

# Import the brain and the limbs
import core_logic
import whatsapp_connector
import telegram_connector

# --- CONFIGURATION ---
ADMIN_CONFIG_FILE_PATH = "./admin_config.json"
# We can add more high-level script configs here if needed later

# --- LOGGER SETUP ---
def setup_logger():
    """Sets up the global logger for the application."""
    logger = logging.getLogger("OllamaWhatsAppAssistant")
    logger.setLevel(logging.DEBUG) # Set the lowest level to capture all messages
    
    # Prevent adding handlers multiple times if this function is called again
    if logger.hasHandlers():
        logger.handlers.clear()

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO) # Only show INFO and above in the console
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File Handler
    try:
        log_file_path = "assistant_main.log"
        file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG) # Log everything to the file
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.error(f"Failed to set up file logger: {e}")

    logger.propagate = False
    # Set log level for external libraries if they are too noisy
    logging.getLogger("WPP_Whatsapp").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING) # python-telegram-bot uses httpx which can be verbose

    return logger

# --- MAIN ORCHESTRATOR ---
async def main():
    """
    Main function to initialize and run all connectors concurrently.
    """
    logger = setup_logger()
    logger.info("==============================================")
    logger.info("   Starting Multi-Platform AI Assistant")
    logger.info("==============================================")
    
    # 1. Load the central configuration
    # The core_logic module will hold the config in its global state, accessible by all connectors.
    core_logic.load_admin_config(ADMIN_CONFIG_FILE_PATH)
    logger.info("Core logic and admin configuration initialized.")

    # 2. Prepare the tasks for each connector
    # We create a list of coroutines to run.
    tasks = []
    
    # WhatsApp Connector Task
    # Note: We can add a toggle in admin_config.json to enable/disable each platform
    if core_logic.g_admin_config.get("whatsapp_settings", {}).get("enabled", True):
        whatsapp_config = core_logic.g_admin_config.get("whatsapp_settings", {})
        whatsapp_task = asyncio.create_task(whatsapp_connector.start_whatsapp_client(
            session_name=whatsapp_config.get("session_name", "default_session"),
            headless=whatsapp_config.get("headless_mode", False),
            browser_args=whatsapp_config.get("browser_args", [])
        ))
        tasks.append(whatsapp_task)
        logger.info("WhatsApp connector task created.")
    else:
        logger.warning("WhatsApp connector is disabled in the configuration.")

    # Telegram Connector Task
    if core_logic.g_admin_config.get("telegram_settings", {}).get("enabled", True):
        telegram_task = asyncio.create_task(telegram_connector.start_telegram_bot())
        tasks.append(telegram_task)
        logger.info("Telegram connector task created.")
    else:
        logger.warning("Telegram connector is disabled in the configuration.")
        
    if not tasks:
        logger.critical("No connectors are enabled. The application has nothing to do. Exiting.")
        return

    # 3. Run the tasks concurrently
    logger.info("Running all enabled connectors...")
    
    # We'll use asyncio.gather to run them. If one task fails, it can bring down the others.
    # We set return_exceptions=True to inspect errors without crashing the orchestrator immediately.
    done, pending = await asyncio.wait(
        tasks,
        return_when=asyncio.FIRST_COMPLETED,
    )

    # 4. Handle shutdown
    # If any task finishes (or crashes), we'll gracefully shut down the others.
    logger.warning("A connector task has finished or failed. Initiating shutdown of all other tasks.")
    for task in pending:
        task.cancel()
    
    # Wait for all tasks to be cancelled
    await asyncio.gather(*pending, return_exceptions=True)
    logger.info("All connector tasks have been shut down.")
    
    # Check for exceptions in the completed tasks
    for task in done:
        try:
            task.result()
        except asyncio.CancelledError:
            pass # This is expected during shutdown
        except Exception as e:
            logger.critical(f"A task exited with a critical error: {e}", exc_info=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nApplication terminated by user (Ctrl+C).")
    except Exception as e:
        print(f"A fatal error occurred in the main orchestrator: {e}")

# --- END OF FILE run.py ---