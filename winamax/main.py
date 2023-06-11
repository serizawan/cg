from enum import Enum
from copy import deepcopy


class Directions(Enum):
    UP = (-1, 0)
    DOWN = (1, 0)
    LEFT = (0, -1)
    RIGHT = (0, 1)

    def __str__(self):
        if self.value == (-1, 0):
            return "^"
        elif self.value == (1, 0):
            return "v"
        elif self.value == (0, -1):
            return "<"
        else:
            return ">"


class Item:
    def __init__(self, i, j):
        self.i_init = i
        self.j_init = j
        self.i = i
        self.j = j


class Ball(Item):
    def __init__(self, i, j, n_remaining_hits):
        super().__init__(i, j)
        self.n_remaining_hits = n_remaining_hits
        self.past_moves = []
        self.paths = []

    @property
    def previous_positions(self):
        current_position = (self.i, self.j)
        crossed_positions = set((move.i, move.j) for move in self.past_moves) if self.past_moves else set()
        return crossed_positions.union({current_position})

    @property
    def is_on_hole(self):
        is_on_holes = [self.i == hole.i and self.j == hole.j for hole in HOLES]
        return any(is_on_holes), is_on_holes.index(True) if any(is_on_holes) else None

    """
    Return the list of future moves if the ball was hit in a given direction.
    """
    def compute_future_moves(self, direction):
        future_moves = []
        for k in range(self.n_remaining_hits):
            future_move = Move(self.i + direction.value[0] * k, self.j + direction.value[1] * k, direction)
            future_moves.append(future_move)
        return future_moves

    """
    Return True if the ball is hittable in a given direction.
    A ball is hittable in a direction if:
      (1) It has remaining hits allowed.
      (2) It doesn't end out of the course.
      (3) It doesn't end on an obstacle.
      (4) It doesn't run over nor end on a previously crossed position.
      (5) It doesn't run over nor end on any ball.
      (6) It doesn't run over a hole.
    """
    def is_hittable(self, direction):
        future_moves = self.compute_future_moves(direction)

        # Future positions are future move positions skipping the first one and adding the final position.
        future_positions = set((future_move.i, future_move.j) for future_move in future_moves[1:])
        final_position = (self.i + direction.value[0] * self.n_remaining_hits, self.j + direction.value[1] * self.n_remaining_hits)
        future_positions.add(final_position)

        # Condition (1)
        has_remaining_hits = bool(self.n_remaining_hits)

        # Condition (2)
        ends_on_course = 0 <= final_position[0] < COURSE.height and 0 <= final_position[1] < COURSE.width

        # Condition (3)
        ends_on_no_obstacle = all(final_position[0] != obstacle.i or final_position[1] != obstacle.j for obstacle in OBSTACLES)

        # Condition (4)
        does_not_cross_nor_end_on_self_path = not self.previous_positions.intersection(future_positions)

        # Condition (5)
        does_not_cross_nor_end_on_ball = not future_positions.intersection(set((ball.i_init, ball.j_init) for ball in balls))

        # Condition (6)
        does_not_cross_hole = not (future_positions - {final_position}).intersection(set((hole.i, hole.j) for hole in HOLES))

        _is_hittable = (has_remaining_hits and
                        ends_on_course and
                        ends_on_no_obstacle and
                        does_not_cross_nor_end_on_self_path and
                        does_not_cross_nor_end_on_ball and
                        does_not_cross_hole)

        return _is_hittable

    def hit(self, direction):
        self.past_moves += self.compute_future_moves(direction)
        self.i = self.i + direction.value[0] * self.n_remaining_hits
        self.j = self.j + direction.value[1] * self.n_remaining_hits
        self.n_remaining_hits -= 1


class Obstacle(Item):
    SYMBOL = "X"


class Hole(Item):
    SYMBOL = "H"


class Move:
    def __init__(self, i, j, direction):
        self.i = i
        self.j = j
        self.direction = direction


class EmptyField(Item):
    SYMBOL = "."


class Reader:
    @staticmethod
    def read_input():
        height = int(input().split()[1])
        matrix = []
        for i in range(height):
            row = list(input())
            matrix.append(row)
        return matrix


class Parser:
    @staticmethod
    def parse(matrix):
        course = Course(matrix)
        holes, obstacles, balls = [], [], []
        for i, row in enumerate(course.matrix):
            for j, symbol in enumerate(row):
                if symbol == EmptyField.SYMBOL:
                    pass
                elif symbol == Obstacle.SYMBOL:
                    obstacles.append(Obstacle(i, j))
                elif symbol == Hole.SYMBOL:
                    holes.append(Hole(i, j))
                else:
                    balls.append(Ball(i, j, int(symbol)))
        return course, holes, obstacles, balls


class Course:
    def __init__(self, matrix):
        self.matrix = matrix

    @property
    def height(self):
        return len(self.matrix)

    @property
    def width(self):
        return len(self.matrix[0])

    def __str__(self):
        return "\n".join(["".join(row) for row in self.matrix])


class Path:
    def __init__(self, start, end, to_hole, hole_index, moves):
        self.start = start
        self.end = end
        self.moves = moves
        self.to_hole = to_hole
        self.hole_index = hole_index

    """
    Return True if two paths do not cross. As a consequence, it checks that two paths don't reach the same hole.
    """
    def does_not_cross(self, other_path):
        self_final_position = (self.end[0], self.end[1])
        self_crossed_positions = set((move.i, move.j) for move in self.moves) if self.moves else set()
        self_previous_positions = self_crossed_positions.union({self_final_position})

        other_path_final_position = (other_path.end[0], other_path.end[1])
        other_path_crossed_positions = set((move.i, move.j) for move in other_path.moves) if other_path.moves else set()
        other_path_previous_positions = other_path_crossed_positions.union({other_path_final_position})

        return not self_previous_positions.intersection(other_path_previous_positions)


class PathFinder:
    def __init__(self, ball):
        self.ball = ball

    """
    Compute allowed paths to holes for a given ball using a DFS algorithm.
    """
    def find_paths(self, paths):
        # Success: Ball did reach a hole.
        if self.ball.is_on_hole[0]:
            path = Path((self.ball.i_init, self.ball.j_init), (self.ball.i, self.ball.j), self.ball.is_on_hole[0], self.ball.is_on_hole[1], self.ball.past_moves)
            paths.append(path)
            return paths

        for direction in Directions:
            if self.ball.is_hittable(direction):
                ball = deepcopy(self.ball)
                self.ball.hit(direction)
                paths = self.find_paths(paths)
                self.ball = ball

        # Failure: Ball didn't reach any hole and is not hittable hence back-track.
        return paths


class PathResolver:
    def __init__(self, balls):
        self.balls = balls

    """
    Compute ball's unique path to avoid paths cross and cover all holes using a DFS algorithm.
    """
    def resolve_paths(self, paths, is_found):
        # Success: The unique solution has been found!
        if len(paths) == len(balls):
            return True

        ball = balls[len(paths)]
        for ball_path in ball.paths:
            if all(ball_path.does_not_cross(path) for path in paths):
                paths.append(ball_path)
                is_found = self.resolve_paths(paths, is_found)
                if not is_found:
                    paths.pop()

        # Failure: Paths list do not provide a solution hence back-track.
        return is_found


class SolutionPrinter:
    def __init__(self, paths):
        self.paths = paths

    def print(self):
        solution_course = [list(EmptyField.SYMBOL * COURSE.width) for i in range(COURSE.height)]
        for path in self.paths:
            for move in path.moves:
                solution_course[move.i][move.j] = str(move.direction)

        print("\n".join(["".join(row) for row in solution_course]))


if __name__ == "__main__":
    COURSE, HOLES, OBSTACLES, balls = Parser.parse(Reader.read_input())
    for ball in balls:
        paths = PathFinder(ball).find_paths([])
        # Compute allowed paths to holes for each ball.
        ball.paths = paths

    # Compute unique solution.
    solution = []
    PathResolver(balls).resolve_paths(solution, False)

    SolutionPrinter(solution).print()
