"""
Enumerate USB video devices on Windows using DirectShow APIs.

Usage:
    >>> devices = enumerate_usb_video_devices_windows()
    >>> for device in devices:
    >>>     print(f"Name: {device.name}, VID: {device.vid}, PID: {device.pid})
"""

import re
import sys
import pythoncom
from collections import namedtuple
from comtypes import (
    COMMETHOD, GUID, HRESULT, IPersist, IUnknown, 
    POINTER, c_int, c_ulong, client, CLSCTX_INPROC_SERVER
)
from comtypes.persist import IPropertyBag
from ctypes.wintypes import _ULARGE_INTEGER


class ISequentialStream(IUnknown):
    """ https://learn.microsoft.com/en-us/windows/win32/api/objidl/nn-objidl-isequentialstream """
    _case_insensitive_ = True
    _iid_ = GUID('{0C733A30-2A1C-11CE-ADE5-00AA0044773D}')
    _idlflags_ = []


class IStream(ISequentialStream):
    """ https://learn.microsoft.com/en-us/windows/win32/api/objidl/nn-objidl-istream """
    _case_insensitive_ = True
    _iid_ = GUID('{0000000C-0000-0000-C000-000000000046}')
    _idlflags_ = []


class IBindCtx(IUnknown):
    """ https://learn.microsoft.com/en-us/windows/win32/api/objidl/nn-objidl-ibindctx """
    _case_insensitive_ = True
    _iid_ = GUID('{0000000E-0000-0000-C000-000000000046}')
    _idlflags_ = []


class IPersistStream(IPersist):
    """ https://learn.microsoft.com/en-us/windows/win32/api/objidl/nn-objidl-ipersiststream """
    _case_insensitive_ = True
    _iid_ = GUID('{00000109-0000-0000-C000-000000000046}')
    _idlflags_ = []


IPersistStream._methods_ = [
    COMMETHOD([], HRESULT, 'IsDirty'),
    COMMETHOD([], HRESULT, 'Load',
            (['in'], POINTER(IStream), 'pstm')),
    COMMETHOD([], HRESULT, 'Save',
            (['in'], POINTER(IStream), 'pstm'),
            (['in'], c_int, 'fClearDirty')),
    COMMETHOD([], HRESULT, 'GetSizeMax',
            (['out'], POINTER(_ULARGE_INTEGER), 'pcbSize')),
]


class IMoniker(IPersistStream):
    """ https://learn.microsoft.com/en-us/windows/win32/api/objidl/nn-objidl-imoniker """
    _case_insensitive_ = True
    _iid_ = GUID('{0000000F-0000-0000-C000-000000000046}')
    _idlflags_ = []

IMoniker._methods_ = [
    COMMETHOD([], HRESULT, 'BindToObject',
            (['in'], POINTER(IBindCtx), 'pbc'),
            (['in'], POINTER(IMoniker), 'pmkToLeft'),
            (['in'], POINTER(GUID), 'riidResult'),
            (['out'], POINTER(POINTER(IUnknown)), 'ppvResult')
            ),
    COMMETHOD([], HRESULT, 'BindToStorage',
            (['in'], POINTER(IBindCtx), 'pbc'),
            (['in'], POINTER(IMoniker), 'pmkToLeft'),
            (['in'], POINTER(GUID), 'riid'),
            (['out'], POINTER(POINTER(IUnknown)), 'ppvObj')
            )]

IMONIKER = POINTER(IMoniker)


class IEnumMoniker(IUnknown):
    """ https://learn.microsoft.com/en-us/windows/win32/api/objidl/nn-objidl-ienummoniker """
    _case_insensitive_ = True
    _iid_ = GUID('{00000102-0000-0000-C000-000000000046}')
    _idlflags_ = []

IEnumMoniker._methods_ = [
    COMMETHOD([], HRESULT, 'Next',
            (['in'], c_ulong, 'celt'),
            (['out'], POINTER(POINTER(IMoniker)), 'rgelt'),
            (['out'], POINTER(c_ulong), 'pceltFetched')),

    COMMETHOD([], HRESULT, 'Skip',
            (['in'], c_ulong, 'celt')),

    COMMETHOD([], HRESULT, 'Reset'),
    COMMETHOD([], HRESULT, 'Clone',
            (['out'], POINTER(POINTER(IMoniker)), 'ppenum'))
]


class ICreateDevEnum(IUnknown):
    """ https://learn.microsoft.com/en-us/windows/win32/api/strmif/nn-strmif-icreatedevenum """
    _case_insensitive_ = True
    _iid_ = GUID('{29840822-5B84-11D0-BD3B-00A0C911CE86}')
    _idlflags_ = []


ICreateDevEnum._methods_ = [
    COMMETHOD([], HRESULT, 'CreateClassEnumerator',
            (['in'], POINTER(GUID), 'clsidDeviceClass'),
            (['out'], POINTER(POINTER(IEnumMoniker)), 'ppEnumMoniker'),
            (['in'], c_int, 'dwFlags'))]


def get_moniker_name(moniker) -> str:
    # The name of the device.
    property_bag = moniker.BindToStorage(0, 0, IPropertyBag._iid_).QueryInterface(IPropertyBag)
    return property_bag.Read("FriendlyName", pErrorLog=None)

def get_device_path(moniker) -> str:
    # A unique string that identifies the device. (Video capture devices only.)
    property_bag = moniker.BindToStorage(0, 0, IPropertyBag._iid_).QueryInterface(IPropertyBag)
    return property_bag.Read("DevicePath", pErrorLog=None)


USBCameraDevice = namedtuple('CameraDevice', 'name vid pid index path')
""" A named tuple representing a USB camera device. """


def enumerate_usb_video_devices_windows():
    """ List all USB video devices connected to the system.

    :note: This function only supports Windows and uses the WMI library.
    :return: A list of USBCameraDevice objects representing the USB video devices.
    :raises OSError: If the current platform is not Windows.

    :usage:
    >>> usb_video_devices = enumerate_usb_video_devices()
    >>> for device in usb_video_devices:
    >>>     print(f"Name: {device.name}, VID: {device.vid}, PID: {device.pid}, Index: {device.index}")
    """
    if sys.platform != 'win32':
        raise OSError("Windows is required to enumerate USB video devices")

    # Ensure we can call the WMI functions.
    # Note: the first call will return S_OK and subsequent calls will return S_FALSE
    # if the COM library is already initialized.
    pythoncom.CoInitialize()

    # Define the GUIDs for the System Device Enumerator and the Video Input Device Category.
    CLSID_SystemDeviceEnum = GUID('{62BE5D10-60EB-11d0-BD3B-00A0C911CE86}')
    CLSID_VideoInputDeviceCategory = GUID("{860BB310-5D01-11d0-BD3B-00A0C911CE86}")

    # Create the System Device Enumerator and enumerate the video input devices.
    device_enumerator = client.CreateObject(
        CLSID_SystemDeviceEnum,
        clsctx=CLSCTX_INPROC_SERVER,
        interface=ICreateDevEnum
    )

    # Get the enumerator for the video input devices.
    moniker_enumerator  = device_enumerator.CreateClassEnumerator(CLSID_VideoInputDeviceCategory, 0)

    # Iterate over the video input devices and extract their information.
    result = []
    try:
        moniker, count = moniker_enumerator.Next(1)
    except ValueError:
        return result

    # Indexed in enumeration order (same as OpenCV).
    index = 0
    while count > 0:
        # Extract the name and path of the device.
        # https://learn.microsoft.com/en-us/windows/win32/directshow/selecting-a-capture-device
        name = get_moniker_name(moniker)
        try:
            path = get_device_path(moniker)
        except Exception:
            path = ""

        # Extract VID and PID from the path.
        match = re.search(r"vid_([0-9A-Fa-f]{4})&pid_([0-9A-Fa-f]{4})", path)
        vid = match.group(1) if match else None
        pid = match.group(2) if match else None

        # Create the camera device object and add it to the list.
        camera = USBCameraDevice(name=name, vid=vid, pid=pid, index=index, path=path)
        result.append(camera)
        moniker, count = moniker_enumerator.Next(1)
        index += 1

    return result


if __name__ == "__main__":
    devices = enumerate_usb_video_devices_windows()
    for device in devices:
        print(f"{device.index} = {device.name} (VID={device.vid}, PID={device.pid}) Path={device.path}")
