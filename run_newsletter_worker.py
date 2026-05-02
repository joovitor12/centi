"""Run scheduled newsletter delivery worker."""

import asyncio
import logging

from app.workers.newsletter_worker import run_newsletter_worker

logging.basicConfig(level=logging.INFO)


if __name__ == "__main__":
    asyncio.run(run_newsletter_worker())
