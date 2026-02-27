from config import logger
from backend.services.monitor import Newsroom

from dotenv import load_dotenv

load_dotenv()

def main():
    """Initialize and run the admin dashboard"""

    logger.debug("Initializing Newsroom Dashboard.")
    dashboard = Newsroom()
    dashboard.run()


if __name__ == "__main__":
    main()
