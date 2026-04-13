from __future__ import annotations

import unittest
from unittest.mock import patch

import varsity_tools


class VarsityToolsTradeOpenTest(unittest.TestCase):
    def test_trade_open_uses_quantity_field(self) -> None:
        with patch.object(varsity_tools, "_post", return_value={"code": 0, "data": {"ok": True}}) as mock_post:
            result = varsity_tools.trade_open(
                competition_id=10,
                direction="long",
                size=0.01,
                take_profit=70000,
                stop_loss=60000,
            )

        self.assertEqual(result, {"ok": True})
        mock_post.assert_called_once_with(
            "/arena/agent/live/10/trade/open",
            {
                "direction": "long",
                "quantity": 0.01,
                "takeProfit": 70000,
                "stopLoss": 60000,
            },
        )


if __name__ == "__main__":
    unittest.main()
