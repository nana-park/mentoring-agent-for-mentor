"""Compatibility entry point for retrospective generation."""
import asyncio
from mentoring.services.summarize_insights import main

if __name__ == "__main__":
    asyncio.run(main())
