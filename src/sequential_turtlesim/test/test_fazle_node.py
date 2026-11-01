"""Check Fazle's turn handling and pen movements."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

pytest.importorskip('rclpy')
from sequential_turtlesim.fazle_node import FazleNode  # noqa: E402


def test_turns_and_digit_movements():
    node = object.__new__(FazleNode)
    node._drawn = set()
    node._failed = False
    node._turn_pub = Mock()
    node._set_pen = AsyncMock()
    node._go_to = AsyncMock()

    async def run():
        await node._on_turn(SimpleNamespace(data=[2, 2]))
        await node._on_turn(SimpleNamespace(data=[10, 2]))

    # Avoid ROS logger initialization when constructing without a running node.
    node.get_logger = Mock(return_value=Mock())
    asyncio.run(run())

    assert [list(call.args[0].data) for call in node._turn_pub.publish.call_args_list] == [
        [3, 3], [11, 3],
    ]
    assert [call.args[0] for call in node._set_pen.call_args_list] == [
        1, 0, 1, 1, 0, 1, 0, 1,
    ]
    assert all(4.0 <= call.args[0] <= 7.0 and 8.0 <= call.args[1] <= 10.0
               for call in node._go_to.call_args_list)
