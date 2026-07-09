import random

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from turtlesim.srv import Spawn

PREY_NAMES = ['prey1', 'prey2', 'prey3']
ARENA_MIN = 1.0
ARENA_MAX = 10.0


class GameManagerNode(Node):
    def __init__(self):
        super().__init__('game_manager_node')

        self.alive = set()
        self.score = 0

        self.spawn_cli = self.create_client(Spawn, '/spawn')
        self.create_subscription(String, '/captures', self.on_capture, 10)
        # Pierwsze 2s czekamy aż turtlesim wstanie, potem co sekundę
        # uzupełniamy brakujące ofiary.
        self.create_timer(1.0, self.respawn_tick)

        self.get_logger().info('Game manager ready')

    def on_capture(self, msg):
        name = msg.data
        self.alive.discard(name)
        self.score += 1
        self.get_logger().info(f'Capture: {name} → score: {self.score}')

    def respawn_tick(self):
        if not self.spawn_cli.service_is_ready():
            return
        for name in PREY_NAMES:
            if name in self.alive:
                continue
            req = Spawn.Request()
            req.name = name
            req.x = random.uniform(ARENA_MIN, ARENA_MAX)
            req.y = random.uniform(ARENA_MIN, ARENA_MAX)
            req.theta = random.uniform(-3.14, 3.14)
            future = self.spawn_cli.call_async(req)
            future.add_done_callback(
                lambda f, n=name: self._on_spawn_done(n, f))

    def _on_spawn_done(self, name, future):
        try:
            future.result()
            self.alive.add(name)
            self.get_logger().info(f'Spawned {name}')
        except Exception:
            # Zajęta nazwa — turtlesim już ma ten żółw.
            self.alive.add(name)


def main(args=None):
    rclpy.init(args=args)
    rclpy.spin(GameManagerNode())
    rclpy.shutdown()


if __name__ == '__main__':
    main()
