#!/usr/bin/env python3
import math
import time
from typing import List, Optional, Tuple

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.action import ActionClient

from sensor_msgs.msg import Image, CameraInfo
from tams_lasertag_client.srv import SubmitHit
from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import PoseStamped

# AprilTag messages (may exist depending on your setup)
try:
    from apriltag_msgs.msg import AprilTagDetectionArray
except Exception:
    AprilTagDetectionArray = None  # type: ignore


class LaserTagStrats(Node):
    """
    Strategy node:
      - Subscribe to image + camera_info
      - Subscribe to AprilTag detections (auto-discover common topics)
      - When a tag is detected: submit latest image via SubmitHit (rate-limited)
      - Run a waypoint/circle patrol using Nav2 NavigateToPose (async, non-blocking)
    """

    # ----------- CONFIG YOU MAY EDIT -----------
    IMAGE_TOPIC = "/oakd/rgb/preview/image_raw"
    CAMINFO_TOPIC = "/oakd/rgb/preview/camera_info"

    # Common apriltag detection topics (we will try these automatically)
    APRILTAG_TOPIC_CANDIDATES = [
        "/apriltag/detections",
        "/tag_detections",
        "/apriltag/tag_detections",
        "/detections",
        "/fiducial_detections",
    ]

    SUBMIT_SERVICE = "submit_hit"
    NAV_ACTION = "/navigate_to_pose"

    # Rate limit for submitting hits (seconds)
    SUBMIT_COOLDOWN_SEC = 10.0

    # How long to wait after starting for camera_info/image to arrive
    STARTUP_GRACE_SEC = 2.0

    # Patrol points (map frame)
    START_POSE = (-0.359, 5.95, 0.00247)
    WAYPOINTS: List[Tuple[float, float, float]] = [
        (2.95, 6.29, 0.00247),
        (1.99, 4.18, 0.00247),
        (-6.70, 7.40, 0.00247),
        (1.07, -0.494, 0.00247),
        (-0.359, 5.95, 0.00247),
    ]
    # Circle checks (center_x, center_y, radius, points)
    CIRCLES: List[Tuple[float, float, float, int]] = [
        (-6.70, 7.40, 1.0, 10),
        (1.07, -0.494, 1.0, 10),
    ]
    # ------------------------------------------

    def __init__(self):
        super().__init__("lasertag_strats")

        # Perception state
        self.camera_info: Optional[CameraInfo] = None
        self.latest_image: Optional[Image] = None
        self.last_submit_time: float = 0.0
        self.pending_submit: bool = False
        self.last_tag_seen_time: float = 0.0

        self.start_time = time.time()

        # Subscribers
        self.create_subscription(
            Image, self.IMAGE_TOPIC, self.image_callback, qos_profile_sensor_data
        )
        self.create_subscription(
            CameraInfo,
            self.CAMINFO_TOPIC,
            self.camera_info_callback,
            qos_profile_sensor_data,
        )

        # Auto-discover apriltag detection topic
        self.detection_topic: Optional[str] = None
        self.detection_sub = None
        self._try_setup_detection_subscription()

        # Service client
        self.client = self.create_client(SubmitHit, self.SUBMIT_SERVICE)
        self.get_logger().info(f"Waiting for service '{self.SUBMIT_SERVICE}'...")
        while not self.client.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn(
                f"Service '{self.SUBMIT_SERVICE}' not available yet, waiting..."
            )
        self.get_logger().info("SubmitHit service is available.")

        # Nav2 Action
        self.nav_client = ActionClient(self, NavigateToPose, self.NAV_ACTION)
        self.get_logger().info(f"Waiting for Nav2 action '{self.NAV_ACTION}'...")
        self.nav_client.wait_for_server()
        self.get_logger().info("Nav2 action server ready.")

        # Patrol state machine
        self.state = "IDLE"
        self.queue: List[Tuple[float, float, float]] = []
        self.active_goal = None
        self.goal_in_flight = False
        self.cycle = 0

        # Timers (non-blocking)
        self.create_timer(0.2, self.tick_patrol)  # navigation state machine tick
        self.create_timer(0.1, self.tick_submit)  # service submit tick
        self.create_timer(2.0, self.tick_discovery)  # retry detection topic discovery

        self.get_logger().info("LaserTag strategy node started.")

    # -------------------- Discovery --------------------
    def tick_discovery(self):
        # if already have detection_sub, nothing to do
        if self.detection_sub is not None:
            return
        self._try_setup_detection_subscription()

    def _try_setup_detection_subscription(self):
        if AprilTagDetectionArray is None:
            self.get_logger().warn(
                "apriltag_msgs not available in Python env. Cannot subscribe to detections."
            )
            return

        topics = dict(self.get_topic_names_and_types())
        for cand in self.APRILTAG_TOPIC_CANDIDATES:
            if cand in topics:
                # Ensure type matches expected
                types = topics[cand]
                if any("apriltag_msgs/msg/AprilTagDetectionArray" in t for t in types):
                    self.detection_topic = cand
                    self.detection_sub = self.create_subscription(
                        AprilTagDetectionArray,
                        cand,
                        self.detections_callback,
                        qos_profile_sensor_data,
                    )
                    self.get_logger().info(f"Subscribed to AprilTag detections: {cand}")
                    return

        # If not found, log occasionally (not spam)
        self.get_logger().warn(
            "No AprilTag detection topic found yet. "
            "Make sure apriltag detector launch is running."
        )

    # -------------------- Callbacks --------------------
    def camera_info_callback(self, msg: CameraInfo):
        self.camera_info = msg

    def image_callback(self, msg: Image):
        self.latest_image = msg

    def detections_callback(self, msg):
        # msg is AprilTagDetectionArray
        if not getattr(msg, "detections", None):
            return

        self.last_tag_seen_time = time.time()

        # mark a submit request (actual service call is done in tick_submit)
        self.pending_submit = True

    # -------------------- Submit logic --------------------
    def tick_submit(self):
        # Need image + camera_info
        if self.latest_image is None or self.camera_info is None:
            return

        # Give system a moment to warm up
        if time.time() - self.start_time < self.STARTUP_GRACE_SEC:
            return

        # Only submit when we recently saw a tag
        if not self.pending_submit:
            return

        # Rate limit
        now = time.time()
        if now - self.last_submit_time < self.SUBMIT_COOLDOWN_SEC:
            return

        # Submit
        self.pending_submit = False
        self.last_submit_time = now

        req = SubmitHit.Request()
        req.image = self.latest_image
        req.camera_info = self.camera_info

        self.get_logger().info("🎯 Tag detected -> submitting image (SubmitHit)")
        future = self.client.call_async(req)
        future.add_done_callback(self._on_submit_done)

    def _on_submit_done(self, future):
        try:
            resp = future.result()
            # resp content depends on srv definition; print safely
            self.get_logger().info(f"✅ SubmitHit response: {resp}")
        except Exception as e:
            self.get_logger().error(f"❌ SubmitHit failed: {e}")

    # -------------------- Navigation helpers --------------------
    def _pose_goal(self, x: float, y: float, yaw: float) -> NavigateToPose.Goal:
        goal = NavigateToPose.Goal()
        goal.pose = PoseStamped()
        goal.pose.header.frame_id = "map"
        goal.pose.header.stamp = self.get_clock().now().to_msg()
        goal.pose.pose.position.x = float(x)
        goal.pose.pose.position.y = float(y)
        # planar yaw -> quaternion z/w
        goal.pose.pose.orientation.z = math.sin(yaw / 2.0)
        goal.pose.pose.orientation.w = math.cos(yaw / 2.0)
        return goal

    def _enqueue_circle(self, cx: float, cy: float, radius: float, points: int):
        for i in range(points):
            ang = 2.0 * math.pi * i / float(points)
            x = cx + radius * math.cos(ang)
            y = cy + radius * math.sin(ang)
            yaw = ang + math.pi / 2.0
            self.queue.append((x, y, yaw))

    def _build_patrol_queue(self):
        self.queue.clear()
        # Start pose
        self.queue.append(self.START_POSE)

        # Waypoints + circles after specific rooms
        # We will insert circle after reaching the matching waypoint center
        for wp in self.WAYPOINTS:
            self.queue.append(wp)
            # If this wp matches a circle center, enqueue a circle
            for cx, cy, r, n in self.CIRCLES:
                if abs(wp[0] - cx) < 1e-3 and abs(wp[1] - cy) < 1e-3:
                    self._enqueue_circle(cx, cy, r, n)

    # -------------------- Patrol state machine (non-blocking) --------------------
    def tick_patrol(self):
        # If we haven't built the queue yet, do it
        if self.state == "IDLE":
            self.cycle += 1
            self.get_logger().info(f"🚀 Starting patrol cycle {self.cycle}")
            self._build_patrol_queue()
            self.state = "RUNNING"

        if self.state != "RUNNING":
            return

        # If goal in flight, do nothing (wait for result callback)
        if self.goal_in_flight:
            return

        # No more goals => restart
        if not self.queue:
            self.get_logger().info(f"✅ Patrol cycle {self.cycle} complete.")
            self.state = "IDLE"
            return

        # Send next goal
        x, y, yaw = self.queue.pop(0)
        goal = self._pose_goal(x, y, yaw)
        self.get_logger().info(f"🧭 Nav goal -> ({x:.2f}, {y:.2f}, yaw={yaw:.2f})")

        send_future = self.nav_client.send_goal_async(goal)
        self.goal_in_flight = True
        send_future.add_done_callback(self._on_goal_response)

    def _on_goal_response(self, future):
        try:
            goal_handle = future.result()
        except Exception as e:
            self.get_logger().error(f"❌ Failed to send goal: {e}")
            self.goal_in_flight = False
            return

        if not goal_handle.accepted:
            self.get_logger().warn("⚠️ Nav goal rejected.")
            self.goal_in_flight = False
            return

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self._on_goal_result)

    def _on_goal_result(self, future):
        try:
            _ = future.result()
            # You can inspect result.status if needed
            self.get_logger().info("✅ Reached nav goal.")
        except Exception as e:
            self.get_logger().warn(f"⚠️ Nav goal result error: {e}")
        finally:
            self.goal_in_flight = False


def main():
    rclpy.init()
    node = LaserTagStrats()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
