import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy


class move(Node):

    def __init__(self):
        super().__init__('move')
        qos=QoSProfile(depth = 10,
        reliability=QoSReliabilityPolicy.BEST_EFFORT,
        history=QoSHistoryPolicy.KEEP_LAST
              )
        self.publisher_ = self.create_publisher(Twist, "/cmd_vel",qos)
        timer_period = 1.0  # seconds
        self.timer = self.create_timer(timer_period, self.timer_callback)
        self.timer_callback
        self.get_logger().info('publishing forward')

    def timer_callback(self):
        msgStraight = Twist()
        msgStraight.linear.x = 1.0
        msgStraight.angular.z = 0.5
        self.publisher_.publish(msgStraight)


def main(args=None):
    rclpy.init(args=args)

    minimal_publisher = move()

    rclpy.spin(minimal_publisher)

    # Destroy the node explicitly
    # (optional - otherwise it will be done automatically
    # when the garbage collector destroys the node object)
    minimal_publisher.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
