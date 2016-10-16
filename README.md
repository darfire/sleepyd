# sleepyd, a sleepd replacement

**sleepyd** is a replacement for sleepd which is not maintained and is missing from the Ubuntu repositories.

It listens to mouse and keyboard events. Optionally, it can check whether established connections to certain local ports (think SSH) exist, in which case it doesn't sleep.

Example configuration file
```
[main]

reload_interval = 30
suspend_interval = 30
suspend_command = pm-suspend
tcp_ports = 22
```
