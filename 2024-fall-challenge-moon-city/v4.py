# Welcome to my Selenia Optimization Tool. Let's build an eco-friendly city!
# The script builds a tube network that connects ALL available buildings.
# Only after, if there are resources left, it builds pods (1 pod / astronaut type / landing area).
# These pods do back and forth between landing area and the closest Moon Module with the corresponding astronaut type.
# Score ~ 3M
# Sample Score ~ 2.6M
# Example 1 ~ 53k
# Example 2 ~ 106k
# Balancing ~ 149k
# Crater Exploration ~ 179k
# Pair ~ 148k
# Villages ~ 60k
# Spiral ~ 357k
# Grid ~ 337k
# Expansion ~ 466k
# Groups ~ 392k
# Concentric Layers ~ 197k
# Distribution Network ~ 201k
from collections import deque
from enum import Enum
import math
import sys

N_MONTHS = 20
N_DAYS_PER_MONTH = 20
REMAINING_RESOURCES_INTEREST_RATE = 0.1
MAX_MONTHLY_LANDINGS = 1_000


class Logger:
    IS_ENABLED = True
    MAX_LEVEL = 0

    @staticmethod
    def log(msg, level=0):
        if Logger.IS_ENABLED and level <= Logger.MAX_LEVEL:
            print(msg, file=sys.stderr, flush=True)


class MathExt:
    @staticmethod
    # Return the signed area formed by p1, p2, p3 (> 0 when (p1, p2, p3) turn counter-clockwise)
    def cross_product(p1, p2, p3):
        return (p2.y - p1.y) * (p3.x - p2.x) - (p2.x - p1.x) * (p3.y - p2.y)

    @staticmethod
    def orientation(p1, p2, p3):
        def sign(x):
            if x > 0:
                return 1
            elif x < 0:
                return -1
            else:
                return 0
        return sign(MathExt.cross_product(p1, p2, p3))

    @staticmethod
    def is_on(p, p1, p2):
        if MathExt.cross_product(p, p1, p2) == 0:
            return (min(p1.x, p2.x) <= p.x <= max(p1.x, p2.x)) and (min(p1.y, p2.y) <= p.y <= max(p1.y, p2.y))
        return False


class Action(Enum):
    TUBE = "TUBE"
    UPGRADE = "UPGRADE"
    TELEPORT = "TELEPORT"
    POD = "POD"
    DESTROY = "DESTROY"
    WAIT = "WAIT"


class Map:
    MAX_X = 160  # km
    MAX_Y = 90  # km


class Route:
    def __init__(self, capacity):
        self.capacity = capacity


class Tube(Route):
    COST_PER_100M = 1

    # A tube is bi-directional, b1 and b2 can be interchanged.
    def __init__(self, b1, b2, capacity=1):
        super().__init__(capacity)
        self.b1 = b1
        self.b2 = b2

    @property
    def length(self):
        return math.sqrt((self.b1.x - self.b2.x) ** 2 + (self.b1.y - self.b2.y) ** 2)

    @property
    def cost(self):
        return math.floor(self.length * 10) * self.COST_PER_100M  # Factor 10 to get the length in 100m units

    def upgrade(self, n_resources, actions):
        self.capacity += 1
        n_resources -= self.cost * self.capacity
        actions.append(f"{Action.UPGRADE.value} {self.b1.id} {self.b2.id}")
        return n_resources

    # Return whether two tubes are crossing each-other.
    def does_cross(self, other_tube):
        does_c1 = MathExt.orientation(self.b1, self.b2, other_tube.b1) * MathExt.orientation(self.b1, self.b2, other_tube.b2) < 0
        does_c2 = MathExt.orientation(other_tube.b1, other_tube.b2, self.b1) * MathExt.orientation(other_tube.b1, other_tube.b2, self.b2) < 0
        return does_c1 and does_c2

    def __str__(self):
        return f"({self.b1.id=}, {self.b2.id=}, {self.capacity=})"

    def __repr__(self):
        return self.__str__()


class Network:
    def __init__(self, tubes, teleporters):
        self.tubes = tubes
        self.teleporters = teleporters

    def build_tube(self, tube, n_resources, actions):
        n_resources -= tube.cost
        actions.append(f"{Action.TUBE.value} {tube.b1.id} {tube.b2.id}")
        Logger.log(f"[{Action.TUBE.value}] Plan a tube build, {tube.b1.id=}, {tube.b2.id=}, {tube.cost=}, {n_resources=}", 1)
        self.tubes.add(tube)
        return n_resources

    def build_teleporter(self, teleporter, n_resources, actions):
        n_resources -= teleporter.COST
        actions.append(f"{Action.TELEPORT.value} {teleporter.b_in.id} {teleporter.b_out.id}")
        Logger.log(f"[{Action.TUBE.value}] Plan a teleporter build, {teleporter.b_in.id=}, {teleporter.b_out.id=}, {Teleporter.COST=}, {n_resources=}", 1)
        self.teleporters.add(teleporter)
        return n_resources

    def __str__(self):
        return str(self.tubes)

    def __repr__(self):
        return self.__str__()


class Item:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def dist(self, item):
        return math.sqrt((self.x - item.x)**2 + (self.y - item.y)**2)


class City:
    def __init__(self, campus, network, n_resources, fleet):
        self.campus = campus
        self.network = network
        self.n_resources = n_resources
        self.fleet = fleet

    def build(self, actions):
        self.build_network(actions)
        self.build_fleet(actions)
        # Upgrade tubes if there are enough remaining resources when there are less than 10 buildings.
        if len(self.campus.buildings) <= 10:
            for tube in self.network.tubes:
                if tube.capacity == 1 and self.n_resources >= tube.cost * 2:
                    self.n_resources = tube.upgrade(self.n_resources, actions)

    def build_network(self, actions):
        self.build_tube_network(actions)
        self.build_teleporter_network(actions)

    def build_tube_network(self, actions):
        # No network has yet been built. Hence, we pick the most central landing area as a starting station for the tube network.
        if not self.network.tubes:
            from_building = sorted(list(self.campus.landing_areas), key=lambda b: b.dist(Item(Map.MAX_X // 2, Map.MAX_Y //2)))[0]
            # from_building = next(iter(self.campus.landing_areas))
            self.extend_tube_network_as_star(deque([from_building]), actions)
        # The city already has a network. Hence, we pick any connected building with less than Building.MAX_TUBES tubes that can reach a non-connected building
        # as a starting station for the tube network extension. Once the network is extended, if there are remaining non-connected buildings, another building that meet the
        # aforementionned conditions is picked.
        else:
            for building in self.campus.buildings:
                if building.tos and len(building.tos) < Building.MAX_TUBES and any(not b.tos and self.is_allowed(Tube(building, b)) for b in self.campus.buildings):
                    from_building = building
                    self.extend_tube_network_as_star(deque([from_building]), actions)

    def extend_tube_network_as_line(self, from_building, actions):
        if self.campus.is_connected():
            return

        closest_buildings = sorted(list(self.campus.buildings), key=lambda b: b.dist(from_building))[1:]  # Remove first building from the list as it is from_building

        is_to_added = False
        i = 0
        while not is_to_added and i < len(closest_buildings):
            next_closest_building = closest_buildings[i]
            tube = Tube(from_building, next_closest_building)
            if not next_closest_building.tos and self.is_allowed(tube) and self.n_resources >= tube.cost:
                self.n_resources = self.network.build_tube(tube, self.n_resources, actions)
                from_building.tos.add(next_closest_building)
                next_closest_building.tos.add(from_building)
                is_to_added = True
                self.extend_tube_network_as_line(next_closest_building, actions)
            i += 1

        # Backtrack as there are no allowed building as candidate for a tube depiste campus is not connected.
        if not self.campus.is_connected() and i < len(closest_buildings):
            self.extend_tube_network_as_line(from_building, actions)


    def extend_tube_network_as_star(self, from_buildings_queue, actions):
        n_star_extension_edges = 2
        max_neighbor_checks = 20
        max_tube_len = 30  # km
        if self.campus.is_connected():
            return

        while from_buildings_queue:
            from_building = from_buildings_queue.popleft()
            closest_buildings = sorted(list(self.campus.buildings), key=lambda b: b.dist(from_building))[1:]  # Remove first building from the list as it is from_building
            added_extension = 0
            i = 0
            while added_extension != n_star_extension_edges and i < len(closest_buildings[:max_neighbor_checks]):
                next_closest_building = closest_buildings[i]
                tube = Tube(from_building, next_closest_building)
                if not next_closest_building.tos and self.is_allowed(tube) and self.n_resources >= tube.cost:
                    if added_extension >= 1 and tube.length > max_tube_len:
                        i += 1
                        continue
                    self.n_resources = self.network.build_tube(tube, self.n_resources, actions)
                    from_building.tos.add(next_closest_building)
                    next_closest_building.tos.add(from_building)
                    from_buildings_queue.append(next_closest_building)
                    added_extension += 1
                i += 1


    def build_teleporter_network(self, actions):
        for landing_area in self.campus.landing_areas:
            for module_type in landing_area.unserved_moon_module_types:
                itinerary = landing_area.find_itinerary_to_closest_typed_module(module_type, enable_tp=True)
                if not landing_area.tos_tp and not itinerary and self.n_resources >= Teleporter.COST:
                    b_out = None
                    for building in self.campus.buildings:
                        if building.type == module_type and not building.froms_tp:
                            b_out = building
                            break
                    if b_out:
                        teleporter = Teleporter(landing_area, b_out)
                        landing_area.tos_tp.add(b_out)
                        b_out.froms_tp.add(landing_area)
                        self.n_resources = self.network.build_teleporter(teleporter, self.n_resources, actions)

    def build_fleet(self, actions):
        for landing_area in self.campus.landing_areas:
            itineraries = []
            for module_type in landing_area.unserved_moon_module_types:
                if itinerary := landing_area.find_itinerary_to_closest_typed_module(module_type, enable_tp=True):
                    itineraries.append(itinerary)
            itineraries.sort(key=lambda itinerary: len(itinerary), reverse=True)
            for itinerary in itineraries:
                pods = []
                pod_itineraries = []
                prev_tp_idx = 0
                for i in range(len(itinerary)-1):
                    if itinerary[i+1] in itinerary[i].tos_tp:
                        if len(itinerary[prev_tp_idx:i+1]) > 1:
                            pod_itineraries.append(itinerary[prev_tp_idx:i+1])
                        prev_tp_idx = i + 1
                if len(itinerary[prev_tp_idx:]) > 1:
                    pod_itineraries.append(itinerary[prev_tp_idx:])
                for i, pod_itinerary in enumerate(pod_itineraries):
                    itinerary_ids = [b.id for b in pod_itinerary]
                    pod = Pod(len(self.fleet.pods) + i + 1, itinerary_ids + list(reversed(itinerary_ids))[1:])
                    pods.append(pod)
                if self.n_resources >= Pod.COST * len(pods):
                    for pod in pods:
                        self.n_resources = self.fleet.build(pod, self.n_resources, actions)
                    landing_area.unserved_moon_module_types.remove(itinerary[-1].type)


    # Return whether a tube can be built under the Game constraints:
    #    - Do not cross any building (C1)
    #    - Do not cross any tube (C2)
    #    - Do not join buildings with already 5 tubes connections (C3)
    # Note that being allowed do not mean being buildable in term of resources!
    def is_allowed(self, tube):
        # (C1)
        for b in self.campus.buildings:
            if b != tube.b1 and b != tube.b2 and b.is_on(tube):
                return False

        # (C2)
        for t in self.network.tubes:
            if t != tube and tube.does_cross(t):
                return False

        # (C3)
        return len(tube.b1.tos) < Building.MAX_TUBES and len(tube.b2.tos) < Building.MAX_TUBES


class Teleporter(Route):
    T_PER_TELEPORT = 0
    COST = 5_000

    # Be careful here, a teleporter is NOT bi-directional, there is an entrance and an exit
    def __init__(self, b_in, b_out):
        self.b_in = b_in
        self.b_out = b_out
        super().__init__(math.inf)


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

    def destroy(self, n_resources, actions):
        n_resources += Pod.RECYCLABLE_RESOURCES
        actions.append(f"{Action.DESTROY.value} {self.id}")
        return n_resources

    def __str__(self):
        return f"({self.id=}, {self.stops=})"

    def __repr__(self):
        return self.__str__()


class Fleet:
    def __init__(self, pods):
        self.pods = pods

    def build(self, pod, n_resources, actions):
        n_resources -= Pod.COST
        actions.append(f"{Action.POD.value} {pod.id} {' '.join(pod.stops)}")
        # Logger.log(f"[{Action.POD.value}] Plan a pod build (and schedule), {Pod.COST=}, {n_resources=}")
        self.pods.add(pod)
        return n_resources


class Building(Item):
    MAX_TOTAL_BUILDINGS = 150
    MAX_TELEPORTERS = 1
    MAX_TUBES = 5

    def __init__(self, type, id, x, y):
        self.type = type
        self.id = id
        self.tos = set()
        self.tos_tp = set()
        self.froms_tp = set()
        super().__init__(x, y)

    @property
    def tos_ids(self):
        return {b.id for b in self.tos}

    def find_itinerary_to_closest_typed_module(self, module_type, enable_tp, max_depth=15):
        queue = deque()
        queue.append((self, 0))
        visited = set()
        visited.add(self)
        froms = dict()
        froms[self] = None
        while queue:
            building, depth = queue.popleft()
            if building.type == module_type:
                itinerary = []
                while building is not None:
                    itinerary.append(building)
                    building = froms[building]
                itinerary.reverse()
                return itinerary

            if depth >= max_depth:
                return

            tos = building.tos
            if enable_tp:
                tos = tos.union(building.tos_tp)
            for b in tos:
                if b not in visited:
                    visited.add(b)
                    froms[b] = building
                    queue.append((b, depth + 1))
        return

    def is_on(self, tube):
        return MathExt.is_on(self, tube.b1, tube.b2)

    def __str__(self):
        return f"({self.type=}, {self.id=}, {self.x=}, {self.y=}, {self.tos_ids=})"

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
        self.unserved_moon_module_types = set(astronaut.type for astronaut in astronauts)

    @property
    def n_astronauts(self):
        return len(self.astronauts)

    @property
    def astronauts_types_and_counts(self):
        a_types = set([a.type for a in self.astronauts])
        return [(a_type, sum(1 for astronaut in self.astronauts if astronaut.type == a_type)) for a_type in a_types]


    def __str__(self):
        return f"({self.type=}, {self.id=}, {self.x=}, {self.y=}, {self.n_astronauts=}, {self.tos_ids=})"  # {self.astronauts=} can be appended to print astronauts


class Campus:
    def __init__(self, landing_areas, moon_modules):
        self.landing_areas = landing_areas
        self.moon_modules = moon_modules

    @property
    def buildings(self):
        return self.landing_areas.union(self.moon_modules)

    # Return whether ALL buildings have at least one "to".
    # This does not generally guarantee that all buildings are connected together by a single tube network
    # but for the designed network plan algorithm it does!
    def is_connected(self):
        return all(b.tos for b in self.buildings)


class SpacePort:
    def __init__(self, landing_areas):
        self.landing_areas = landing_areas


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
        tubes, teleporters = set(), set()
        for i in range(n_routes):
            b1, b2, capacity = input().split()
            if capacity:
                tubes.add(Tube(b1, b2, int(capacity)))
            else:
                teleporters.add(Teleporter(b1, b2))

        network = Network(tubes, teleporters)

        n_pods = int(input())
        pods = set()
        for i in range(n_pods):
            p_id, _, *stops = input().split()
            pods.add(Pod(p_id, stops))

        n_shipped_buildings = int(input())
        landing_areas = set()
        moon_modules = set()
        for i in range(n_shipped_buildings):
            b_type, b_id, b_x_str, b_y_str, *astronaut_count_and_types = input().split()
            astronaut_types = astronaut_count_and_types[1:]
            if int(b_type):
                moon_modules.add(MoonModule(b_type, b_id, int(b_x_str), int(b_y_str)))
            else:
                astronauts = {Astronaut(a_type, b_id) for a_type in astronaut_types}
                landing_areas.add(LandingArea(b_id, int(b_x_str), int(b_y_str), astronauts))

        Logger.log(f"Month {n_month=} starts with: {n_resources=}")
        # Logger.log(f"Month {n_month=} starts with: {n_resources=}, {network=}, {teleporters=}, {pods=}")  # {moon_modules=}, {landing_areas=}

        campus = Campus(landing_areas, moon_modules)
        fleet = Fleet(pods)
        city = City(campus, network, n_resources, fleet)

        return n_resources, city, teleporters, pods, landing_areas, moon_modules


class Game:
    @staticmethod
    def play():
        # First Month variable initiation
        n_month = 1
        n_resources, city, teleporters, pods, landing_areas, moon_modules = Parser.parse(n_month)

        # One loop iteration is a Moon month increase
        while True:
            # Every Months, there are new resources available.
            actions = []
            city.build(actions)

            if actions:
                print(";".join(actions))
            else:
                print(f"{Action.WAIT.value}")

            # Logger.log(f"Month {n_month=} ends with: {city.n_resources=}, {city.network=}, {teleporters=}, {pods=}") # {moon_modules=}, {landing_areas=}

            # Next Month variables initiation
            n_month += 1
            month_n_resources, month_network, month_teleporters, month_pods, month_landing_areas, month_moon_modules = Parser.parse(n_month)

            n_resources = month_n_resources
            city.n_resources = month_n_resources
            # assert len(tubes) == len(month_tubes)
            # tubes = month_tubes

            # assert len(month_teleporters) == len(teleporters)
            month_teleporters = teleporters

            # assert len(month_pods) == len(pods)
            month_pods = pods

            moon_modules.update(month_moon_modules)
            landing_areas.update(month_landing_areas)
            buildings = landing_areas.union(moon_modules)


Game.play()
