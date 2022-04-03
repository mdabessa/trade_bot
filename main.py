import traceback

from modules.config import (
    API_KEY,
    API_SECRET,
    DISCORD_WEBHOOK_URL,
    DISCORD_WEBHOOK_USERNAME,
    DISCORD_WEBHOOK_AVATAR,
    DISCORD_USER_ID_MENTION,
    COINS,
    STRATEGY,
)
from modules.logger import DiscordLogger, Logger
from modules.manager import ManagerBinance
from modules.strategy import StrategyRelative as Strategy
from modules.models import Header

configs = STRATEGY["relative"]

if DISCORD_WEBHOOK_URL:
    logger = DiscordLogger(
        webhook_url=DISCORD_WEBHOOK_URL,
        avatar_url=DISCORD_WEBHOOK_AVATAR,
        webhook_username=DISCORD_WEBHOOK_USERNAME,
        fname="./logs/log.txt",
    )

else:
    logger = Logger("./logs/log.txt")

manager = ManagerBinance(
    logger=logger,
    coins_symbols=COINS,
    api_key=API_KEY,
    api_secret=API_SECRET,
    keep_historic=1440,
)

strategy = Strategy(manager, configs)

if __name__ == "__main__":
    try:
        strategy.run(delay=60)
    except Exception as e:
        if ("Connection reset by peer" in str(e)) or ("Read timed out." in str(e)):
            logger("Connection reset by peer or Read timed out.")

        else:
            logger(str(e), mention_id=DISCORD_USER_ID_MENTION)
            t = str(traceback.format_exc())
            logger(t, file=True)
            scout = Header.create_update("scout", "1", type_="bool")
