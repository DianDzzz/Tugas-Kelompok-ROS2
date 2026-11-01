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
from std_srvs.srv import Empty
try:  # ROS 2 Lyrical and newer expose the messages in turtlesim_msgs.
    from turtlesim_msgs.msg import Pose
    from turtlesim_msgs.srv import SetPen
except ImportError:  # ROS 2 Jazzy and older ship them inside turtlesim.
    from turtlesim.msg import Pose
    from turtlesim.srv import SetPen

MEMBER_ID = 1
NEXT_MEMBER_ID = 2
NUMBERS = (1, 9)
TURN_TOPIC = '/relay/turn'
PEN_COLOR = (255, 105, 180)
PEN_WIDTH = 4
SLOT_CENTER = (2.0, 9.0)
DIGIT_WIDTH = 1.0
DIGIT_HEIGHT = 2.0

DIGIT_STROKES = {
    1: ((0.2, 0.8), (0.5, 1.0), (0.5, 0.0)),
    9: ((1.0, 0.5), (0.0, 0.5), (0.0, 1.0),
        (1.0, 1.0), (1.0, 0.0), (0.0, 0.0)),
}

POSITION_TOLERANCE = 0.03
HEADING_TOLERANCE = 0.03
LINEAR_GAIN = 3.0
ANGULAR_GAIN = 6.0
MAX_LINEAR_SPEED = 3.0
MAX_ANGULAR_SPEED = 4.0


class ArvitoNode(Node):

    def __init__(self) -> None:
        super().__init__('arvito_node')
        self.declare_parameter('autostart', True)
        self._started = False
        self._failed = False
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
        self._clear_client = self.create_client(Empty, '/clear')
        self.create_subscription(Pose, '/turtle1/pose', self._on_pose, 10)
        self.create_subscription(
            Int32MultiArray, TURN_TOPIC, self._on_turn, turn_qos,
            callback_group=MutuallyExclusiveCallbackGroup(),
        )

    def wait_for_turtlesim(self) -> None:
        for client in (self._pen_client, self._clear_client):
            while rclpy.ok() and not client.wait_for_service(timeout_sec=1.0):
                self.get_logger().info(f'Waiting for {client.srv_name}...')

    def start_relay(self) -> None:
       
        if not rclpy.ok() or self._started:
            return
        self._started = True
        if self.get_parameter('autostart').value:
            self.get_logger().info('Starting cycle 1 with token [1, 1]')
            self._turn_pub.publish(Int32MultiArray(data=[1, 1]))
        else:
            self.get_logger().info('Idle; waiting for token [1, 1]')

    async def _on_turn(self, msg: Int32MultiArray) -> None:
        if len(msg.data) != 2:
            self.get_logger().warning('Ignoring malformed token; expected [number, member]')
            return
        number, member = msg.data
        if (self._failed or member != MEMBER_ID or number not in NUMBERS
                or number in self._drawn):
            return
        if number == 9 and 1 not in self._drawn:
            self.get_logger().warning('Ignoring out-of-order token: draw 1 before 9')
            return

        self.get_logger().info(f'My turn: drawing {number} in Slot 1')
        try:
            if number == 9:
                await self._set_pen(off=1)
                await self._clear_client.call_async(Empty.Request())
                self.get_logger().info('Canvas cleared; starting cycle 2')
            await self._draw_number(number)
        except Exception as error:
            self._failed = True
            self._goal = None
            self._cmd_pub.publish(Twist())
            self.get_logger().error(f'Drawing failed; turn not passed: {error}')
            return
        self._drawn.add(number)
        self._turn_pub.publish(Int32MultiArray(data=[number + 1, NEXT_MEMBER_ID]))
        self.get_logger().info(f'Finished {number}; passed [{number + 1}, {NEXT_MEMBER_ID}]')
        if number == 9:
            self.get_logger().info('Arvito finished both turns; idle')

    async def _draw_number(self, number: int) -> None:
        left = SLOT_CENTER[0] - DIGIT_WIDTH / 2
        bottom = SLOT_CENTER[1] - DIGIT_HEIGHT / 2
        points = [(left + x * DIGIT_WIDTH, bottom + y * DIGIT_HEIGHT)
                  for x, y in DIGIT_STROKES[number]]
        await self._set_pen(off=1)
        await self._go_to(*points[0])
        await self._set_pen(off=0)
        for x, y in points[1:]:
            await self._go_to(x, y)
        await self._set_pen(off=1)

    async def _set_pen(self, off: int) -> None:
        r, g, b = PEN_COLOR
        await self._pen_client.call_async(
            SetPen.Request(r=r, g=g, b=b, width=PEN_WIDTH, off=off),
        )

    async def _go_to(self, x: float, y: float) -> None:
        self._goal = (x, y)
        self._goal_reached = Future()
        await self._goal_reached

    def _on_pose(self, pose: Pose) -> None:
        if self._goal is None or self._goal_reached is None:
            return
        dx, dy = self._goal[0] - pose.x, self._goal[1] - pose.y
        distance = hypot(dx, dy)
        twist = Twist()
        if distance < POSITION_TOLERANCE:
            self._goal = None
            self._cmd_pub.publish(twist)
            self._goal_reached.set_result(True)
            return

        
        error = atan2(dy, dx) - pose.theta
        error = atan2(sin(error), cos(error))
        twist.angular.z = max(-MAX_ANGULAR_SPEED, min(MAX_ANGULAR_SPEED, ANGULAR_GAIN * error))
        if abs(error) < HEADING_TOLERANCE:
            twist.linear.x = min(MAX_LINEAR_SPEED, LINEAR_GAIN * distance)
        self._cmd_pub.publish(twist)

    def stop(self) -> None:   
        if self._goal is not None and rclpy.ok():
            self._cmd_pub.publish(Twist())
        self._goal = None


def main(args=None) -> None:
    rclpy.init(args=args)
    node = ArvitoNode()
    try:
        node.wait_for_turtlesim()
        node.start_relay()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.stop()
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
