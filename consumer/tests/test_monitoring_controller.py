from unittest.mock import MagicMock, patch

import pytest

from monitoring import MonitoringController


@pytest.fixture
def mock_database():
    db = MagicMock()
    db.__getitem__.return_value = MagicMock()
    return db


def test_creates_new_agent_controller_for_unseen_id(mock_database):
    controller = MonitoringController(database=mock_database)

    with patch("monitoring.AgentController") as MockAgentController:
        mock_instance = MagicMock()
        MockAgentController.return_value = mock_instance

        controller.check({"id": "AGENTE1", "status": "online"})

        MockAgentController.assert_called_once_with(mock_database["AGENTE1"])
        mock_instance.check.assert_called_once_with({"id": "AGENTE1", "status": "online"})


def test_reuses_existing_agent_controller_for_known_id(mock_database):
    controller = MonitoringController(database=mock_database)

    with patch("monitoring.AgentController") as MockAgentController:
        mock_instance = MagicMock()
        MockAgentController.return_value = mock_instance

        controller.check({"id": "AGENTE1", "status": "online"})
        controller.check({"id": "AGENTE1", "status": "offline"})

        MockAgentController.assert_called_once()
        assert mock_instance.check.call_count == 2


def test_separates_controllers_by_agent_id(mock_database):
    controller = MonitoringController(database=mock_database)

    with patch("monitoring.AgentController") as MockAgentController:
        MockAgentController.side_effect = [MagicMock(), MagicMock()]

        controller.check({"id": "AGENTE1", "status": "online"})
        controller.check({"id": "AGENTE2", "status": "online"})

        assert MockAgentController.call_count == 2
        assert "AGENTE1" in controller.controlers
        assert "AGENTE2" in controller.controlers
