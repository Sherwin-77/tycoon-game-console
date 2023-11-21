from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Generator, List, Optional
from enum import Enum

import asyncio
from collections import defaultdict, deque
import datetime
from functools import lru_cache
from os import name, system
import random
import time


START_TIME = datetime.datetime.now()
MENU = """=== MENU ===
1. Upgrade Furniture
2. Hire Staff
0. Exit
"""

class NotEnoughBudget(Exception):
    pass


# Utility to create function run every x second without blocking main program
async def create_schedule(func, interval: int = 5, *args, **kwargs):
    while True:
        await asyncio.gather(
            asyncio.sleep(interval),
            func(*args, **kwargs)
        )


# Utility to do exponentiation with integer only
@lru_cache()
def exponentiation(base: int, exp: int) -> int:
    if (exp == 0):
        return 1
    if (exp == 1):
        return base
     
    t = exponentiation(base, exp // 2);
    t *= t
     
    if (exp % 2 == 0):
        return t
    else:
        return base * t 


# Utility to create incremental name with generator
def name_generator():
    cur_staff_id = 1
    while True:
        yield f"Staff-{cur_staff_id}"
        cur_staff_id += 1


class PositionType(Enum):
    CONSULTANT = 1
    MANAGER = 2
    LEADER = 3


class DisplayState:
    """
    Utility class for handling display state
    """
    def __init__(self, office: Office) -> None:
        self.__pending = False
        self.__result_input = None
        self._office = office
        self._input_menu = MENU
        self._errors = None
        self._pending_clear = False
        self.__lock = asyncio.Lock()

    # Accessor in case result fails to get
    @property
    def result_input(self):
        return self.__result_input        

    async def get_input(self, input_msg: Optional[str] = None):
        """
        Utility to get input async. Will ignore if input already in progress

        `input_msg` will be ignored if string not supplied
        """
        if not self.__pending:
            loop = asyncio.get_event_loop()
            self.__pending = True
            if input_msg is not None and isinstance(input_msg, str):
                self._input_menu = input_msg
            print(self._input_menu)
            self.__result_input = await loop.run_in_executor(None, input, "Select Option -> ")

            try:
                self.__result_input = int(self.__result_input)
            except ValueError:
                self.flush()
                self.set_error("Invalid option")
            else:
                it = self.__result_input
                self.flush()
                return it
        else:
            return None
    
    def set_error(self, error):
        self._errors = error

    # Utility for clear console screen. Usually called automatically
    def clear(self):
        # for windows
        if name == 'nt':
            _ = system('cls')
    
        # for mac and linux(here, os.name is 'posix')
        else:
            _ = system('clear')
        
    async def display(self):
        """
        Display the game info. Will automatically call `DisplayState.clear()`
        """
        async with self.__lock:
            if self._pending_clear:
                return
            self._pending_clear = True
        await asyncio.sleep(0.5)
        self.clear()
        print(self._office.display)
        if self._errors is not None:
            print("ERROR:", self._errors)
        if self.__pending:
            print(self._input_menu)
            print("Select Option -> ", end='', flush=True)
        self._pending_clear = False

    # Utility to clear input. Normally should done automatically 
    def flush(self):
        self.__pending = None
        self.__result_input = None
        self._errors = None


class Buff(ABC):
    """
    Abstract base class for any buff
    """
    
    @abstractmethod
    def activate(self):
        pass

    @property
    def name(self) -> str:
        return self.__class__.__name__

    def __str__(self) -> str:
        return self.name


class StaticBuff(Buff):
    """
    Represent buff that doesn't have duration (permanent).
    Usually stat up buff

    If inherited for different stat buff, `activate` and `__str__` method must be overridden
    """
    def __init__(self, office: Office, amount: int, stack: int) -> None:
        super().__init__()
        if not all(isinstance(x, int) for x in [amount, stack]):
            raise TypeError("Amount and stack must be integer")
        if not isinstance(office, Office):
            raise TypeError("Office must be class of Office")
        self._amount = amount
        self._stack = stack
        self._office = office

    @property
    def name(self) -> str:
        return "Stats Buff"

    @property
    def amount(self) -> int:
        return self._amount
    
    @amount.setter
    def amount(self, val: int):
        if not isinstance(val, int):
            raise TypeError("Value of amount must be integer")
        self._amount = val

    @property
    def stack(self) -> int:
        return self._stack
    
    @stack.setter
    def stack(self, val: int):
        if not isinstance(val, int):
            raise TypeError("Value of stack must be integer")
        self._stack = val

    # Default activate will goes increase the income directly
    def activate(self):
        self._office.income += self._office.income * (self._amount * self._stack)//500

    def __str__(self) -> str:
        return f"{self.name} x{self._stack} (INCOME UP {self._amount//5}%)"


class TimedBuff(StaticBuff):
    """
    Represent buff that has duration. Inherits attribute from `StaticBuff`

    If inherited for different stat buff, `activate` and `__str__` method must be overridden
    """
    def __init__(self, office: Office, amount: int, stack: int, duration: int, state: DisplayState) -> None:
        super().__init__(office, amount, stack)
        if not isinstance(duration, int):
            raise TypeError("Duration must be int")
        if not isinstance(state, DisplayState):
            raise TypeError("State must be class of DisplayState")
        self._start = time.time()
        self._duration = duration
        self._state = state
        self._running = False

    @property
    def name(self) -> str:
        return "Limited Buff"

    async def _do_timeout(self):
        await asyncio.sleep(self._duration)
        await self._office.collect()
        self._office.remove_buff(self)
        self._office.update_income()
        await self._state.display()

    def activate(self):
        if not self._running:
            asyncio.create_task(self._do_timeout())
            self._running = True
        super().activate()

    def __str__(self) -> str:
        diff = time.time() - self._start
        return f"{self.name} x{self._stack} (INCOME UP {self._amount//5}%) - {round(self._duration - diff)} seconds left"


# Below is specific skill for staff
class DoubleIncome(TimedBuff):
    """
    Buff that doubles the current income. When stacked, will be multiplied by stacks+1 instead
    """
    @property
    def name(self) -> str:
        return "Rewind Time"
    def activate(self):
        if not self._running:
            asyncio.create_task(self._do_timeout())
            self._running = True

        self._office.income += (self._office.income * (1 + self.stack))


class RewindTime(TimedBuff):
    """
    Buff that freezes and rewind the current time and revert when time out
    """
    @property
    def name(self):
        return "Rewind Time"

    async def _do_timeout(self, original_time: float):
        await asyncio.sleep(self._duration * self._stack)
        # Before collecting, we make sure to set the froze claim time then revert it
        self._office.last_claim = original_time - ((self._duration + self.amount) * self._stack)
        await self._office.collect()
        self._office.remove_buff(self)
        self._office.update_income()
        await self._state.display()
        # Back to original time of last claim
        self._office.last_claim = original_time

    def activate(self):
        if not self._running:
            # Rewind time of last claim
            self._office.last_claim = self._office.last_claim - ((self._duration + self.amount) * self._stack)
            asyncio.create_task(self._do_timeout(self._office.last_claim))
            self._running = True

    def __str__(self) -> str:
        diff = time.time() - self._start
        return f"{self.name} x{self._stack} - {round(((self._duration + self.amount) * self._stack) - diff)} seconds until back to present time"


class ExtraBudget(TimedBuff):
    """
    Increase income and delayed increase budget
    """
    @property
    def name(self):
        return "Extra Budget"

    async def _do_timeout(self):
        await super()._do_timeout()
        self._office.budgets += self._office.budgets * (self._amount * self._stack)//500


class Staff:
    """
    This will be class representing of staff

    When initialized, this will registered as office staff. Thus increasing the office staff income
    """
    def __init__(self, name: str, age: int, office: Office, position: PositionType) -> None:
        if not isinstance(name, str):
            raise TypeError("Name must be string")
        if not isinstance(age, int):
            raise TypeError("Age must be integer")
        if not isinstance(position, PositionType):
            raise TypeError("Position must be instance of PositionType")
        if not isinstance(office, Office):
            raise TypeError("Office must be class Office")

        self.name = name
        self._age = age
        self.__office = office
        self.__position = position
        office.staff_income += max(55-age, 10)
    
    @property
    def age(self) -> int:
        return self._age

    @property
    def position(self) -> PositionType:
        return self.__position

    def use_skill(self, state: DisplayState):
        if not isinstance(state, DisplayState):
            raise TypeError("State must be from class DisplayState")
        # Position 2 staff have TimedBuff increase
        if self.position.value >= 2:
            self.__office.add_buff(TimedBuff(self.__office, random.randint(5, 20), random.choices([3, 2, 1], weights=[0.5, 4.5, 95])[0], 10, state))
        # Position 3 staff have 10% chance to trigger unique skill
        if self.position.value >= 3 and random.random() < 0.10:
            # Since all the unique skill inherit TimedBuff, we can 'hack' using duck typing
            tb = random.choice([DoubleIncome, RewindTime, ExtraBudget])
            buff = tb(self.__office, random.randint(15, 30), random.choices([3, 2, 1], weights=[0.1, 3, 96.9])[0], 20, state)
            self.__office.add_buff(buff)
            self.__office.add_log(f"{self.name} Successfully trigger skill, created {buff.name} Buff")


class Facility:
    """
    `Facility` class for `Office`. Usually predefined
    """
    def __init__(self, name: str, base_cost: int,  effects: List[StaticBuff], r_percent: int) -> None:
        if not isinstance(name, str):
            raise TypeError("Name must be string")
        if not isinstance(base_cost, int):
            raise TypeError("Base cost must be int")
        if not isinstance(r_percent, int):
            raise TypeError("R Factors must be float")
        if not isinstance(effects, list):
            raise TypeError("Effects must be list")
        if r_percent < 1:
            raise ValueError("R Percents must be greater than 1")
        for e in effects:
            if not isinstance(e, StaticBuff):
                raise TypeError("List of effects must be StaticBuff")
            if isinstance(e, TimedBuff):
                raise NotImplementedError("Timed buff as effects is not supported yet")

        self.name = name
        self._level = 1
        self._cached_cost = (1, base_cost)
        self._base_cost = base_cost
        self.__effects = effects
        self.R = r_percent
    
    @property
    def cost(self) -> int:
        if self._level == self._cached_cost[0]:
            return self._cached_cost[1]
        c = (self._base_cost * (exponentiation(self.R, self.level) - exponentiation(100, self.level))) // ((self.R * exponentiation(100, self.level-1)) - exponentiation(100, self.level))
        self._cached_cost = (self._level, c)
        return c

    @property
    def effects(self) -> List[StaticBuff]:
        return self.__effects.copy()
    
    @property
    def level(self) -> int:
        return self._level

    def upgrade(self) -> None:
        self._level += 1
        for x in self.__effects:
            x.amount += 4
            if self._level % 10 == 0:
                x.stack += 1


class Office:
    """
    Main class for saving any state of game
    """
    def __init__(self, name: str, address: str) -> None:
        if not isinstance(name, str):
            raise TypeError("Name must be string")
        if not isinstance(address, str):
            raise TypeError("Address must be string")
        self.name = name
        self._address = address

        self.__base_income = 10
        self._income = self.__base_income

        self.__budgets = 1600
        self.__facilities: List[Facility] = [
            Facility("Chair", 50, [StaticBuff(self, 5, 1)], 150),
            Facility("Table", 100, [StaticBuff(self, 10, 1)], 175),
            Facility("PC", 200, [StaticBuff(self, 10, 1), StaticBuff(self, 5, 2)], 200),
            Facility("Toilet", 350, [StaticBuff(self, 10, 1), StaticBuff(self, 10, 2), StaticBuff(self, 5, 3)], 300)
        ]
        self.__logs: deque[str] = deque()
        self.__effects: List[Buff] = []
        self.__buffs: List[Buff] = []
        self.__staffs: List[Staff] = []
        self.__last_claim = time.time()
        self.__lock = asyncio.Lock()
        self.__name_gen = name_generator()
        self._staff_cost = 160
        self._staff_income = 0
        self._staff_counts = 0
        self.__staff_info = {
            "consultant": 0,
            "manager": 0,
            "leader": 0
        }

        self.update_effects()

    # Property of buffs using generator to 'save' memory
    @property
    def buffs(self) -> Generator[Buff, None, None]:
        self.update_effects()
        for x in self.__effects:
            yield x
        for x in self.__buffs:
            yield x

    @property
    def facilities(self) -> List[Facility]:
        return self.__facilities.copy()
    
    @property
    def budgets(self) -> int:
        return self.__budgets

    @budgets.setter
    def budgets(self, val: int):
        if not isinstance(val, int):
            raise TypeError("Budgets setter must be integer")
        self.__budgets = val
        
    @property
    def income(self):
        return self._income
    
    @income.setter
    def income(self, val: int):
        if not isinstance(val, int):
            raise TypeError("Income setter must be integer")
        self._income = val

    @property
    def staff_income(self) -> int:
        return self._staff_income
    
    @staff_income.setter
    def staff_income(self, val):
        if not isinstance(val, int):
            raise TypeError("Staff income setter must be integer")
        self._staff_income = val

    @property
    def last_claim(self) -> float:
        return self.__last_claim

    @last_claim.setter
    def last_claim(self, val: float):
        if not isinstance(val, float):
            raise TypeError("Last claim time setter must be float")
        self.__last_claim = val

    def get_buff_size(self) -> int:
        return len(self.__buffs) + len(self.__effects)
    
    def get_staff_cost(self, bulk_10: bool = False) -> int:
        if not isinstance(bulk_10, bool):
            raise TypeError("Bulk 10 option must be boolean")
        if bulk_10:
            a = 10 - (self._staff_counts % 10) 
            return (self._staff_cost * a) + (self._staff_cost * 3 * (10-a))
        else:
            return self._staff_cost

    def add_log(self, val: str):
        tm = str((datetime.datetime.now() - START_TIME)).split('.')[0]
        if not isinstance(val, str):
            raise TypeError("Log must be string")
        if len(self.__logs) >= 5:
            self.__logs.popleft()
        self.__logs.append(val + f" - At {tm}")
    
    def clear_log(self):
        self.__logs.clear()

    @property
    def display(self):
        f = ''.join([f"{i}) {x.name} - LVL {x.level} [{x.cost} for next upgrade]" + ('\n' if (i+1)%2 else '\t') for i, x in enumerate(self.__facilities, start=1)])
        b = ''
        sz = self.get_buff_size()
        # Truncate the output when buff amount more than 10
        if sz > 10:
            hashmap = defaultdict(int)
            for x in self.buffs:
                if type(x) == StaticBuff:
                    hashmap["Stats Buff"] += 1
                elif type(x) == TimedBuff:
                    hashmap["Timed Buff"] += 1
                else:
                    hashmap[x.name] += 1
            for k, v in hashmap.items():
                b += f"{k} - {v} Total\n"
        else:
            b = '\n'.join([str(x) for x in self.buffs])
        l = '\n'.join(self.__logs)
        tm = str((datetime.datetime.now() - START_TIME)).split('.')[0]
        return (  
            f"Elapsed Time: {tm}\n"
            f"{self.name} - {self._address}\n"
            f"Current Income: {self.income} / HyperSecond\n"
            f"Current Budgets: {self.__budgets}\n"
            f"=== FACILITIES ===\n"
            f"{f.strip()}\n"
            f"=== STAFFS ===\n"
            f"Leader\t\t: {self.__staff_info['leader']}\n"
            f"Manager\t\t: {self.__staff_info['manager']}\n"
            f"Consultant\t: {self.__staff_info['consultant']}\n"
            f"=== ACTIVE BUFFS & EFFECTS ===\n"
            f"{b.strip()}\n"
            f"=== LOGS ===\n"
            f"{l.strip()}"
        )
    
    def add_buff(self, buff: Buff):
        """
        Add buff to list buffs
        """
        if not isinstance(buff, Buff):
            raise TypeError("buff must be from class Buff")
        self.__buffs.append(buff)


    def remove_buff(self, buff: Buff):
        """
        Remove buff from list buffs. Taking memory reference as comparison

        Parameters
        ----------
        buff : `Buff`
            Buff to be deleted. This must be the same object when added to buff

        Raises
        ------
        TypeError
            Buff not class Buff
        ValueError
            Buff not exist in list of buffs
        """
        if not isinstance(buff, Buff):
            raise TypeError("buff must be from class Buff")
        found = None
        for i in range(len(self.__buffs)):
            if self.__buffs[i] is buff:
                found = i
                break
        if found is not None:
            self.__buffs.pop(found)
        else:
            raise ValueError("Value not found")
    
    # Method to trigger all skill from staff
    def use_staff_skill(self, state: DisplayState):
        if not isinstance(state, DisplayState):
            raise TypeError("State must be class of DisplayState")
        for s in self.__staffs:
            s.use_skill(state)

    # Method to update effect from facilities. Usually done automatically
    def update_effects(self):
        self.__effects.clear()
        for x in self.__facilities:
            self.__effects.extend(x.effects)
    
    # Method to update income from facilities. Usually done automatically
    def update_income(self):
        self._income = self.__base_income
        for x in self.buffs:
            x.activate()
        self._income += self._staff_income

    def upgrade_facility(self):
        """
        Create coroutine generator of upgrade facility. to upgrade, use .send(index_of_facility).
        Call `next(generator)` before start using this

        Raises
        ------
        TypeError
            Raises when index is not integer
        IndexError
            Raises when index out of range
        NotEnoughBudget
            Raises when budget not enough to upgrade
        """
        while True:
            # facility_index is 0 based
            facility_index = yield
            if not isinstance(facility_index, int):
                raise TypeError("Index facility must be integer")
            if facility_index < 0 or facility_index >= len(self.__facilities):
                raise IndexError(f"Index facility must be ranged from 1 to {len(self.__facilities)}")
            if self.__facilities[facility_index].cost > self.__budgets:
                raise NotEnoughBudget(f"Missing {self.__facilities[facility_index].cost - self.__budgets} budgets")
            self.__budgets -= self.__facilities[facility_index].cost
            self.__facilities[facility_index].upgrade()
            self.update_effects()

    def hire_staff(self, bulk_10: bool = False):
        """
        Method to add more staff
        """
        # Since get_staff_cost also do type checking, we don't need to check here anymore
        cost = self.get_staff_cost(bulk_10)
        if cost > self.budgets:
            raise NotEnoughBudget(f"Missing {cost-self.budgets} budgets to add staff")
        st = [
            Staff(next(self.__name_gen), random.randint(18, 55), self, x) 
            for x in random.choices([PositionType.LEADER, PositionType.MANAGER, PositionType.CONSULTANT], weights=[0.5, 3, 96.5], k=(10 if bulk_10 else 1))
        ]
        arr = []
        s2 = 0
        for x in st:
            if x.position == PositionType.LEADER:
                self.add_log("You successfully hired rank 3 Leader staff!")
                self.__staff_info["leader"] += 1
                arr.append(x)
            elif x.position == PositionType.MANAGER:
                self.__staff_info["manager"] += 1
                s2 += 1
                arr.append(x)
            else:
                # Here we drop level 1 staff to save memory & looping time since their role is just adding into staff_income
                self.__staff_info["consultant"] += 1
            self._staff_counts += 1
        if s2 > 0:
            self.add_log(f"hired {s2} rank 2 Manager staff")
        self.__budgets -= cost
        self._staff_cost = 180 * (3 ** (self._staff_counts//10))
        self.__staffs.extend(arr)

    async def collect(self):
        """
        Collect from income. To handle race condition, this method use underlying `asyncio.Lock`
        """
        async with self.__lock:
            cur = time.time()
            self.update_effects()
            self.update_income()
            cl = self._income * round(cur - self.__last_claim)
            if cl == 0:
                return
            self.add_log(f"Collect {cl}")
            self.__budgets += self._income * round(cur -self.__last_claim)
            self.__last_claim = cur


async def timer_task(state: DisplayState, office: Office):
    office.use_staff_skill(state)
    await office.collect()
    await state.display()


async def main(name, address):
    office = Office(name, address)
    state = DisplayState(office)
    asyncio.create_task(create_schedule(timer_task, 30, state, office))  # Automatic refresh every 30 seconds
    office.add_buff(TimedBuff(office, 70, 1, 30, state))
    upgrader = office.upgrade_facility()  # Set coroutine upgrade facility
    next(upgrader)
    while True:
        office.update_income()
        await state.display()
        opt = await state.get_input(MENU)
        if opt is None:
            continue
        if opt == 0:
            break
        elif opt == 1:
            fi = await state.get_input("Select facility number to upgrade")
            try:
                if fi is None:
                    continue
                upgrader.send(fi-1)
            except Exception as e:
                state.set_error(e)
                upgrader = office.upgrade_facility()  # Set new coroutine when error
                next(upgrader)
        elif opt == 2:
            opt = await state.get_input(f"1. 1x hire [{office.get_staff_cost()}]\n2. 10x hire [{office.get_staff_cost(True)}]")
            try:
                if opt is None:
                    continue
                if opt == 1:
                    office.hire_staff()
                elif opt == 2:
                    office.hire_staff(True)
                else:
                    state.set_error("Invalid hire option")
            except Exception as e:
                state.set_error(e)
        else:
            state.set_error("Invalid option")

if __name__ == "__main__":
    # Kode utama disini
    name = input("Choose your office name: ")
    address = input("Choose your office address: ")
    asyncio.run(main(name, address))
