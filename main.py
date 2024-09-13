import asyncio
from api.bnu_api import bnuAPI


def main():
    # Initialize the discord bot
    discordAPI = bnuAPI()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(discordAPI.authenticate())


if __name__ == "__main__":
    main()
