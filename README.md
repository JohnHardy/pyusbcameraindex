<div align="center">

# pyusbcameraindex

Identify and select your USB cameras in Python for use with OpenCV.

 🚀🤯 Stop guessing the camera index in OpenCV! 🤯🚀

[![PyPI](https://img.shields.io/pypi/v/pyusbcameraindex?logo=python&logoColor=%23cccccc)](https://pypi.org/project/pyusbcameraindex)
![PyPI - License](https://img.shields.io/pypi/l/pyusbcameraindex)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pyusbcameraindex)

![PyPI - Downloads](https://img.shields.io/pypi/dm/pyusbcameraindex)
![GitHub repo size](https://img.shields.io/github/repo-size/JohnHardy/pyusbcameraindex)

</div>

The [pyusbcameraindex](https://github.com/JohnHardy/pyusbcameraindex) package enumerates USB video devices on *Windows* using DirectShow APIs.

Linux and Mac are not supported, but pull requests are welcome.

Usage:
```python
import cv2
from pyusbcameraindex import enumerate_usb_video_devices_windows

# List the devices.
devices = enumerate_usb_video_devices_windows()
for device in devices:
    print(f"{device.index} == {device.name} (VID: {device.vid}, PID: {device.pid}, Path: {device.path}")

# Show a frame from each.
for device in devices:
    cap = cv2.VideoCapture(device.index, cv2.CAP_DSHOW)
    ret, frame = cap.read()
    cv2.imshow(f"Device={device.name}", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
    cap.release()
cv2.destroyAllWindows()
```
