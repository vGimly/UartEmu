from state import DeviceState


def _create_device(state, identity):
    row = state.db.execute(
        """
        INSERT INTO devices(name, identity, protocol, description, created_at, updated_at)
        VALUES (?, ?, 'default', '', 't', 't')
        RETURNING id
        """,
        (identity, identity),
    ).fetchone()
    state.db.commit()
    return row[0]


def test_state_crud(tmp_path):
    state = DeviceState(str(tmp_path / "state.db"))
    device_id = _create_device(state, "state-test")

    assert state.dump(device_id) == {}

    state.write(device_id, 2, -139)
    assert state.read(device_id, 2) == -139
    assert state.dump(device_id) == {"0x02": -139}

    state.write(device_id, 2, 42)
    assert state.read(device_id, 2) == 42

    assert state.delete(device_id, 2) is True
    assert state.delete(device_id, 2) is False
    assert state.read(device_id, 2) == 0
    assert state.dump(device_id) == {}


def test_clear_state_does_not_affect_other_devices(tmp_path):
    state = DeviceState(str(tmp_path / "state.db"))
    device_a = _create_device(state, "state-a")
    device_b = _create_device(state, "state-b")

    state.write(device_a, 1, 10)
    state.write(device_b, 1, 20)

    state.clear(device_a)

    assert state.dump(device_a) == {}
    assert state.dump(device_b) == {"0x01": 20}
