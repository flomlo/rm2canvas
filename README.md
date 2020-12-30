# rm2canvas
A html canvas based screencasting server for the reMarkable (1/2) digital paper systems.
It draws live on the canvas from the remarkables touchscreen input, but also fetches ground truth via occasional screenshots from the remarkable, trying to (seamlessly) integrate these two.


### Why is it cool?
- High quality screencast, with native 1872x1404 resolution (These are unfortunately a few seconds old, bad for live presentations)!
- Instantanious updates on what is drawn/removed on the rm via the Wacom pen (30 times per second)!
- Smooth interpolation between those two!
- Low data usage: Updates are only send if there is something to update. As the event stream is rather small and the PNG backgrounds are just updated every few seconds, the whole streaming experience uses just ~20-50kb/s.

These features make it ideal for streaming a course too many students. That's why I developed it, at least.

### Usage
1) enable SSH access on your remarkable
2) If using a rm2: Place the screenshotter GO programm (see https://gist.github.com/owulveryck/4007cbf14e0028f373e4294f66c4ad07) in `/home/root/screenshot.arm` on your device. Warning: Please be aware of the risks.
If using a rm1: TODO (should be quite risk free, just read /dev/fb0?)
3) Install `imagemagick` as we both need the `convert` and the `compare` tool as well as `websockets` via pip.
4) start the server via `python3 server.py HOSTADDRESS`, where `HOSTADDRESS` could be either `localhost` or some IPv4/IPv6 address. This opens a (maybe publicly reachable!) HTTP Server on Port 7622. Be aware that the file request sanitzier was programmed at 02:53 in the morning.



### Background

#### Building upon others work:
The original idea of drawing to a html canvas with input capured from the reMarkable is @afandians idea, see https://gitlab.com/afandian/pipes-and-paper.
We modified (and hopefully improved) his code significantly, but the basic idea remains.

Furthermore, the rm2 screenshotter is due to a gist of https://gist.github.com/owulveryck (https://gist.github.com/owulveryck/4007cbf14e0028f373e4294f66c4ad07),
who himself builds upon a lot of other peoples work, see https://github.com/rien/reStream/issues/28.

Input parsing was easy thanks to the information here: https://github.com/canselcik/libremarkable/wiki/Reading-from-Wacom-I2C-Digitizer

I (flomlo) also recevied generous amounts of help of my friends
- thejonny (https://github.com/thejonny/)  (help with python/websockets/JavaScript)
- Nikolai Wüstemann (https://wuestemann.net/) (help with CSS/JavaScript/HTML)
Thank you ♥


#### Working principles
The reMarkable features a full Linux with root access. This means that we may just read the input device `/dev/input/even1` (`event0` on rm1) via 
the following command:ssh -o ConnectTimeout=2 {rm_user}@{rm_host} cat {input_device}. This information is parsed in `tipa.py` according to the rules described in the libremarkable wiki and send to the JavaScript frontend via the websocketInput. 
There the input is drawn on a html canvas (and saved in an Array together with a timestamp).

Concurrently a new screenshot is grabbed every few seconds and send (together with a timestamp `tsBg`) to the JavaScript frontend via the websocketBackground. There it triggers a transition to the newest screenshot as well as triggering the removal of all Canvas strokes older than that timestamp.


The websocket server is happy to serve as many clients as there are, the only limits are currently the bandwith (and CPU, as it is single-threaded via pythons `asyncio`).
Simultanious streaming to ~20 devices was already tested.






#### ToDo:
- enable rm1 support. Should be almost trivial, I just don't have any device to test this with.
- remove canvas strokes with a smooth transition instead of abruptly deleting them (eyecandy)
- Hunt bugs. Please report any you encounter!
- Fix rotation.

#### Planned bigger features
- detect swipes to new pages and save a backlog of pages in the html
- Make setup easier
- Switch to a "real" http server, not something made in websockets. 
- Make HTTPS support easier
