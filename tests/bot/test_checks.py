"""Tests for Discord bot permission checks."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from doppelganger.bot.checks import has_required_role, is_not_blacklisted


@pytest.fixture
def interaction() -> MagicMock:
    """Create a mock Discord interaction."""
    inter = MagicMock()
    role1 = MagicMock()
    role1.id = 111
    role2 = MagicMock()
    role2.id = 222
    inter.user.roles = [role1, role2]
    return inter


def _make_db_engine(user_row: dict[str, object] | None) -> MagicMock:
    """Create a mock DB engine that returns the given user row from get_user_by_discord_id."""
    engine = MagicMock()
    conn = AsyncMock()

    # conn.execute is async, returns MagicMock result so .mappings().first() is sync
    execute_result = MagicMock()
    execute_result.mappings.return_value.first.return_value = user_row
    conn.execute.return_value = execute_result

    ctx = AsyncMock()
    ctx.__aenter__.return_value = conn
    engine.connect.return_value = ctx
    return engine


class TestHasRequiredRole:
    """Tests for has_required_role check."""

    async def test_returns_true_when_no_role_configured(self, interaction: MagicMock) -> None:
        result = await has_required_role(interaction, "")
        assert result is True

    async def test_returns_true_when_user_has_role(self, interaction: MagicMock) -> None:
        result = await has_required_role(interaction, "222")
        assert result is True

    async def test_returns_false_when_user_lacks_role(self, interaction: MagicMock) -> None:
        result = await has_required_role(interaction, "999")
        assert result is False


class TestIsNotBlacklisted:
    """Tests for is_not_blacklisted check."""

    async def test_returns_true_for_unknown_user(self) -> None:
        engine = _make_db_engine(None)
        result = await is_not_blacklisted(engine, "12345")
        assert result is True

    async def test_returns_true_for_non_blacklisted_user(self) -> None:
        engine = _make_db_engine({"id": 1, "discord_id": "12345", "blacklisted": False})
        result = await is_not_blacklisted(engine, "12345")
        assert result is True

    async def test_returns_false_for_blacklisted_user(self) -> None:
        engine = _make_db_engine({"id": 1, "discord_id": "12345", "blacklisted": True})
        result = await is_not_blacklisted(engine, "12345")
        assert result is False
