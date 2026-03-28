# Copyright 2016 Open Source Robotics Foundation, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import String
import time


class MinimalPublisher(Node):
    def __init__(self):
        # ros2 topic pub --once /turtle1/cmd_vel geometry_msgs/ms/Twist ""

        #
        # go straight
        # ros2 topic pub --once /turtle1/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 2.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
        # ros2 topic pub --once /turtle1/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 2.828, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
        #
        #
        # turn 45 degrees left
        # ros2 topic pub --once /turtle1/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: pi/2}}"
        #
        #
        # turn 45 degrees right
        # ros2 topic pub --once /turtle1/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: -pi/2}}"
        #
        # go straight -> turn 2x 45 deg left -> go straight ->  turn 3x45 deg left -> go straight
        # -> 45 deg right -> go straight -> 45 deg right -> go straight -> 2x45 deg right -> go straight -> 45 deg right -> go straight -> 45 deg left
        # -> go straight

        self.diag = math.sqrt(2)
        self.pi = math.pi
        super().__init__("minimal_publisher")
        self.publisher_ = self.create_publisher(Twist, "turtle1/cmd_vel", 10)
        timer_period = 1.0  # seconds
        self.timer = self.create_timer(timer_period, self.timer_callback)
        self.timer_callback

    def timer_callback(self):
        turn = self.pi / 4.0
        turn2 = turn * -1.0

        msgStraight = Twist()
        msgStraight.linear.x = 1.0

        msgDiag = Twist()
        msgDiag.linear.x = math.sqrt(2.0)

        msgTurn = Twist()
        msgTurn.angular.z = turn

        msgTurnR = Twist()
        msgTurnR.angular.z = turn2

        msgDiagD = Twist()
        msgDiagD.linear.x = math.sqrt(1.0)

        # 1
        self.publisher_.publish(msgStraight)
        time.sleep(2.0)

        self.publisher_.publish(msgTurn)
        time.sleep(1.0)
        self.publisher_.publish(msgTurn)
        time.sleep(1.0)

        # 2
        self.publisher_.publish(msgStraight)
        time.sleep(2.0)

        self.publisher_.publish(msgTurn)
        time.sleep(1.0)
        self.publisher_.publish(msgTurn)
        time.sleep(1.0)
        self.publisher_.publish(msgTurn)
        time.sleep(1.0)

        # 3
        self.publisher_.publish(msgDiag)
        time.sleep(math.sqrt(8.0))
        self.publisher_.publish(msgTurnR)
        time.sleep(1.0)
        self.publisher_.publish(msgTurnR)
        time.sleep(1.0)
        self.publisher_.publish(msgTurnR)
        time.sleep(1.0)

        # 4
        self.publisher_.publish(msgStraight)
        time.sleep(2.0)
        self.publisher_.publish(msgTurnR)
        time.sleep(1.0)

        # 5
        self.publisher_.publish(msgDiagD)
        time.sleep(math.sqrt(0.5))
        self.publisher_.publish(msgTurnR)
        time.sleep(1.0)
        self.publisher_.publish(msgTurnR)
        time.sleep(1.0)

        # 6
        self.publisher_.publish(msgDiagD)
        time.sleep(math.sqrt(0.5))
        self.publisher_.publish(msgTurnR)
        time.sleep(1.0)
        self.publisher_.publish(msgTurnR)
        time.sleep(1.0)
        self.publisher_.publish(msgTurnR)
        time.sleep(1.0)

        # 7
        self.publisher_.publish(msgStraight)
        time.sleep(2.0)
        self.publisher_.publish(msgTurn)
        time.sleep(1.0)
        self.publisher_.publish(msgTurn)
        time.sleep(1.0)
        self.publisher_.publish(msgTurn)
        time.sleep(1.0)

        # 8
        self.publisher_.publish(msgDiag)
        time.sleep(1.0)
        self.publisher_.publish(msgTurn)
        time.sleep(1.0)
        self.publisher_.publish(msgTurn)
        time.sleep(1.0)
        self.publisher_.publish(msgTurn)
        time.sleep(1.0)

        # 9
        self.publisher_.publish(msgStraight)
        self.publisher_.publish(msgTurn)
        time.sleep(1.0)
        self.publisher_.publish(msgTurn)
        time.sleep(1.0)
        self.publisher_.publish(msgTurn)
        time.sleep(1.0)
        self.publisher_.publish(msgTurn)
        time.sleep(1.0)
        time.sleep(math.sqrt(8.0))

        self.get_logger().info('Publishing: "straight"')


def main(args=None):
    rclpy.init(args=args)

    minimal_publisher = MinimalPublisher()

    rclpy.spin(minimal_publisher)

    # Destroy the node explicitly
    # (optional - otherwise it will be done automatically
    # when the garbage collector destroys the node object)
    minimal_publisher.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
