"""ROS 2 relay node for member 8 (Fayyazi), drawing 8 and 16."""

from math import atan2, hypot, sin, cos

from geometry_msgs.msg import Twist
import rclpy
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from rclpy.task import Future
from std_msgs.msg import Int32MultiArray
try:  # ROS 2 Lyrical and newer expose the messages in turtlesim_msgs.
    from turtlesim_msgs.msg import Pose
    from turtlesim_msgs.srv import SetPen
except ImportError:  # ROS 2 Jazzy and older ship them inside turtlesim.
    from turtlesim.msg import Pose
    from turtlesim.srv import SetPen

MEMBER_ID = 8
NUMBERS = (8, 16)
SLOT_CENTER = (5.5, 2.0)
DIGIT_WIDTH, DIGIT_HEIGHT, DIGIT_GAP = 1.0, 2.0, 0.6
DIGITS = {
    '1': ((0.2, 0.8), (0.5, 1.0), (0.5, 0.0)),
    '6': ((1, 1), (0, 0.5), (0, 0), (1, 0), (1, 0.5), (0, 0.5)),
    '8': ((0, 0), (0, 1), (1, 1), (1, 0), (0, 0), (0, 0.5), (1, 0.5)),
}


class FayyaziNode(Node):
    """Wait for member 8's turn, draw, and pass the cycle transition."""

    def __init__(self):
        super().__init__('fayyazi_node')
        self._drawn = set()
        self._failed = False
        self._goal = None
        self._goal_reached = None
        qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                         durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self._turn_pub = self.create_publisher(Int32MultiArray, '/relay/turn', qos)
        self._cmd_pub = self.create_publisher(Twist, '/turtle1/cmd_vel', 10)
        self._pen_client = self.create_client(SetPen, '/turtle1/set_pen')
        self.create_subscription(Pose, '/turtle1/pose', self._on_pose, 10)
        self.create_subscription(Int32MultiArray, '/relay/turn', self._on_turn, qos,
                                 callback_group=MutuallyExclusiveCallbackGroup())

    def wait_for_turtlesim(self):
        while rclpy.ok() and not self._pen_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Waiting for turtlesim pen service...')

    async def _on_turn(self, msg):
        if len(msg.data) != 2:
            return
        number, member = msg.data
        if self._failed or member != MEMBER_ID or number not in NUMBERS or number in self._drawn:
            return
        if number == 16 and 8 not in self._drawn:
            return
        self.get_logger().info(f'My turn: drawing {number} in Slot 8')
        try:
            await self._draw_number(number)
        except Exception as error:
            self._failed = True
            self._goal = None
            self._cmd_pub.publish(Twist())
            self.get_logger().error(f'Drawing failed; turn not passed: {error}')
            return
        self._drawn.add(number)
        if number == 8:
            self._turn_pub.publish(Int32MultiArray(data=[9, 1]))
            self.get_logger().info('Finished 8; passed cycle transition to member 1')
        else:
            self.get_logger().info('All sequences complete; turtle is idle')

    async def _draw_number(self, number):
        digits = str(number)
        total_width = len(digits) * DIGIT_WIDTH + (len(digits) - 1) * DIGIT_GAP
        left = SLOT_CENTER[0] - total_width / 2
        bottom = SLOT_CENTER[1] - DIGIT_HEIGHT / 2
        for index, digit in enumerate(digits):
            x0 = left + index * (DIGIT_WIDTH + DIGIT_GAP)
            points = [(x0 + x * DIGIT_WIDTH, bottom + y * DIGIT_HEIGHT)
                      for x, y in DIGITS[digit]]
            await self._set_pen(1)
            await self._go_to(*points[0])
            await self._set_pen(0)
            for x, y in points[1:]:
                await self._go_to(x, y)
        await self._set_pen(1)

    async def _set_pen(self, off):
        await self._pen_client.call_async(
            SetPen.Request(r=135, g=206, b=250, width=4, off=off))

    async def _go_to(self, x, y):
        self._goal = (x, y)
        self._goal_reached = Future()
        await self._goal_reached

    def _on_pose(self, pose):
        if self._goal is None or self._goal_reached is None:
            return
        dx, dy = self._goal[0] - pose.x, self._goal[1] - pose.y
        distance = hypot(dx, dy)
        twist = Twist()
        if distance < 0.03:
            self._goal = None
            self._cmd_pub.publish(twist)
            self._goal_reached.set_result(True)
            return
        error = atan2(dy, dx) - pose.theta
        error = atan2(sin(error), cos(error))
        twist.angular.z = max(-4.0, min(4.0, 6.0 * error))
        if abs(error) < 0.03:
            twist.linear.x = min(3.0, 3.0 * distance)
        self._cmd_pub.publish(twist)


def main(args=None):
    rclpy.init(args=args)
    node = FayyaziNode()
    try:
        node.wait_for_turtlesim()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if node._goal is not None and rclpy.ok():
            node._cmd_pub.publish(Twist())
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
