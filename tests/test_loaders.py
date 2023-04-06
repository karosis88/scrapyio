import tempfile
import warnings

import pytest
from pydantic import BaseModel

from scrapyio.item_loaders import BaseLoader
from scrapyio.item_loaders import CSVLoader
from scrapyio.item_loaders import JSONLoader
from scrapyio.item_loaders import LoaderState
from scrapyio.item_loaders import ProxyLoader
from scrapyio.items import Item


class FakeLoader:
    async def open(self):
        ...

    async def dump(self, item: object):
        ...

    async def close(self):
        ...


class TestItem(BaseModel):
    best_scraping_library: str


class EmptyLoader(BaseLoader):
    async def open(self) -> None:
        raise NotImplementedError

    async def dump(self, item: "Item") -> None:
        raise NotImplementedError

    async def close(self) -> None:
        raise NotImplementedError


@pytest.mark.anyio
async def test_proxy_loader_closing_not_opened():
    proxy_loader = ProxyLoader(loader=EmptyLoader())
    assert proxy_loader.state == LoaderState.CREATED

    with pytest.raises(
        RuntimeError,
        match=r"The loader cannot be closed because it has not yet been opened.",
    ):
        await proxy_loader.close()


@pytest.mark.anyio
async def test_proxy_loader_closing_already_closed():
    proxy_loader = ProxyLoader(loader=EmptyLoader())
    assert proxy_loader.state == LoaderState.CREATED
    proxy_loader.state = LoaderState.CLOSED

    with pytest.raises(
        RuntimeError,
        match=r"Loader cannot be closed because it is already closed.",
    ):
        await proxy_loader.close()


@pytest.mark.anyio
async def test_proxy_loader_dumping_created():
    proxy_loader = ProxyLoader(loader=EmptyLoader())
    assert proxy_loader.state == LoaderState.CREATED

    with pytest.raises(
        RuntimeError,
        match=r"The newly created loader cannot dump an object; it must be opened.",
    ):
        await proxy_loader.dump(object())


@pytest.mark.anyio
async def test_proxy_loader_dumping_closed():
    proxy_loader = ProxyLoader(loader=EmptyLoader())
    assert proxy_loader.state == LoaderState.CREATED
    proxy_loader.state = LoaderState.CLOSED

    with pytest.raises(
        RuntimeError,
        match="It is not possible to dump a pydantic "
        r"object after the loader has been closed.",
    ):
        await proxy_loader.dump(object())


@pytest.mark.anyio
async def test_proxy_loader_opening_already_opened():
    proxy_loader = ProxyLoader(loader=EmptyLoader())
    assert proxy_loader.state == LoaderState.CREATED
    proxy_loader.state = LoaderState.OPENED

    with pytest.raises(
        RuntimeError, match=r"Cannot open a loader that has already been opened."
    ):
        await proxy_loader.open()


@pytest.mark.anyio
async def test_proxy_loader_opening_with_dumping_state():
    proxy_loader = ProxyLoader(loader=EmptyLoader())
    assert proxy_loader.state == LoaderState.CREATED
    proxy_loader.state = LoaderState.DUMPING

    with pytest.raises(
        RuntimeError,
        match=r"Cannot open a loader that is already in the dumping state.",
    ):
        await proxy_loader.open()


@pytest.mark.anyio
async def test_proxy_loader_opening_closed():
    proxy_loader = ProxyLoader(loader=EmptyLoader())
    assert proxy_loader.state == LoaderState.CREATED
    proxy_loader.state = LoaderState.CLOSED

    with pytest.raises(
        RuntimeError,
        match=r"It is not possible to reopen a loader that has already been closed.",
    ):
        await proxy_loader.open()


@pytest.mark.anyio
async def test_json_loader_open():
    path = tempfile.mktemp()
    loader = JSONLoader(filename=path)
    try:
        await loader.open()
    finally:
        loader.file.close()
        with open(path, encoding="utf-8") as f:
            assert f.read() == "[\n"


@pytest.mark.anyio
async def test_json_loader_close():
    path = tempfile.mktemp()
    loader = JSONLoader(filename=path)
    try:
        loader.file = open(path, "w")
    finally:
        await loader.close()
        with open(path, encoding="utf-8") as f:
            assert f.read() == "\n]"


@pytest.mark.anyio
async def test_json_loader_dump_first_item():
    item = TestItem(best_scraping_library="scrapyio")
    path = tempfile.mktemp()
    loader = JSONLoader(filename=path)
    try:
        loader.file = open(path, "w")
        await loader.dump(item=item)
    finally:
        loader.file.close()
        with open(path, encoding="utf-8") as f:
            assert f.read() == '{"best_scraping_library": "scrapyio"}'


@pytest.mark.anyio
async def test_json_loader_dump_not_first_item():
    item = TestItem(best_scraping_library="scrapyio")
    path = tempfile.mktemp()
    loader = JSONLoader(filename=path)
    try:
        loader.file = open(path, "w")
        loader.first_item = False
        await loader.dump(item=item)
    finally:
        loader.file.close()
        with open(path, encoding="utf-8") as f:
            assert f.read() == ',\n{"best_scraping_library": "scrapyio"}'


@pytest.mark.anyio
async def test_csv_loader_open():
    path = tempfile.mktemp()
    loader = CSVLoader(filename=path)
    try:
        await loader.open()
    finally:
        loader.file.close()
        with open(path, encoding="utf-8") as f:
            assert f.read() == ""


@pytest.mark.anyio
async def test_csv_loader_close():
    path = tempfile.mktemp()
    loader = CSVLoader(filename=path)
    try:
        await loader.open()
    finally:
        await loader.close()
        with open(path, encoding="utf-8") as f:
            assert f.read() == ""


@pytest.mark.anyio
async def test_csv_loader_dump_first_item():
    item = TestItem(best_scraping_library="scrapyio")
    path = tempfile.mktemp()
    loader = CSVLoader(filename=path)
    try:
        loader.file = open(path, "w")
        await loader.dump(item=item)
    finally:
        loader.file.close()
        with open(path, encoding="utf-8") as f:
            assert f.read() == "best_scraping_library\nscrapyio\n"


@pytest.mark.anyio
async def test_csv_loader_dump_not_first_item():
    item = TestItem(best_scraping_library="scrapyio")
    path = tempfile.mktemp()
    loader = CSVLoader(filename=path)
    try:
        loader.file = open(path, "w")
        loader.first_item = False

        with pytest.raises(
            AssertionError, match=r"Trying to use csv.DictWriter which is None"
        ):
            await loader.dump(item=item)
    finally:
        loader.file.close()
        with open(path, encoding="utf-8") as f:
            assert f.read() == ""


@pytest.mark.anyio
async def test_proxy_loader_open():
    loader = FakeLoader()
    proxy_loader = ProxyLoader(loader=loader)

    await proxy_loader.open()
    assert proxy_loader.state == LoaderState.OPENED


@pytest.mark.anyio
async def test_proxy_loader_dumping():
    loader = FakeLoader()
    proxy_loader = ProxyLoader(loader=loader)

    proxy_loader.state = LoaderState.OPENED
    await proxy_loader.dump(object())
    assert proxy_loader.state == LoaderState.DUMPING

    proxy_loader.state = LoaderState.DUMPING
    await proxy_loader.dump(object())
    assert proxy_loader.state == LoaderState.DUMPING


@pytest.mark.filterwarnings("once::RuntimeWarning")
@pytest.mark.anyio
async def test_proxy_loader_closing_opened():
    loader = FakeLoader()
    proxy_loader = ProxyLoader(loader=loader)
    proxy_loader.state = LoaderState.OPENED

    with warnings.catch_warnings(record=True) as w:
        await proxy_loader.close()
        assert len(w) == 1
        assert w[0].category == RuntimeWarning