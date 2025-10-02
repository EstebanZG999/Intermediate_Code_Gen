from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
from .tac_ir import Temp

@dataclass
class TempAllocator:
    prefix: str = "t"
    _counter: int = 0
    _free_list: List[str] = field(default_factory=list)

    def new(self) -> Temp:
        if self._free_list:
            return Temp(self._free_list.pop())
        name = f"{self.prefix}{self._counter}"
        self._counter += 1
        return Temp(name)

    def free(self, temp: Temp) -> None:
        if temp.name not in self._free_list:
            self._free_list.append(temp.name)

    def reset(self) -> None:
        self._counter = 0
        self._free_list.clear()