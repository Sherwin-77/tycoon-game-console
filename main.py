from __future__ import annotations
from typing import List


class Anything:
    """
    Base class for anything with name property
    """
    def __init__(self, name: str) -> None:
        if not isinstance(name, str):
            raise TypeError("Name must be string")

        self._name = name

    @property
    def name(self) -> str:
        return self._name
    
    def __str__(self) -> str:
        return f"{self.__class__}: {self._name}"


class Buff:
    def __init__(self, amount: int, duration: int, stack: int = 1) -> None:
        self.amount = amount
        self.duration = duration
        self.stack = stack


class Staff(Anything):
    def __init__(self, name: str, age: int, position: str) -> None:
        super().__init__(name)

        if not isinstance(age, int):
            raise TypeError("Age must be integer")
        if not isinstance(position, str):
            raise TypeError("Position must be string")

        self._age = age
        self.__position = position
    
    @property
    def age(self) -> int:
        return self._age

    @property
    def position(self) -> str:
        return self.__position


class Office(Anything):
    def __init__(self, name: str, address: str) -> None:
        super().__init__(name)

        if not isinstance(address, str):
            raise TypeError("Address must be string")

        self._address = address


class Facility(Anything):
    def __init__(self, name: str, effects: List[Buff]) -> None:
        super().__init__(name)

        if not isinstance(effects, list):
            raise TypeError("Effects must be list")
        for e in effects:
            if not isinstance(e, Buff):
                raise TypeError("List of effects must be Buff")

        self.__effects = effects

    @property
    def effects(self) -> List[Buff]:
        return self.__effects.copy()


if __name__ == "__main__":
    # Kode utama disini
    pass
