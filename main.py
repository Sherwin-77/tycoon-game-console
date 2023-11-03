from __future__ import annotations
from typing import List
from enum import Enum

from os import name, system
import datetime


# Utility for clear console screen
def clear():
    # for windows
    if name == 'nt':
        _ = system('cls')
 
    # for mac and linux(here, os.name is 'posix')
    else:
        _ = system('clear')


class PositionType(Enum):
    CONSULTANT = 1
    MANAGER = 2
    LEADER = 3


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
        return f"{self.__class__.__qualname__}: {self._name}"


class Buff:
    """
    Abstract base class for any buff
    """
    
    def activate(self):
        raise NotImplementedError("Buff must be inherited")


    @property
    def name(self) -> str:
        return self.__class__.__name__

    def __str__(self) -> str:
        return self.name



class StaticBuff(Buff):
    """
    Represent buff that doesn't have duration (permanent)
    Usually stat up buff
    """
    def __init__(self, office: Office, amount: int, stack: int) -> None:
        super().__init__()
        if not all(isinstance(x, int) for x in [amount, stack]):
            raise TypeError("Amount and stack must be integer")
        if not isinstance(office, Office):
            raise TypeError("Office must be class of Office")
        self._amount = amount
        self._stack = stack
        self.__office = office

    @property
    def name(self) -> str:
        return "Stats Buff"

    # Default activate will goes increase the income directly
    def activate(self):
        self.__office.income = round(self.__office.income * (1+((self._amount * self._stack)/100)))

    def __str__(self) -> str:
        return f"{self.name} x{self._stack} (INCOME UP {self._amount}%)"


class Staff(Anything):
    """
    This will be base class representing of staff
    """
    def __init__(self, name: str, age: int, position: PositionType, skills: List[Buff]) -> None:
        super().__init__(name)

        if not isinstance(age, int):
            raise TypeError("Age must be integer")
        if not isinstance(position, PositionType):
            raise TypeError("Position must be instance of PositionType")
        if not isinstance(skills, list):
            raise TypeError("Skills must be list")
        for x in skills:
            if not isinstance(x, Buff):
                raise TypeError("Skills must be list of Buff")

        self._age = age
        self.__position = position
        self.__skills = skills
    
    @property
    def age(self) -> int:
        return self._age

    @property
    def position(self) -> PositionType:
        return self.__position

    @property
    def skills(self) -> List[Buff]:
        return self.__skills


class Facility(Anything):
    """
    `Facility` class for `Office`. Usually predefined
    """
    def __init__(self, name: str, cost_growth: int,  effects: List[Buff]) -> None:
        super().__init__(name)

        if not isinstance(cost_growth, int):
            raise TypeError("Cost growth must be int")

        if not isinstance(effects, list):
            raise TypeError("Effects must be list")
        for e in effects:
            if not isinstance(e, Buff):
                raise TypeError("List of effects must be Buff")

        self._level = 1
        self._cost_growth = cost_growth
        self.__effects = effects

    @property
    def effects(self) -> List[Buff]:
        return self.__effects.copy()
    
    @property
    def level(self) -> int:
        return self._level

    def upgrade(self) -> None:
        pass

class Office(Anything):
    """
    Main class for saving any state of game
    """
    def __init__(self, name: str, address: str) -> None:
        super().__init__(name)

        if not isinstance(address, str):
            raise TypeError("Address must be string")

        self._address = address

        self.__base_income = 10
        self._income = self.__base_income

        self.__budgets = 1000
        self.__facilities: List[Facility] = [
            Facility("PC", 100, [StaticBuff(self, 10, 1)])
        ]
        self.__effects: List[Buff] = []
        self.__buffs: List[Buff] = []
        self.__last_claim = datetime.datetime.now()

        self.update_effects()

    # Function to update effect from facilities. Usually done automatically
    def update_effects(self):
        self.__effects = []
        for x in self.__facilities:
            self.__effects.extend(x.effects)
    
    # Function to update income from facilities. Usually done automatically
    def update_income(self):
        self._income = self.__base_income
        for x in self.buffs:
            x.activate()

    def upgrade_facility(self, facility: Facility):
        pass

    # Collect based on time passed and incomes
    def collect(self):
        cur = datetime.datetime.now()
        self.update_effects()
        self.update_income()
        self.__budgets += round(self._income * (cur - self.__last_claim).total_seconds())
        self.__last_claim = cur

    @property
    def buffs(self) -> List[Buff]:
        self.update_effects()
        return self.__effects + self.__buffs

    @property
    def income(self):
        return self._income
    
    @income.setter
    def income(self, val: int):
        if not isinstance(val, int):
            raise TypeError("Income setter must be integer")
        self._income = val

    @property
    def display(self):
        """
        Get the display state from office. Automatically collect when accessed
        """
        self.collect()
        f = '\n'.join([f"{x.name} - LVL {x.level}" for x in self.__facilities])
        b = '\n'.join([str(x) for x in self.buffs])
        return (  
            f"{self.name} - {self._address}\n"
            f"Current Income: {self.income} / HyperSecond\n"
            f"Current Budgets: {self.__budgets}\n"
            f"Last collect: {self.__last_claim}\n"
            f"=== FACILITIES ===\n"
            f"{f}\n"
            f"=== ACTIVE BUFFS ===\n"
            f"{b}\n"
        )


start_time = datetime.datetime.now()
def main(name, address):
    office = Office(name, address)
    while True:
        clear()
        print(office.display)

        opt = input("Select option -> ")
        try:
            opt = int(opt)
        except ValueError:
            print("Invalid option")
        else:
            pass


if __name__ == "__main__":
    # Kode utama disini
    name = input("Choose your office name: ")
    address = input("Choose your office address: ")
    main(name, address)
