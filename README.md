# BNU Discord Bot

## Overview

The BNU Discord Bot is a bot designed to interact with the Kavita manga server, providing users with easy access to manga information, recent chapters, and other functionalities directly within Discord.

## Features

- Fetch and display series information from the Kavita server.
- Retrieve and show recent chapters with relevant metadata.
- Embed chapter information with links for reading.
- Support for handling user reactions to trigger specific actions.
- Customizable embeds for chapter and series display.

## Installation

### Prerequisites

- Python 3.8 or higher
- A Discord bot token
- Access to a running Kavita server

### Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/hillmanation/bnu-discord-bot.git
   cd bnu-discord-bot
   ```

2. Create a virtual environment and activate it:

    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
   ```
   
3. Install the required packages:
    ```bash
    pip install -r requirements.txt
    ```

4. Set your Discord bot token and Kavita server URL in a configuration file or environment variables.

### Usage
To run the bot, execute the following command:
```bash
python src/bnu-discord-bot.py
```

### Commands
- Reaction to Manga Titles: Users can react to messages with specific emojis to fetch and display detailed information about the manga series, including recent chapters.
- Chapter Embeds: Upon reacting, the bot sends an embed containing the chapter title, release date, page count, and a link to read the chapter.
### Code Structure
- `src/`: Contains the main bot script and entry point.
- `api/`: Contains modules for interacting with the Discord API and the Kavita server.
- `utilities/`: Contains helper functions and classes for building embeds and handling data.  

## Contributing

Contributions are welcome! If you have suggestions or improvements, please fork the repository and submit a pull request.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.

## Acknowledgements
Thanks to the creators of Kavita for providing the manga server.
Thanks to the discord.py library for making bot development easy.


### Customization

Feel free to adjust any sections, such as the repository link, setup instructions, or features, to better match your project's specifics. Let me know if you need any further changes!
