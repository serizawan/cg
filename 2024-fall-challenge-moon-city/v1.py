# Welcome to my Selenia Optimization Tool. Let's build an eco-friendly city!
# v1 script builds a tube route loop and two pods that navigate clockwise and counter-clockwise.
# This naïve solution only works for sample 1 and 2.
# Score ~ N/A
# Example 1 ~ 50k
# Example 2 ~ 77k
# Balancing ~ N/A
# Crater Exploration ~ 121k
# Pair ~ 2k
# Villages ~ N/A
# Spiral ~ N/A
# Grid ~ N/A
# Expansion ~ N/A
# Groups ~ N/A
# Concentric Layers ~ N/A
# Distribution Network ~ N/A

from enum import Enum
import math
import sys

N_MONTHS = 20
N_DAYS_PER_MONTH = 20
REMAINING_RESOURCES_INTEREST_RATE = 0.1
MAX_MONTHLY_LANDINGS = 1_000


class Action(Enum):
    TUBE = "TUBE"
    UPGRADE = "UPGRADE"
    TELEPORT = "TELEPORT"
    POD = "POD"
    DESTROY = "DESTROY"
    WAIT = "WAIT"


class Ground:
    MAX_X = 160  # km
    MAX_Y = 90  # km


class Route:
    def __init__(self, b1, b2, capacity):
        self.b1 = b1
        self.b2 = b2
        self.capacity = capacity


class Tube(Route):
    COST_PER_100M = 1

    # A tube is bi-directional, b1 and b2 can be switched independently
    def __init__(self, b1, b2, capacity=1):
        super().__init__(b1, b2, capacity)
        self.max_n_pods = 1

    @property
    def length(self):
        return math.sqrt((self.b1.x - self.b2.x) ** 2 + (self.b1.y - self.b2.y) ** 2)

    @property
    def cost(self):
        return math.floor(self.length * 10) * self.COST_PER_100M  # Factor 10 to get the length in 100m units

    def build(self, n_resources, actions, tubes):
        n_resources -= self.cost
        actions.append(f"{Action.TUBE.value} {self.b1.id} {self.b2.id}")
        Logger.log(f"[{Action.TUBE.value}] Plan a tube build, {self.cost=}, {n_resources=}")
        tubes.append(self)
        return n_resources

    def upgrade(self, n_resources, actions):
        self.max_n_pods += 1
        n_resources -= self.cost * self.max_n_pods
        actions.append(f"{Action.UPGRADE.value} {self.b1} {self.b2}")
        return n_resources

    def __str__(self):
        return f"({self.b1=}, {self.b2=}, {self.capacity=})"

    def __repr__(self):
        return self.__str__()


class Teleporter(Route):
    T_PER_TELEPORT = 0
    COST = 5_000

    # Be careful here, a teleporter is NOT bi-directional, there is an entrance and an exit
    def __init__(self, entrance, exit):
        super().__init__(entrance, exit, math.inf)

    def build(self, n_resources, actions):
        n_resources -= Teleporter.COST
        actions.append(f"{Action.TELEPORT.value} {self.b1} {self.b2}")
        return n_resources


class Pod:
    MIN_POD_ID, MAX_POD_ID = 1, 500
    T_PER_TUBE = 1
    MAX_PASSENGERS = 10
    COST = 1_000
    RECYCLABLE_RESOURCES = 750

    def __init__(self, id, stops):
        self.id = id
        self.stops = stops

    @property
    def n_stops(self):
        return len(self.stops)

    def build(self, n_resources, actions, pods):
        n_resources -= Pod.COST
        actions.append(f"{Action.POD.value} {self.id} {' '.join(self.stops)}")
        Logger.log(f"[{Action.POD.value}] Plan a pod build (and schedule), {Pod.COST=}, {n_resources=}")
        pods.append(self)
        return n_resources

    def destroy(self, n_resources, actions):
        n_resources += Pod.RECYCLABLE_RESOURCES
        actions.append(f"{Action.DESTROY.value} {self.id}")
        return n_resources

    def __str__(self):
        return f"({self.id=}, {self.stops=})"

    def __repr__(self):
        return self.__str__()


class Building:
    MAX_TOTAL_BUILDINGS = 150
    MAX_TELEPORTERS = 1
    MAX_TUBES = 5

    def __init__(self, type, id, x, y):
        self.type = type
        self.id = id
        self.x = x
        self.y = y

    def __str__(self):
        return f"({self.type=}, {self.id=}, {self.x=}, {self.y=})"

    def __repr__(self):
        return self.__str__()


class MoonModule(Building):
    N_TYPES = 20


class LandingArea(Building):
    N_TYPE = 1
    TYPE_ID = 0
    MIN_LANDINGS, MAX_LANDINGS = 1, 100

    def __init__(self, id, x, y, astronauts):
        super().__init__(LandingArea.TYPE_ID, id, x, y)
        self.astronauts = astronauts

    @property
    def n_astronauts(self):
        return len(self.astronauts)

    def __str__(self):
        return f"({self.type}, {self.id=}, {self.x=}, {self.y=}, {self.n_astronauts=})"  # {self.astronauts=} can be appended to print astronauts


class Logger:
    IS_ENABLED = True

    @staticmethod
    def log(msg):
        if Logger.IS_ENABLED:
            print(msg, file=sys.stderr, flush=True)


class Astronaut:
    MAX_SPEED_POINTS = 50
    MAX_BALANCE_POINTS = 50
    MIN_BONUS_POINTS = 0

    def __init__(self, type, landing_area_id):
        self.type = type
        self.landing_area_id = landing_area_id

    def __str__(self):
        return f"({self.landing_area_id}, {self.type=})"

    def __repr__(self):
        return self.__str__()


class Parser:
    @staticmethod
    def parse(n_month):
        n_resources = int(input())
        n_routes = int(input())
        tubes, teleporters = [], []
        for i in range(n_routes):
            b1, b2, capacity = input().split()
            if capacity:
                tubes.append(Tube(b1, b2, int(capacity)))
            else:
                teleporters.append(Teleporter(b1, b2))

        n_pods = int(input())
        pods = []
        for i in range(n_pods):
            p_id, _, *stops = input().split()
            pods.append(Pod(p_id, stops))

        n_shipped_buildings = int(input())
        landing_areas = []
        moon_modules = []
        for i in range(n_shipped_buildings):
            b_type, b_id, b_x_str, b_y_str, *astronaut_types = input().split()
            if int(b_type):
                moon_modules.append(MoonModule(b_type, b_id, int(b_x_str), int(b_y_str)))
            else:
                astronauts = [Astronaut(a_type, b_id) for a_type in astronaut_types]
                landing_areas.append(LandingArea(b_id, int(b_x_str), int(b_y_str), astronauts))

        Logger.log(f"Month {n_month=} starts with: {n_resources=}, {tubes=}, {teleporters=}, {pods=}, {moon_modules=}, {landing_areas=}")
        return n_resources, tubes, teleporters, pods, landing_areas, moon_modules


class Game:
    @staticmethod
    def play():
        # First Month variable initiation
        n_month = 1
        n_resources, tubes, teleporters, pods, landing_areas, moon_modules = Parser.parse(n_month)
        buildings = landing_areas + moon_modules

        # Strategy: Build a route that loops through all buildings.
        end_of_tube_route_building = None
        next_tube_route_building_index = 0
        expected_end_of_tube_route_building = buildings[0]

        # One loop iteration is a Moon month increase
        is_tube_loop_complete = False
        while True:
            actions = []
            # Every Months, there are new resources available. Retry to build the route loop if incomplete.
            is_last_tube_route_built = True
            while (not is_tube_loop_complete) and is_last_tube_route_built:
                end_of_tube_route_building = buildings[next_tube_route_building_index]
                next_tube_route_building_index = (next_tube_route_building_index + 1) % len(buildings)
                next_tube_route_building = buildings[next_tube_route_building_index]
                next_tube = Tube(end_of_tube_route_building, next_tube_route_building)
                is_next_tube_route_buildable = (next_tube.cost <= n_resources)
                if is_next_tube_route_buildable:
                    n_resources = next_tube.build(n_resources, actions, tubes)
                    is_last_tube_route_built = True  # This assignment is redundant and optional.
                    is_tube_loop_complete = (next_tube_route_building == expected_end_of_tube_route_building)
                else:
                    is_last_tube_route_built = False

            # The loop is complete! Let's start building 2 Pods that loops in the two directions (clockwise and counter)!
            if is_tube_loop_complete and n_resources >= Pod.COST and len(pods) < 2:
                next_pod_id = str(int(pods[-1].id) + 1) if pods else "1"
                stops = [b.id for b in buildings]
                if len(pods) % 2:
                    stops[1:] = stops[1:][::-1]
                stops.append(stops[0])
                Logger.log(f"{pods=}")
                pod = Pod(next_pod_id, stops)
                n_resources = pod.build(n_resources, actions, pods)

            if actions:
                print(";".join(actions))
            else:
                print(f"{Action.WAIT.value}")

            Logger.log(f"Month {n_month=} ends with: {n_resources=}, {tubes=}, {teleporters=}, {pods=}, {moon_modules=}, {landing_areas=}")

            # Next Month variables initiation
            n_month += 1
            month_n_resources, month_tubes, month_teleporters, month_pods, month_landing_areas, month_moon_modules = Parser.parse(n_month)

            n_resources = month_n_resources
            assert len(tubes) == len(month_tubes)
            tubes = month_tubes

            assert len(month_teleporters) == len(teleporters)
            month_teleporters = teleporters

            assert len(month_pods) == len(pods)
            month_pods = pods

            moon_modules += month_moon_modules
            landing_areas += month_landing_areas
            buildings = landing_areas + moon_modules


Game.play()