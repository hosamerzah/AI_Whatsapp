# AI_Whatsapp

A powerful, customizable WhatsApp assistant powered by Python, `wpp-whatsapp`, and a local Ollama LLM. This project is designed to act as a configurable "AI employee" on WhatsApp, capable of handling reactive conversations, executing targeted outreach campaigns, and being managed entirely through admin commands.

## Key Features

- **Dual AI Context:** Intelligently separates "Reactive" chat (general conversation) from "Outreach" chat (specific, goal-oriented campaigns), each with its own history and system prompt.
- **Persistent Configuration:** All admin settings are saved in an `admin_config.json` file, so your customizations persist across restarts.
- **Admin Approval Workflow:** Initiate outreach campaigns in a "prepared" state, allowing you to review and approve the AI's first message before it's sent.
- **Durable Interaction Logging:** Every conversation is saved to organized `.jsonl` log files for auditing, debugging, and future analysis, without impacting live performance.
- **Deep Customization:** Control the AI's persona, goals, interaction style, and LLM parameters on the fly via WhatsApp commands.
- **Remote Browser Control:** Open, close, and restart the underlying WhatsApp Web browser instance via admin commands.
- **Dual Licensing:** Free for personal, non-commercial use with attribution. A paid license is required for commercial applications.

## License

This project is released under a **Dual License**. Please choose the one that fits your use case.

- **🧑‍💻 For Individuals, Students, and Non-Commercial Use:** The code is available under the [Creative Commons BY-NC 4.0 License](https://creativecommons.org/licenses/by-nc/4.0/). You are free to use, share, and adapt it, but you must give appropriate credit and cannot use it for commercial purposes.

- **🏢 For Companies and Commercial Use:** If you intend to use this software for any commercial purpose (e.g., in a for-profit business, as part of a paid product or service), you must purchase a commercial license. Please contact the author, **eng.alzubairy**, at **eng.alzubairy27@gmail.com** to inquire about a commercial license.

For full details, please see the [LICENSE](LICENSE) file.

## Requirements

### Software Prerequisites

You must have the following software installed on your system:

1.  **Python:** Version 3.9 or newer. You can download it from [python.org](https://www.python.org/downloads/).
2.  **Ollama:** The Ollama server application must be installed and running. Download it from [ollama.com](https://ollama.com/).
3.  **An Ollama Model:** You need at least one model pulled. For example, in your terminal:
    ```bash
    ollama pull gemma3:4b
    ```
4.  **Google Chrome:** The `wpp-whatsapp` library requires the Google Chrome or Chromium browser.
5.  **Git:** Required for cloning this repository. Download it from [git-scm.com](https://git-scm.com/).

### Python Libraries

All required Python libraries are listed in the `requirements.txt` file.

## Installation

1.  **Clone the repository:**
    Open your terminal or command prompt and run:
    ```bash
    git clone <URL_of_your_GitHub_repository>
    cd <repository_folder_name>
    ```

2.  **Install Python dependencies:**
    Run the following command in the project folder to install all necessary libraries:
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

1.  **First Run:** The first time you run the script, it will automatically generate a default `admin_config.json` file.

2.  **⚠️ CRITICAL STEP: Set Your Admin Number**
    -   After the first run, **stop the script**.
    -   Open the newly created `admin_config.json` file.
    -   Find the line for `ADMIN_CHAT_ID` (this is a constant in the code, you should move it into the config file if you haven't already, or just set it in the script). For this project, you've set it directly in the script. **Ensure `ADMIN_CHAT_ID: str = "YOUR_NUMBER@c.us"` is set correctly with your WhatsApp number.** The AI will not respond to admin commands from any other number.

3.  **Review Other Settings (Optional):**
    You can review and change other default settings in `admin_config.json`, such as the `ollama_model_name`, `message_aggregation_delay_seconds`, or predefined messages.

## Running the Script

1.  Make sure your Ollama server is running in the background.
2.  Execute the main Python script from your terminal:
    ```bash
    python AIaspects.py
    ```
3.  On the first run for a new session, you will likely need to scan a QR code with your phone to link WhatsApp Web. The script will wait for you to do this.
4.  Once connected, the console will show "--- Main async: Ollama Outreach Assistant IS LIVE! ---".

## Usage (Admin Commands)

All management of the AI is done through your designated Admin WhatsApp account. Send messages starting with the command prefix (default is `$`).

-   To see a full list of commands, send:
    ```
    $help
    ```
-   To check the current status of the AI and its configuration:
    ```
    $status
    ```
-   To see available Ollama models you can switch to:
    ```
    $listmodels
    ```
-   To change the active LLM model:
    ```
    $setmodel gemma:2b
    ```

## Disclaimer

This software is provided "as-is", for fun, and without any warranty. The author is not responsible for any misuse or improper practices related to this software. Use it responsibly.