import pytest
from unittest.mock import patch, MagicMock
import sys

# Add the root directory to the Python path to allow for imports
# from the 'src' directory, as the main script does.
sys.path.insert(0, '.')

from market_intelligence_main import main

@patch('src.orchestrator.MarketIntelligenceOrchestrator')
def test_main_success(mock_orchestrator):
    """
    Tests the main function's success path.
    """
    # Arrange: Configure the mock orchestrator to simulate a successful run
    mock_instance = MagicMock()
    mock_instance.run_analysis.return_value = {'success': True}
    mock_orchestrator.return_value = mock_instance

    # Act & Assert: The main function should exit with code 0 for success
    with pytest.raises(SystemExit) as e:
        main()
    assert e.type == SystemExit
    assert e.value.code == 0

    # Verify that the orchestrator was initialized and run
    mock_orchestrator.assert_called_once()
    mock_instance.run_analysis.assert_called_once()

@patch('src.orchestrator.MarketIntelligenceOrchestrator')
def test_main_failure(mock_orchestrator):
    """
    Tests the main function's failure path.
    """
    # Arrange: Configure the mock orchestrator to simulate a failed run
    mock_instance = MagicMock()
    mock_instance.run_analysis.return_value = {
        'success': False,
        'errors': ['Something went wrong']
    }
    mock_orchestrator.return_value = mock_instance

    # Act & Assert: The main function should exit with code 1 for failure
    with pytest.raises(SystemExit) as e:
        main()
    assert e.type == SystemExit
    assert e.value.code == 1

    # Verify that the orchestrator was initialized and run
    mock_orchestrator.assert_called_once()
    mock_instance.run_analysis.assert_called_once()

@patch('src.orchestrator.MarketIntelligenceOrchestrator')
def test_main_critical_exception(mock_orchestrator):
    """
    Tests the main function's exception handling for critical errors.
    """
    # Arrange: Configure the mock orchestrator to raise an exception upon initialization
    mock_orchestrator.side_effect = Exception("Critical initialization failure")

    # Act & Assert: The main function should catch the exception and exit with code 1
    with pytest.raises(SystemExit) as e:
        main()
    assert e.type == SystemExit
    assert e.value.code == 1

    # Verify that initialization was attempted
    mock_orchestrator.assert_called_once()
