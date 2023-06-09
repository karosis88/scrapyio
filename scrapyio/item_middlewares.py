from abc import ABC, abstractmethod

from scrapyio.items import Item


class BaseItemMiddleWare(ABC):
    @abstractmethod
    async def process_item(self, item: Item) -> None:
        ...
