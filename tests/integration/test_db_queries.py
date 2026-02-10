"""Integration tests for DB query functions against a real Postgres."""

import pytest
from sqlalchemy.ext.asyncio import AsyncConnection

from doppelganger.db.queries import audit_log, characters, tts_requests, users
from doppelganger.db.types import UserRow

pytestmark = pytest.mark.integration


async def test_create_user(db_conn: AsyncConnection) -> None:
    """create_user returns a dataclass with id, discord_id, and created_at."""
    row = await users.create_user(db_conn, discord_id="111111111111111111")
    assert row.discord_id == "111111111111111111"
    assert row.id is not None
    assert row.created_at is not None
    assert row.blacklisted is False


async def test_get_user_by_discord_id_found(db_conn: AsyncConnection) -> None:
    """get_user_by_discord_id returns the user when present."""
    created = await users.create_user(db_conn, discord_id="222222222222222222")
    found = await users.get_user_by_discord_id(db_conn, "222222222222222222")
    assert found is not None
    assert found.id == created.id


async def test_get_user_by_discord_id_not_found(db_conn: AsyncConnection) -> None:
    """get_user_by_discord_id returns None for missing users."""
    result = await users.get_user_by_discord_id(db_conn, "000000000000000000")
    assert result is None


async def test_set_user_blacklisted(db_conn: AsyncConnection) -> None:
    """set_user_blacklisted toggles the blacklisted flag."""
    user = await users.create_user(db_conn, discord_id="333333333333333333")
    assert user.blacklisted is False

    updated = await users.set_user_blacklisted(db_conn, user.id, blacklisted=True)
    assert updated is not None
    assert updated.blacklisted is True

    restored = await users.set_user_blacklisted(db_conn, user.id, blacklisted=False)
    assert restored is not None
    assert restored.blacklisted is False


async def test_set_user_blacklisted_missing(db_conn: AsyncConnection) -> None:
    """set_user_blacklisted returns None for non-existent user."""
    result = await users.set_user_blacklisted(db_conn, 999999, blacklisted=True)
    assert result is None


async def test_list_users(db_conn: AsyncConnection) -> None:
    """list_users returns all users ordered by created_at DESC."""
    await users.create_user(db_conn, discord_id="444444444444444444")
    await users.create_user(db_conn, discord_id="555555555555555555")

    result = await users.list_users(db_conn)
    assert len(result) >= 2

    discord_ids = [u.discord_id for u in result]
    assert "444444444444444444" in discord_ids
    assert "555555555555555555" in discord_ids
    assert result[0].created_at >= result[-1].created_at  # Most recent first


async def test_create_character(db_conn: AsyncConnection) -> None:
    """create_character returns a dataclass with id, name, and reference_audio_path."""
    row = await characters.create_character(db_conn, "test-voice", "/voices/test-voice/reference.wav")
    assert row.name == "test-voice"
    assert row.reference_audio_path == "/voices/test-voice/reference.wav"
    assert row.id is not None
    assert row.created_at is not None


async def test_get_character_by_name_found(db_conn: AsyncConnection) -> None:
    """get_character_by_name returns the character when present."""
    created = await characters.create_character(db_conn, "findme", "/voices/findme/reference.wav")
    found = await characters.get_character_by_name(db_conn, "findme")
    assert found is not None
    assert found.id == created.id


async def test_get_character_by_name_not_found(db_conn: AsyncConnection) -> None:
    """get_character_by_name returns None for missing characters."""
    result = await characters.get_character_by_name(db_conn, "nonexistent")
    assert result is None


async def test_delete_character_success(db_conn: AsyncConnection) -> None:
    """delete_character returns True and removes the row."""
    row = await characters.create_character(db_conn, "deleteme", "/voices/deleteme/reference.wav")
    assert await characters.delete_character(db_conn, row.id) is True
    assert await characters.get_character_by_name(db_conn, "deleteme") is None


async def test_delete_character_missing(db_conn: AsyncConnection) -> None:
    """delete_character returns False for non-existent ID."""
    assert await characters.delete_character(db_conn, 999999) is False


async def test_list_characters(db_conn: AsyncConnection) -> None:
    """list_characters returns all characters ordered by name ASC."""
    await characters.create_character(db_conn, "zara", "/voices/zara/reference.wav")
    await characters.create_character(db_conn, "alpha", "/voices/alpha/reference.wav")

    result = await characters.list_characters(db_conn)
    assert len(result) >= 2

    names = [c.name for c in result]
    assert "alpha" in names
    assert "zara" in names
    assert names == sorted(names)


async def _create_test_user(db_conn: AsyncConnection, discord_id: str) -> UserRow:
    """Helper to create a user for FK references."""
    return await users.create_user(db_conn, discord_id=discord_id)


async def test_create_tts_request(db_conn: AsyncConnection) -> None:
    """create_tts_request returns a dataclass with pending status."""
    user = await _create_test_user(db_conn, "600000000000000000")
    row = await tts_requests.create_tts_request(db_conn, user.id, "test-voice", "Hello world")
    assert row.status == "pending"
    assert row.character == "test-voice"
    assert row.text == "Hello world"
    assert row.user_id == user.id
    assert row.started_at is None
    assert row.completed_at is None


async def test_update_tts_request_status(db_conn: AsyncConnection) -> None:
    """update_tts_request_status changes the status field."""
    user = await _create_test_user(db_conn, "610000000000000000")
    req = await tts_requests.create_tts_request(db_conn, user.id, "voice", "text")
    updated = await tts_requests.update_tts_request_status(db_conn, req.id, "failed")
    assert updated is not None
    assert updated.status == "failed"


async def test_update_tts_request_status_missing(db_conn: AsyncConnection) -> None:
    """update_tts_request_status returns None for non-existent ID."""
    result = await tts_requests.update_tts_request_status(db_conn, 999999, "failed")
    assert result is None


async def test_mark_tts_request_started(db_conn: AsyncConnection) -> None:
    """mark_tts_request_started sets started_at and status to processing."""
    user = await _create_test_user(db_conn, "620000000000000000")
    req = await tts_requests.create_tts_request(db_conn, user.id, "voice", "text")
    started = await tts_requests.mark_tts_request_started(db_conn, req.id)
    assert started is not None
    assert started.status == "processing"
    assert started.started_at is not None


async def test_mark_tts_request_completed(db_conn: AsyncConnection) -> None:
    """mark_tts_request_completed sets completed_at, duration_ms, and status."""
    user = await _create_test_user(db_conn, "630000000000000000")
    req = await tts_requests.create_tts_request(db_conn, user.id, "voice", "text")
    await tts_requests.mark_tts_request_started(db_conn, req.id)

    completed = await tts_requests.mark_tts_request_completed(db_conn, req.id, duration_ms=1234)
    assert completed is not None
    assert completed.status == "completed"
    assert completed.completed_at is not None
    assert completed.duration_ms == 1234


async def test_list_tts_requests_all(db_conn: AsyncConnection) -> None:
    """list_tts_requests without filter returns all requests."""
    user = await _create_test_user(db_conn, "640000000000000000")
    await tts_requests.create_tts_request(db_conn, user.id, "voice", "one")
    await tts_requests.create_tts_request(db_conn, user.id, "voice", "two")

    result = await tts_requests.list_tts_requests(db_conn)
    assert len(result) >= 2


async def test_list_tts_requests_with_status_filter(db_conn: AsyncConnection) -> None:
    """list_tts_requests with status filter returns only matching requests."""
    user = await _create_test_user(db_conn, "650000000000000000")
    req = await tts_requests.create_tts_request(db_conn, user.id, "voice", "filtered")
    await tts_requests.update_tts_request_status(db_conn, req.id, "failed")

    failed = await tts_requests.list_tts_requests(db_conn, status="failed")
    assert any(r.id == req.id for r in failed)

    pending = await tts_requests.list_tts_requests(db_conn, status="pending")
    assert all(r.id != req.id for r in pending)


async def test_get_tts_request_found(db_conn: AsyncConnection) -> None:
    """get_tts_request returns the request when present."""
    user = await _create_test_user(db_conn, "660000000000000000")
    req = await tts_requests.create_tts_request(db_conn, user.id, "voice", "text")
    found = await tts_requests.get_tts_request(db_conn, req.id)
    assert found is not None
    assert found.id == req.id


async def test_get_tts_request_not_found(db_conn: AsyncConnection) -> None:
    """get_tts_request returns None for missing ID."""
    result = await tts_requests.get_tts_request(db_conn, 999999)
    assert result is None


async def test_create_audit_entry_minimal(db_conn: AsyncConnection) -> None:
    """create_audit_entry works with just an action string."""
    row = await audit_log.create_audit_entry(db_conn, "test.action")
    assert row.action == "test.action"
    assert row.user_id is None
    assert row.details is None
    assert row.id is not None
    assert row.created_at is not None


async def test_create_audit_entry_full(db_conn: AsyncConnection) -> None:
    """create_audit_entry works with user_id and details."""
    user = await _create_test_user(db_conn, "670000000000000000")
    row = await audit_log.create_audit_entry(
        db_conn,
        "character.created",
        user_id=user.id,
        details={"name": "test-voice"},
    )
    assert row.action == "character.created"
    assert row.user_id == user.id
    assert row.details is not None


async def test_list_audit_entries(db_conn: AsyncConnection) -> None:
    """list_audit_entries respects limit and orders by created_at DESC."""
    await audit_log.create_audit_entry(db_conn, "action.first")
    await audit_log.create_audit_entry(db_conn, "action.second")
    await audit_log.create_audit_entry(db_conn, "action.third")

    result = await audit_log.list_audit_entries(db_conn, limit=2)
    assert len(result) == 2
    assert result[0].created_at >= result[1].created_at  # Most recent first
