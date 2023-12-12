"""ONYX API event thread."""
import asyncio
import logging
import threading
from random import uniform

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api_connector import APIConnector
from .const import MAX_BACKOFF_TIME

_LOGGER = logging.getLogger(__name__)


class EventThread(threading.Thread):
    """The event thread for asynchronous updates."""

    def __init__(
        self,
        api: APIConnector,
        coordinator: DataUpdateCoordinator,
        force_update: bool = False,
        backoff=True,
    ):
        threading.Thread.__init__(self, name="HellaOnyx")
        self._api = api
        self._coordinator = coordinator
        self._force_update = force_update
        self._backoff = backoff

    async def _update(self):
        """Listen for updates."""
        while True:
            backoff = int(uniform(0, MAX_BACKOFF_TIME) * 60)
            try:
                async for device in self._api.events(self._force_update):
                    self._api.updated_device(device)
                    self._coordinator.async_set_updated_data(None)
            except Exception as ex:
                _LOGGER.error(
                    "connection reset: %s, restarting with backoff of %s seconds (%s)",
                    ex,
                    backoff,
                    self._backoff,
                )
            if self._backoff:
                await asyncio.sleep(backoff)
            else:
                break

    def run(self):
        """Start the thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.create_task(self._update())
        loop.run_forever()
