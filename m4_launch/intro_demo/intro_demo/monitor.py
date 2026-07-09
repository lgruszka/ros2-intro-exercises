"""
Module 4 — Monitor node.

Subskrybuje wszystkie topiki /count_* dynamicznie wykrywane przez DDS.
Co 2 sekundy loguje sumę otrzymanych wartości per topic.

ros2 run intro_demo monitor
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32


class Monitor(Node):
    def __init__(self):
        super().__init__('monitor')
        self.subscriptions_map = {}
        self.latest = {}

        # Co 1 sekundę: skanuj graf i subskrybuj nowe /count_*
        self.scan_timer = self.create_timer(1.0, self.scan_topics)
        # Co 2 sekundy: loguj sumę
        self.report_timer = self.create_timer(2.0, self.report)

        self.get_logger().info('Monitor scanning for /count_* topics')

    def scan_topics(self):
        topics = self.get_topic_names_and_types()
        for name, types in topics:
            if (name.startswith('/count_')
                    and name not in self.subscriptions_map
                    and 'std_msgs/msg/Int32' in types):
                self.get_logger().info(f'Subscribing to {name}')
                sub = self.create_subscription(
                    Int32,
                    name,
                    lambda msg, n=name: self.on_msg(n, msg),
                    10,
                )
                self.subscriptions_map[name] = sub

    def on_msg(self, topic, msg):
        self.latest[topic] = msg.data

    def report(self):
        if not self.latest:
            return
        items = ', '.join(f'{t}={v}' for t, v in sorted(self.latest.items()))
        total = sum(self.latest.values())
        self.get_logger().info(f'{items} → suma {total}')


def main():
    rclpy.init()
    node = Monitor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
