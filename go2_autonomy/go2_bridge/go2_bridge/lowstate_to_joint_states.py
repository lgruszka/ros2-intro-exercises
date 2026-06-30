"""Adapter: /lowstate -> /joint_states for robot_state_publisher (Go2 variant).

Unitree Go2 firmware publikuje /lowstate (unitree_go/LowState) z 12
pozycjami motorów (4 nogi × 3 stawy: hip, thigh, calf). robot_state_publisher
potrzebuje /joint_states (sensor_msgs/JointState) z URDF joint names żeby
policzyć TF.

Mapowanie motor index → joint name per Unitree SDK2 konwencja Go2:
  0..2:  FR (front-right) hip / thigh / calf
  3..5:  FL (front-left)
  6..8:  RR (rear-right)
  9..11: RL (rear-left)

Joint names matchują unitree_ros/robots/go2_description/urdf/go2_description.urdf.
"""
from __future__ import annotations

import sys
from typing import List, Optional

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState

try:
    from unitree_go.msg import LowState
    UNITREE_GO_OK = True
    UNITREE_GO_ERR: Optional[Exception] = None
except ImportError as exc:
    LowState = None  # type: ignore[assignment]
    UNITREE_GO_OK = False
    UNITREE_GO_ERR = exc


# Go2 12-DoF motor index -> joint name (matches go2_description URDF).
DEFAULT_JOINT_NAMES: List[str] = [
    'FR_hip_joint',      # 0
    'FR_thigh_joint',    # 1
    'FR_calf_joint',     # 2
    'FL_hip_joint',      # 3
    'FL_thigh_joint',    # 4
    'FL_calf_joint',     # 5
    'RR_hip_joint',      # 6
    'RR_thigh_joint',    # 7
    'RR_calf_joint',     # 8
    'RL_hip_joint',      # 9
    'RL_thigh_joint',    # 10
    'RL_calf_joint',     # 11
]


class LowStateToJointStates(Node):
    def __init__(self) -> None:
        super().__init__('lowstate_to_joint_states')
        self.declare_parameter('lowstate_topic', '/lowstate')
        self.declare_parameter('joint_states_topic', '/joint_states')
        # Comma-separated override; empty = use DEFAULT_JOINT_NAMES (Go2 12-DoF).
        self.declare_parameter('joint_names_csv', '')

        in_topic = str(self.get_parameter('lowstate_topic').value)
        out_topic = str(self.get_parameter('joint_states_topic').value)
        csv = str(self.get_parameter('joint_names_csv').value).strip()
        self._joint_names = (
            [name.strip() for name in csv.split(',') if name.strip()]
            if csv else DEFAULT_JOINT_NAMES
        )

        self._pub = self.create_publisher(JointState, out_topic, 10)
        self._sub = self.create_subscription(LowState, in_topic, self._on_lowstate, 10)
        self.get_logger().info(
            f'lowstate_to_joint_states ready '
            f'({in_topic} -> {out_topic}, {len(self._joint_names)} joints)'
        )

    def _on_lowstate(self, msg) -> None:
        out = JointState()
        out.header.stamp = self.get_clock().now().to_msg()
        out.name = list(self._joint_names)
        n = len(self._joint_names)
        out.position = [float(msg.motor_state[i].q) for i in range(n)]
        out.velocity = [float(msg.motor_state[i].dq) for i in range(n)]
        out.effort = [float(msg.motor_state[i].tau_est) for i in range(n)]
        self._pub.publish(out)


def main(args=None) -> None:
    if not UNITREE_GO_OK:
        sys.stderr.write(
            f'lowstate_to_joint_states requires unitree_go messages. '
            f'Import error: {UNITREE_GO_ERR}\n'
        )
        return
    rclpy.init(args=args)
    node = LowStateToJointStates()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
