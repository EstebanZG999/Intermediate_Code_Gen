from dataclasses import dataclass, field
from typing import Dict, Optional

@dataclass
class Slot:
    name: str
    region: str        # "param" | "local" | "this" | "temp"
    offset: int        # relativo a fp

@dataclass
class ActivationRecord:
    func_name: str
    slots: Dict[str, Slot] = field(default_factory=dict)
    locals_size: int = 0     # #palabras reservadas hacia negativos
    params_size: int = 0     # #palabras de parámetros (hacia positivos)
    has_this: bool = False

    def add_param(self, name: str, size: int = 1):
        # convención: params en offsets positivos (fp+2 = primer param)
        off = self.params_size + 2  # +2 para [ret_addr][old_fp]
        self.slots[name] = Slot(name, "param", off)
        self.params_size += size

    def add_this(self):
        # convención: this en fp+1 (después de old_fp)
        self.slots["this"] = Slot("this", "this", 1)
        self.has_this = True

    def add_local(self, name: str, size: int = 1):
        # convención: locales hacia negativos: fp-1, fp-2, ...
        self.locals_size += size
        off = -self.locals_size
        self.slots[name] = Slot(name, "local", off)

    def addr_of(self, name: str) -> Optional[Slot]:
        return self.slots.get(name)

    @property
    def frame_size(self) -> int:
        """
        Tamaño 'lógico' del frame:
          [ret_addr][old_fp] + (this?) + params_size + locals_size
        """
        return 2 + (1 if self.has_this else 0) + self.params_size + self.locals_size
