"""
Shared service initialization for HTTP and gRPC servers.

Provides common startup logic to avoid code duplication.
"""

from agent.utils.logging import get_logger

logger = get_logger(__name__)


async def initialize_intent_router() -> None:
    """
    Initialize IntentRouter eagerly during application startup.

    Benefits:
    - Avoids 500-1000ms latency spike on first request
    - Catches configuration errors early (fail-fast)
    - Prevents race conditions from concurrent initializations

    This function is safe to call multiple times (idempotent).
    If initialization fails, logs error and continues with keyword fallback.
    """
    try:
        from agent.intent_router.intent_routing import get_intent_router

        logger.info("Initializing IntentRouter...")
        intent_router = get_intent_router()
        await intent_router.initialize()
        logger.info("✅ IntentRouter initialized successfully")

    except Exception as e:
        logger.error(
            f"❌ Failed to initialize IntentRouter: {e}",
            exc_info=True,
            extra={
                "event": "intent_router_init_failed",
                "error": str(e)
            }
        )
        logger.warning(
            "IntentRouter will fallback to keyword-based routing. "
            "Vector DB routing will not be available."
        )


async def initialize_all_services() -> None:
    """
    Initialize all application services during startup.

    Add new services here as needed. Each service should handle
    its own errors gracefully.
    """
    logger.info("Starting service initialization...")

    # Initialize IntentRouter
    await initialize_intent_router()

    # Add more services here in the future:
    # await initialize_vector_db()
    # await initialize_cache()
    # etc.

    logger.info("Service initialization complete!")


async def cleanup_services() -> None:
    """
    Cleanup services during application shutdown.

    Add cleanup logic here as needed.
    """
    logger.info("Cleaning up services...")

    # Add cleanup logic here
    # await vector_db.close()
    # await cache.close()

    logger.info("Service cleanup complete!")

