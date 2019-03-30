import asyncio

#-------------------------------------------------------------------------------

async def cancel_task(task, name, log):
    """
    Cancels and cleans up `task`, with logging as `name`.
    """
    log.info(f"canceling {name} task")
    if task.cancelled():
        log.info(f"{name} task already canceled")
    else:
        task.cancel()

    try:
        return await task
    except asyncio.CancelledError:
        log.info(f"{name} task canceled")


