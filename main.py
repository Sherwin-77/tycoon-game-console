from __future__ import annotations
from typing import List
from enum import Enum

import asyncio
from os import name, system
import datetime
import time


# Utility to create function run every x second without blocking main program
async def create_schedule(func ,interval: int = 5, *args, **kwargs):
    while True:
        await asyncio.gather(
            asyncio.sleep(interval),
            func(*args, **kwargs)
        )


# Utility for clear console screen
def clear():
    # for windows
    if name == 'nt':
        _ = system('cls')
 
    # for mac and linux(here, os.name is 'posix')
    else:
        _ = system('clear')


class DisplayState:
    """
    Utility class for handling display state
    """
    def __init__(self, office: Office) -> None:
        self.__pending = False
        self.__result_input = None
        self._office = office

    async def get_input(self):
        """
        Utility to get input async. WIll return None if input already in progress
        """
        if not self.__pending:
            loop = asyncio.get_event_loop()
            self.__pending = True
            self.__result_input = await loop.run_in_executor(None, input, "Select Option -> ")

            try:
                self.__result_input = int(self.__result_input)
            except ValueError:
                self.flush()
                print("Invalid option")
            else:
                it = self.__result_input
                self.flush()
                return it
        else:
            return None
    
    def display(self):
        print(self._office.display)
        if self.__pending:
            print("Select Option -> ", end='', flush=True)

    # Utility to clear input. Normally should done automatically 
    def flush(self):
        self.__pending = None
        self.__result_input = None

    # Accessor in case result fails to get
    @property
    def result_input(self):
        return self.__result_input


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
        self.__last_claim = time.time()

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
        cur = time.time()
        self.update_effects()
        self.update_income()
        self.__budgets += round(self._income * (cur - self.__last_claim))
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
        self.collect()
        f = '\n'.join([f"{x.name} - LVL {x.level}" for x in self.__facilities])
        b = '\n'.join([str(x) for x in self.buffs])
        return (  
            f"{self.name} - {self._address}\n"
            f"Current Income: {self.income} / HyperSecond\n"
            f"Current Budgets: {self.__budgets}\n"
            f"=== FACILITIES ===\n"
            f"{f}\n"
            f"=== ACTIVE BUFFS ===\n"
            f"{b}\n"
        )


start_time = datetime.datetime.now()
async def timer_task(state: DisplayState):
    clear()
    print(str((datetime.datetime.now() - start_time)).split('.')[0])
    state.display()

async def main(name, address):
    office = Office(name, address)
    state = DisplayState(office)
    asyncio.create_task(create_schedule(timer_task, 15, state))  # Automatic refresh every 15 seconds
    while True:
        clear()
        state.display()
        opt = await state.get_input()
        if opt is None:
            continue
        if opt == 0:
            break


if __name__ == "__main__":
    # Kode utama disini
    name = input("Choose your office name: ")
    address = input("Choose your office address: ")
    asyncio.run(main(name, address))
