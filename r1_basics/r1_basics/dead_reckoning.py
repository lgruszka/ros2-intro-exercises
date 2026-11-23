#!/usr/bin/env python3
"""dead_reckoning - odometria zliczeniowa R1: prędkość zadana (vx, vy) + kurs z IMU -> /r1/odom.

R1 nie ma potwierdzonego tematu odometrii (docs/r1_plan.md §4), więc liczymy ją sami:
  - prędkość: /r1/cmd_vel_sent (to, co most naprawdę wysłał robotowi, po limitach), rama robota,
  - kurs: /lowstate imu_state.rpy[2] minus kurs z pierwszej odebranej wiadomości (start = 0),
  - x, y: całkowanie co 1/rate_hz.
Dryf rośnie z drogą (robot nie idzie idealnie z zadaną prędkością): cele do ok. 2 m, sprawdzaj taśmą.
"""
import math

from geometry_msgs.msg import TransformStamped, Twist
from nav_msgs.msg import Odometry
from r1_basics.params import declare_float
from r1_basics.util import integrate_body_velocity, wrap_angle, yaw_to_quat
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from tf2_ros import TransformBroadcaster
from unitree_hg.msg import LowState

ODOM_FRAME = 'odom'
BASE_FRAME = 'base_link'
IMU_STALE_S = 0.5


class DeadReckoning(Node):
    def __init__(self):
        super().__init__('dead_reckoning')
        rate_hz = declare_float(self, 'rate_hz', 20.0)
        self.cmd_timeout_s = declare_float(self, 'cmd_timeout_s', 0.5)
        self.publish_tf = bool(self.declare_parameter('publish_tf', True).value)

        self.create_subscription(Twist, '/r1/cmd_vel_sent', self.on_cmd, 10)
        self.create_subscription(LowState, '/lowstate', self.on_lowstate, qos_profile_sensor_data)
        self.odom_pub = self.create_publisher(Odometry, '/r1/odom', 10)
        self.tf_broadcaster = TransformBroadcaster(self) if self.publish_tf else None

        self.x = self.y = 0.0
        self.heading = 0.0
        self.yaw0 = None
        self.gyro_z = 0.0
        self.cmd = Twist()
        self.cmd_time = None
        self.imu_time = None
        self.last_tick = None
        self.create_timer(1.0 / max(rate_hz, 1.0), self.tick)
        self.get_logger().info(
            f'dead_reckoning: /r1/cmd_vel_sent + /lowstate (IMU yaw) -> /r1/odom ({ODOM_FRAME} -> '
            f'{BASE_FRAME}), {rate_hz:.0f} Hz, TF {"tak" if self.publish_tf else "nie"}')

    def on_cmd(self, msg):
        self.cmd = msg
        self.cmd_time = self.get_clock().now()

    def on_lowstate(self, msg):
        yaw = float(msg.imu_state.rpy[2])
        if self.yaw0 is None:
            self.yaw0 = yaw
            self.get_logger().info(f'kurs startowy z IMU: {yaw:.3f} rad (w /r1/odom to będzie 0)')
        self.heading = wrap_angle(yaw - self.yaw0)
        self.gyro_z = float(msg.imu_state.gyroscope[2])
        self.imu_time = self.get_clock().now()

    def age(self, stamp, now):
        return math.inf if stamp is None else (now - stamp).nanoseconds * 1e-9

    def tick(self):
        now = self.get_clock().now()
        if self.yaw0 is None:
            self.get_logger().warning('czekam na /lowstate (kurs z IMU)...', throttle_duration_sec=2.0)
            self.last_tick = now
            return
        if self.age(self.imu_time, now) > IMU_STALE_S:
            self.get_logger().warning('/lowstate nieświeże - kurs zamrożony, odometria niepewna',
                                      throttle_duration_sec=2.0)
        dt = 0.0 if self.last_tick is None else (now - self.last_tick).nanoseconds * 1e-9
        self.last_tick = now
        if self.age(self.cmd_time, now) <= self.cmd_timeout_s:
            vx, vy = self.cmd.linear.x, self.cmd.linear.y
        else:
            vx = vy = 0.0          # most milczy = robot stoi
        self.x, self.y = integrate_body_velocity(self.x, self.y, self.heading, vx, vy, dt)
        self.publish(now, vx, vy)

    def publish(self, now, vx, vy):
        qx, qy, qz, qw = yaw_to_quat(self.heading)
        odom = Odometry()
        odom.header.stamp = now.to_msg()
        odom.header.frame_id = ODOM_FRAME
        odom.child_frame_id = BASE_FRAME
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.orientation.x, odom.pose.pose.orientation.y = qx, qy
        odom.pose.pose.orientation.z, odom.pose.pose.orientation.w = qz, qw
        odom.twist.twist.linear.x = float(vx)
        odom.twist.twist.linear.y = float(vy)
        odom.twist.twist.angular.z = self.gyro_z
        self.odom_pub.publish(odom)
        if self.tf_broadcaster is not None:
            tf = TransformStamped()
            tf.header = odom.header
            tf.child_frame_id = BASE_FRAME
            tf.transform.translation.x = self.x
            tf.transform.translation.y = self.y
            tf.transform.rotation = odom.pose.pose.orientation
            self.tf_broadcaster.sendTransform(tf)


def main(args=None):
    rclpy.init(args=args)
    node = DeadReckoning()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
