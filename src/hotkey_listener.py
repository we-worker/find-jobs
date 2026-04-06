from __future__ import annotations

from collections.abc import Callable

import keyboard


class HotkeyListener:
    def __init__(self, hotkey: str, callback: Callable[[], bool]) -> None:
        self.hotkey = hotkey
        self.callback = callback
        self._registered = False
        self._handler = None

    def start(self) -> None:
        if self._registered:
            return
        self._handler = keyboard.add_hotkey(self.hotkey, self.callback, suppress=False)
        self._registered = True

    def stop(self) -> None:
        if not self._registered:
            return
        if self._handler is not None:
            keyboard.remove_hotkey(self._handler)
            self._handler = None
        self._registered = False
