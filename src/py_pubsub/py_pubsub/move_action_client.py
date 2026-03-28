import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import PoseStamped
import math
from nav2_msgs.srv import ClearEntireCostmap


# ros2 service call /local_costmap/clear_entirely_local_costmap nav2_msgs/srv/ClearEntireCostmap "{}"


class MoveActionClient(Node):
    def __init__(self):
        super().__init__("move_action_client")
        self._action_client = ActionClient(self, NavigateToPose, "navigate_to_pose")
        self.get_logger().info("Waiting for action server...")
        self._action_client.wait_for_server()
        self.get_logger().info("Action server available!")
        self.clear_local_costmap.client = self.create_client(
            ClearEntireCostmap,
            "/local_costmap/clear_entirely_local_costmap",
        )
        self.get_logger().info("clearing blabla")
        while not self.clear_local_costmap_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn("Local costmap clear service not available yet...")

        # Timer to continuously clear local costmap
        self.clear_costmap_timer = self.create_timer(
            3.0,  # seconds (adjust if needed)
            self.clear_local_costmap_callback,
        )

        # Goals to alternate
        self.goals = [
            (-3.0, 5.6, 0.0),
            (-5.4, -2.3, 0.0),
        ]
        self.goal_index = 0
        self.sending_goal = False

        # timer to periodically check and send next goal
        self.timer = self.create_timer(1.0, self.timer_callback)

    def create_goal(self, x, y, yaw):
        goal_msg = NavigateToPose.Goal()
        pose = PoseStamped()
        pose.header.frame_id = "map"
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = x
        pose.pose.position.y = y
        pose.pose.position.z = 0.0
        qz = math.sin(yaw / 2.0)
        qw = math.cos(yaw / 2.0)
        pose.pose.orientation.z = qz
        pose.pose.orientation.w = qw
        goal_msg.pose = pose
        return goal_msg

    def timer_callback(self):
        # only send a goal if we're not already sending one
        if not self.sending_goal:
            self.send_next_goal()

    def send_next_goal(self):
        x, y, yaw = self.goals[self.goal_index]
        self.get_logger().info(
            f"Sending goal {self.goal_index}: x={x}, y={y}, yaw={yaw}"
        )
        goal_msg = self.create_goal(x, y, yaw)
        self.sending_goal = True

        send_goal_future = self._action_client.send_goal_async(
            goal_msg, feedback_callback=self.feedback_callback
        )
        send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().info("Goal rejected :(")
            self.sending_goal = False
            return
        self.get_logger().info("Goal accepted :)")
        get_result_future = goal_handle.get_result_async()
        get_result_future.add_done_callback(self.get_result_done_callback)

    def get_result_done_callback(self, future):
        self.get_logger().info(f"Goal finished")
        # Move to next goal
        self.goal_index = (self.goal_index + 1) % len(self.goals)
        self.sending_goal = False  # allow next goal to be sent

    def feedback_callback(self, feedback_msg):
        feedback = feedback_msg.feedback
        est_time_sec = (
            feedback.estimated_time_remaining.sec
            + feedback.estimated_time_remaining.nanosec * 1e-9
        )

        self.get_logger().info(
            f"Distance remaining: {feedback.distance_remaining:.2f} m | "
            f"Estimated time: {est_time_sec:.1f} s | "
            f"Recoveries: {feedback.number_of_recoveries}"
        )

        def clear_local_costmap_callback(self):
            if not self.clear_local_costmap_client.service_is_ready():
                return

        request = ClearEntireCostmap.Request()
        future = self.clear_local_costmap_client.call_async(request)

        future.add_done_callback(self.clear_costmap_done_callback)

    def clear_costmap_done_callback(self, future):
        try:
            future.result()
            self.get_logger().debug("Local costmap cleared")
        except Exception as e:
            self.get_logger().warn(f"Failed to clear local costmap: {e}")


def main(args=None):
    rclpy.init(args=args)
    node = MoveActionClient()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Interrupted by user")
    rclpy.shutdown()


if __name__ == "__main__":
    main()
