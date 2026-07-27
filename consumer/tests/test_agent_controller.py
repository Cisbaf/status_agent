from unittest.mock import MagicMock

import pytest

from agent import AgentController


@pytest.fixture
def mock_collection():
    collection = MagicMock()
    # Por padrão, nenhum registro anterior encontrado
    collection.find.return_value.sort.return_value.limit.return_value = []
    return collection


def test_init_with_no_previous_records_sets_last_register_to_none(mock_collection):
    controller = AgentController(mock_collection)

    assert controller.last_register is None


def test_init_loads_last_register_when_present(mock_collection):
    existing = {"_id": "abc123", "id": "AGENTE1", "status": "online"}
    mock_collection.find.return_value.sort.return_value.limit.return_value = [existing]

    controller = AgentController(mock_collection)

    assert controller.last_register == existing


def test_register_inserts_document_and_updates_last_register(mock_collection):
    mock_collection.insert_one.return_value.inserted_id = "new-id"
    mock_collection.find_one.return_value = {"_id": "new-id", "id": "AGENTE1", "status": "online"}
    controller = AgentController(mock_collection)

    controller.register({"id": "AGENTE1", "status": "online"})

    mock_collection.insert_one.assert_called_once_with({"id": "AGENTE1", "status": "online"})
    assert controller.last_register["_id"] == "new-id"


def test_check_registers_first_document_when_no_last_register(mock_collection):
    mock_collection.insert_one.return_value.inserted_id = "new-id"
    mock_collection.find_one.return_value = {"_id": "new-id", "id": "AGENTE1", "status": "online"}
    controller = AgentController(mock_collection)

    controller.check({"id": "AGENTE1", "status": "online"})

    mock_collection.insert_one.assert_called_once()


def test_check_registers_new_document_on_status_change(mock_collection):
    existing = {"_id": "abc123", "id": "AGENTE1", "status": "online", "last_date": "x", "date_status": "y"}
    mock_collection.find.return_value.sort.return_value.limit.return_value = [existing]
    mock_collection.insert_one.return_value.inserted_id = "new-id"
    mock_collection.find_one.return_value = {"_id": "new-id", "id": "AGENTE1", "status": "offline"}
    controller = AgentController(mock_collection)

    controller.check({"id": "AGENTE1", "status": "offline", "last_date": "x2", "date_status": "y2"})

    mock_collection.insert_one.assert_called_once()


def test_check_updates_existing_document_when_non_status_field_changes(mock_collection):
    existing = {
        "_id": "abc123",
        "id": "AGENTE1",
        "status": "online",
        "extra_field": "old_value",
        "last_date": "x",
        "date_status": "y",
    }
    mock_collection.find.return_value.sort.return_value.limit.return_value = [existing]
    controller = AgentController(mock_collection)

    controller.check({
        "id": "AGENTE1",
        "status": "online",
        "extra_field": "new_value",
        "last_date": "x2",
        "date_status": "y2",
    })

    mock_collection.insert_one.assert_not_called()
    mock_collection.update_one.assert_called_once()
    args, _ = mock_collection.update_one.call_args
    assert args[0] == {"_id": "abc123"}
    assert args[1]["$set"]["extra_field"] == "new_value"


def test_check_does_nothing_when_no_changes(mock_collection):
    existing = {
        "_id": "abc123",
        "id": "AGENTE1",
        "status": "online",
        "last_date": "x",
        "date_status": "y",
    }
    mock_collection.find.return_value.sort.return_value.limit.return_value = [existing]
    controller = AgentController(mock_collection)

    controller.check({"id": "AGENTE1", "status": "online", "last_date": "x2", "date_status": "y2"})

    mock_collection.insert_one.assert_not_called()
    mock_collection.update_one.assert_not_called()


def test_get_updates_ignores_timestamp_fields(mock_collection):
    existing = {
        "_id": "abc123",
        "id": "AGENTE1",
        "status": "online",
        "last_date": "old",
        "date_status": "old",
        "date_now": "old",
    }
    mock_collection.find.return_value.sort.return_value.limit.return_value = [existing]
    controller = AgentController(mock_collection)

    changes = controller.get_updates({
        "id": "AGENTE1",
        "status": "online",
        "last_date": "new",
        "date_status": "new",
        "date_now": "new",
    })

    assert changes == {}
