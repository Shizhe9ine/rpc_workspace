import rclpy
import math
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist


class MinimalSubscriber(Node):
    def __init__(self):
        super().__init__("scan_for_obstacles")

        self.timer = self.create_timer(0.1, self.cmd)
        self.closest = math.inf
        self.have_scan = False
        self.qos = QoSProfile(
            depth=10,
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
        )

        self.cmd_qos = QoSProfile(
            depth=10,
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
        )

        # self.subscription  # prevent unused variable warning

        self.sub = self.create_subscription(LaserScan, "/scan", self.on_scan, self.qos)
        self.pub = self.create_publisher(Twist, "cmd_vel", self.cmd_qos)
        # elf.stop_distance = 0.2

    def on_scan(self, msg: LaserScan):
        finite = [r for r in msg.ranges if (math.isfinite(r) and r > 0.15)]
        self.closest = min(finite) if finite else math.inf
        self.have_scan = True

    def cmd(self):
        msg = Twist()
        if not self.have_scan:
            self.pub.publish(msg)
            self.get_logger().warn("no scan received yet")
            return

        if self.closest < 1.0:
            msg.linear.x = 0.5
            msg.angular.z = 0.1
            self.get_logger().info("slowing down")
            if self.closest < 0.75:
                msg.linear.x = 0.25
                msg.angular.z = 0.2
                if self.closest < 0.5:
                    msg.linear.x = 0.05
                    msg.angular.z = 0.3
                    self.get_logger().info("no movement")

        else:
            msg.linear.x = 1.0
            msg.angular.z = 0.0
            self.get_logger().info("move")

        self.pub.publish(msg)
        self.get_logger().info(
            f"closest = {self.closest:.3f}m | cmd.linear.x = {msg.linear.x:.2f}"
        )


def main(args=None):
    rclpy.init(args=args)

    minimal_subscriber = MinimalSubscriber()
    rclpy.spin(minimal_subscriber)

    # Destroy the node explicitly
    # (optional - otherwise it will be done automatically
    # when the garbage collector destroys the node object)
    minimal_subscriber.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
