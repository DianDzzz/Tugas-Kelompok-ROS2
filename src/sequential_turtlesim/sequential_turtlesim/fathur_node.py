"""Relay node for member 7 (Fathur): draws 7 and 15 in Slot 7."""

from math import atan2, cos, hypot, sin
from typing import Optional, Set, Tuple

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

MEMBER_ID = 7
NEXT_MEMBER_ID = 8
NUMBERS = (7, 15)

# Turn token layout: data = [current_number, active_member].
TURN_TOPIC = '/relay/turn'

PEN_COLOR = (255, 0, 0)
PEN_WIDTH = 4

SLOT_CENTER = (2.0, 2.0)
DIGIT_WIDTH = 1.0
DIGIT_HEIGHT = 2.0
DIGIT_GAP = 0.6

# One polyline per digit, in (0..1, 0..1) cell coordinates from bottom-left.
DIGIT_STROKES = {
    '1': ((0.2, 0.8), (0.5, 1.0), (0.5, 0.0)),
    '5': ((1.0, 1.0), (0.0, 1.0), (0.0, 0.5), (1.0, 0.5), (1.0, 0.0), (0.0, 0.0)),
    '7': ((0.0, 1.0), (1.0, 1.0), (0.3, 0.0)),
}

POSITION_TOLERANCE = 0.03
HEADING_TOLERANCE = 0.03
LINEAR_GAIN = 3.0
ANGULAR_GAIN = 6.0
MAX_LINEAR_SPEED = 3.0
MAX_ANGULAR_SPEED = 4.0


class FathurNode(Node):
    """Stay idle until the turn token arrives, draw, then pass the token on."""

    def __init__(self) -> None:
        super().__init__('fathur_node')
        self._drawn: Set[int] = set()
        self._goal: Optional[Tuple[float, float]] = None
        self._goal_reached: Optional[Future] = None

        turn_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self._turn_pub = self.create_publisher(Int32MultiArray, TURN_TOPIC, turn_qos)
        self._cmd_pub = self.create_publisher(Twist, '/turtle1/cmd_vel', 10)
        self._pen_client = self.create_client(SetPen, '/turtle1/set_pen')
        self.create_subscription(Pose, '/turtle1/pose', self._on_pose, 10)
        # An async callback holds its group until it returns, so the turn
        # subscription must not share a group with the pose and pen callbacks.
        self.create_subscription(
            Int32MultiArray, TURN_TOPIC, self._on_turn, turn_qos,
            callback_group=MutuallyExclusiveCallbackGroup(),
        )

    def wait_for_turtlesim(self) -> None:
        """Block until the turtlesim pen service is available."""
        while not self._pen_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Waiting for turtlesim...')
        self.get_logger().info('Idle, waiting for my turn')

    async def _on_turn(self, msg: Int32MultiArray) -> None:
        number, member = msg.data
        if member != MEMBER_ID or number not in NUMBERS or number in self._drawn:
            return
        self._drawn.add(number)
        self.get_logger().info(f'My turn: drawing {number}')
        await self._draw_number(number)
        self._turn_pub.publish(Int32MultiArray(data=[number + 1, NEXT_MEMBER_ID]))
        self.get_logger().info(f'Done, passing turn to member {NEXT_MEMBER_ID}')

    async def _draw_number(self, number: int) -> None:
        digits = str(number)
        total_width = len(digits) * DIGIT_WIDTH + (len(digits) - 1) * DIGIT_GAP
        left = SLOT_CENTER[0] - total_width / 2
        bottom = SLOT_CENTER[1] - DIGIT_HEIGHT / 2

        for index, digit in enumerate(digits):
            digit_left = left + index * (DIGIT_WIDTH + DIGIT_GAP)
            points = [
                (digit_left + u * DIGIT_WIDTH, bottom + v * DIGIT_HEIGHT)
                for u, v in DIGIT_STROKES[digit]
            ]
            await self._set_pen(off=1)
            await self._go_to(*points[0])
            await self._set_pen(off=0)
            for x, y in points[1:]:
                await self._go_to(x, y)
        await self._set_pen(off=1)

    async def _set_pen(self, off: int) -> None:
        r, g, b = PEN_COLOR
        request = SetPen.Request(r=r, g=g, b=b, width=PEN_WIDTH, off=off)
        await self._pen_client.call_async(request)

    async def _go_to(self, x: float, y: float) -> None:
        self._goal = (x, y)
        self._goal_reached = Future()
        await self._goal_reached

    def _on_pose(self, pose: Pose) -> None:
        if self._goal is None or self._goal_reached is None:
            return

        dx = self._goal[0] - pose.x
        dy = self._goal[1] - pose.y
        distance = hypot(dx, dy)
        twist = Twist()

        if distance < POSITION_TOLERANCE:
            self._goal = None
            self._cmd_pub.publish(twist)
            self._goal_reached.set_result(True)
            return

        # Turn on the spot first so that every stroke stays a straight line.
        error = atan2(dy, dx) - pose.theta
        error = atan2(sin(error), cos(error))
        angular = ANGULAR_GAIN * error
        twist.angular.z = max(-MAX_ANGULAR_SPEED, min(MAX_ANGULAR_SPEED, angular))
        if abs(error) < HEADING_TOLERANCE:
            twist.linear.x = min(LINEAR_GAIN * distance, MAX_LINEAR_SPEED)
        self._cmd_pub.publish(twist)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = FathurNode()
    try:
        node.wait_for_turtlesim()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
