import asyncio
import inspect
import logging
import typing
from contextlib import suppress
from warnings import warn

import httpx

from scrapyio import Request
from scrapyio.downloader import BaseDownloader, Downloader
from scrapyio.exceptions import (
    DownloadFailedException,
    InvalidParseMethodException,
    InvalidYieldValueException,
    ParseFailedException,
)
from scrapyio.http import clean_up_response
from scrapyio.items import ItemManager
from scrapyio.spider import BaseSpider, Item
from scrapyio.types import CLEANUP_WITH_RESPONSE, DOWNLOADER_EXCEPTION_CALLBACK

log = logging.getLogger("scrapyio")


class Engine:
    downloader_class: typing.ClassVar[typing.Type[BaseDownloader]] = Downloader

    def __init__(
        self,
        spider: BaseSpider,
        downloader: typing.Optional[BaseDownloader] = None,
        items_manager: typing.Optional[ItemManager] = None,
        loop_delay: int = 0,
        downloader_exception_callback: typing.Optional[
            DOWNLOADER_EXCEPTION_CALLBACK
        ] = None,
    ):
        self.spider = spider
        self.loop_delay = loop_delay

        self.downloader: BaseDownloader
        if downloader is None:
            self.downloader = self.downloader_class()
        else:
            self.downloader = downloader

        self.downloader_exception_callback = downloader_exception_callback
        self.items_manager = items_manager
        if self.items_manager is None:
            warn(
                "Because no `items_manager` was specified, all items"
                " yielded by the 'parse' method will be ignored.",
                RuntimeWarning,
            )

    async def _send_single_request_to_downloader(
        self, request: Request
    ) -> typing.Optional[CLEANUP_WITH_RESPONSE]:
        return await self.downloader.handle_request(request=request)

    async def _send_all_requests_to_downloader(
        self,
    ) -> typing.List[CLEANUP_WITH_RESPONSE]:
        request_tasks: typing.List[typing.Awaitable] = []
        for request in self.spider.requests:
            request_tasks.append(
                asyncio.create_task(
                    self._send_single_request_to_downloader(request=request)
                )
            )
        self.spider.requests.clear()
        coro = asyncio.gather(*request_tasks)  # type: ignore
        try:
            responses = await coro
        except BaseException as e:  # pragma: no cover
            coro.cancel()
            raise DownloadFailedException from e
        return [
            response
            for response in responses
            if response and not isinstance(response, BaseException)
        ]

    async def _handle_single_response(
        self, response_and_generator: CLEANUP_WITH_RESPONSE
    ) -> None:
        try:  # pragma: no cover
            from bs4 import BeautifulSoup
        except ImportError:  # pragma: no cover
            BeautifulSoup = None
        if not inspect.isasyncgenfunction(self.spider.parse):
            raise InvalidParseMethodException(
                "Spider's `parse` must be an asynchronous generator function"
            )
        clean_up_generator, response = response_and_generator
        soup = None
        if BeautifulSoup is not None:
            with suppress(httpx.ResponseNotRead):  # pragma: no cover
                soup = BeautifulSoup(response.text, "html.parser")

        response.soup = soup  # type: ignore[attr-defined]
        gen = self.spider.parse(response=response)
        async for yielded_value in gen:
            if isinstance(yielded_value, Request):
                self.spider.requests.append(yielded_value)
            elif isinstance(yielded_value, Item):
                self.spider.items.append(yielded_value)  # pragma: no cover
            elif yielded_value is None:  # pragma: no cover
                ...  # pragma: no cover
            else:
                raise InvalidYieldValueException(
                    "Invalid type yielded, expected `Request` or `Item` got `%s`"
                    % yielded_value.__class__.__name__
                )

    async def _handle_responses(
        self, responses: typing.List[CLEANUP_WITH_RESPONSE]
    ) -> None:
        tasks = [
            asyncio.create_task(self._handle_single_response(response))
            for response in responses
        ]
        coro = asyncio.gather(*tasks)
        try:
            await coro
        except BaseException as e:  # pragma: no cover
            coro.cancel()
            raise ParseFailedException from e

    async def _run_once(self) -> None:
        log.debug("Running engine once")
        responses = await self._send_all_requests_to_downloader()
        try:
            log.debug("Handling the responses")
            await self._handle_responses(responses=responses)
            if self.items_manager:
                log.debug("Processing the items")
                await self.items_manager.process_items(self.spider.items)
            log.debug("Clear spider items after processing")
            self.spider.items.clear()
        finally:
            for gen, response in responses:
                log.debug("Cleaning up the responses")
                await clean_up_response(gen)

    async def _tear_down(self) -> None:
        log.debug("Tear down was called")
        if self.items_manager:
            log.info(f"Closing the opened loaders: {self.items_manager.loaders=}")
            await self.items_manager.tear_down_loaders()

    async def run(self) -> None:
        try:
            while self.spider.requests:
                await self._run_once()
                await asyncio.sleep(self.loop_delay)
        except Exception as e:  # pragma: no cover
            log.error("Exception %s was raised" % e.__class__.__name__)
        finally:
            log.info("Calling tear down on engine")
            await self._tear_down()
