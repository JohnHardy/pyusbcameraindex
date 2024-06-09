import pytest
import sys
from unittest.mock import MagicMock, patch

from pyusbcameraindex import directshow

@pytest.fixture
def mock_pythoncom(mocker):
    mocker.patch("pyusbcameraindex.directshow.pythoncom.CoInitialize")

@pytest.fixture
def mock_client(mocker):
    mock_client = mocker.patch("pyusbcameraindex.directshow.client.CreateObject")
    return mock_client

@pytest.fixture
def mock_enumerator(mocker):
    mock_enumerator = MagicMock()
    mocker.patch("pyusbcameraindex.directshow.get_moniker_name", return_value="Mock Camera")
    mocker.patch("pyusbcameraindex.directshow.get_device_path", return_value="MockPath\\vid_1234&pid_5678")
    return mock_enumerator

def test_enumerate_usb_video_devices_windows_non_windows():
    """ An OSError is raised if the platform is not Windows. """
    original_platform = sys.platform
    sys.platform = "linux"
    with pytest.raises(OSError):
        directshow.enumerate_usb_video_devices_windows()
    sys.platform = original_platform

def test_enumerate_usb_video_devices_windows_no_devices(mock_pythoncom, mock_client):
    """ An empty list is returned if there are no camera devices attached. """
    sys.platform = "win32"
    mock_client().CreateClassEnumerator().Next.side_effect = ValueError
    devices = directshow.enumerate_usb_video_devices_windows()
    assert devices == []

def test_enumerate_usb_video_devices_windows_with_devices(mock_pythoncom, mock_client, mock_enumerator):
    """ A single camera device is enumerated and returned. """
    sys.platform = "win32"
    mock_moniker = MagicMock()
    
    # Mock the Next method to return the mock_moniker once and then indicate no more monikers
    mock_enumerator.Next.side_effect = [(mock_moniker, 1), (None, 0)]
    mock_client().CreateClassEnumerator.return_value = mock_enumerator

    devices = directshow.enumerate_usb_video_devices_windows()
    assert len(devices) == 1
    assert devices[0].name == "Mock Camera"
    assert devices[0].vid == "1234"
    assert devices[0].pid == "5678"
    assert devices[0].index == 0
    assert devices[0].path == "MockPath\\vid_1234&pid_5678"


def test_enumerate_usb_video_devices_windows_with_two_devices():
    """ Two camera devices are enumerated and returned. """
    with patch("pyusbcameraindex.directshow.pythoncom.CoInitialize"), \
         patch("pyusbcameraindex.directshow.client.CreateObject") as mock_client, \
         patch("pyusbcameraindex.directshow.get_moniker_name") as mock_get_moniker_name, \
         patch("pyusbcameraindex.directshow.get_device_path") as mock_get_device_path:
        
        sys.platform = "win32"
        mock_moniker1 = MagicMock()
        mock_moniker2 = MagicMock()
        
        # Mock the Next method to return the two mock monikers sequentially and then indicate no more monikers
        mock_enumerator = MagicMock()
        mock_enumerator.Next.side_effect = [(mock_moniker1, 1), (mock_moniker2, 1), (None, 0)]
        mock_client().CreateClassEnumerator.return_value = mock_enumerator
        
        mock_get_moniker_name.side_effect = ["Mock Camera 1", "Mock Camera 2"]
        mock_get_device_path.side_effect = [
            "MockPath\\vid_1234&pid_5678",
            "MockPath\\vid_8765&pid_4321"
        ]

        devices = directshow.enumerate_usb_video_devices_windows()
        assert len(devices) == 2

        # Check the details of the first device
        assert devices[0].name == "Mock Camera 1"
        assert devices[0].vid == "1234"
        assert devices[0].pid == "5678"
        assert devices[0].index == 0
        assert devices[0].path == "MockPath\\vid_1234&pid_5678"

        # Check the details of the second device
        assert devices[1].name == "Mock Camera 2"
        assert devices[1].vid == "8765"
        assert devices[1].pid == "4321"
        assert devices[1].index == 1
        assert devices[1].path == "MockPath\\vid_8765&pid_4321"
