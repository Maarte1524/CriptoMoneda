from bot.utils import round_step


def test_round_step() -> None:
    assert round_step(1.23456, 0.001) == 1.234
