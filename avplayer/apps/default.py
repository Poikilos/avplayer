# -*- coding: utf-8 -*-

from argparse import Namespace
from asyncio import get_running_loop
from asyncio import run as asyncio_run
from asyncio import run_coroutine_threadsafe
from asyncio import sleep as asyncio_sleep
from datetime import datetime
from tkinter import NW, Canvas, Tk
from typing import Final, Optional

from numpy import full, ndarray, uint8
from overrides import overrides
from PIL.Image import fromarray
from PIL.ImageTk import PhotoImage

from avplayer.logging.logging import logger
from avplayer.media.media_callbacks import AsyncMediaCallbacksInterface
from avplayer.media.media_options import MediaOptions
from avplayer.media.media_player import MediaPlayer

DEFAULT_TITLE: Final[str] = "AVPlayer"


def make_bgr888(width: int, height: int, blue=0, green=0, red=0) -> ndarray:
    return full(
        shape=(height, width, 3),
        fill_value=(blue, green, red),
        dtype=uint8,
    )


class DefaultApp(Tk, AsyncMediaCallbacksInterface):
    def __init__(
        self,
        source: str,
        output: Optional[str] = None,
        options: Optional[MediaOptions] = None,
        width=800,
        height=600,
        x=0,
        y=0,
        title=DEFAULT_TITLE,
        fps=60,
    ):
        super().__init__()

        self.title(title)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.resizable(False, False)

        self._player = MediaPlayer(
            source,
            destination=output,
            callbacks=self,
            options=options,
        )

        self._sleep = 1.0 / fps
        self._exit = False

        self._canvas = Canvas(self, width=width, height=height, bg="white")
        self._canvas.pack()

        self._array = make_bgr888(width, height)[:, :, ::-1]
        self._image = fromarray(self._array, mode="RGB")
        self._photo = PhotoImage(image=self._image)
        self._canvas.create_image(0, 0, image=self._photo, anchor=NW)

        self.protocol("WM_DELETE_WINDOW", self.on_destroy)

    def on_destroy(self) -> None:
        logger.warning("Exit signal detected")
        run_coroutine_threadsafe(self.close(), get_running_loop())

    def is_exit(self) -> bool:
        return self._exit and not self._player.is_open()

    @overrides
    async def on_container_begin(self) -> None:
        pass

    @overrides
    async def on_container_end(self) -> None:
        pass

    @overrides
    async def on_video_frame(
        self, frame: ndarray, start: datetime, last: datetime
    ) -> None:
        if self.is_exit():
            return
        size = self.winfo_width(), self.winfo_height()
        self._array = frame[:, :, ::-1]
        self._image = fromarray(self._array, mode="RGB").resize(size)
        self._photo = PhotoImage(image=self._image)
        self._canvas.create_image(0, 0, image=self._photo, anchor=NW)
        self.update()

    @overrides
    async def on_audio_frame(
        self, frame: ndarray, start: datetime, last: datetime
    ) -> None:
        if self.is_exit():
            return
        pass

    @overrides
    async def on_segment(
        self, directory: str, filename: str, start: datetime, last: datetime
    ) -> None:
        if self.is_exit():
            return
        pass

    async def run(self) -> None:
        self._player.open(get_running_loop())
        try:
            while not self.is_exit():
                await asyncio_sleep(self._sleep)
        finally:
            await self.close()

    async def close(self) -> None:
        self._exit = True
        if self._player.is_open():
            self._player.close()


def default_main(args: Namespace) -> None:
    assert args is not None

    debug = args.debug
    verbose = args.verbose
    output = args.output
    source = args.source

    assert isinstance(debug, bool)
    assert isinstance(verbose, int)
    assert isinstance(output, (type(None), str))
    assert isinstance(source, str)

    app = DefaultApp(source, output)
    asyncio_run(app.run())
