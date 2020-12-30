import asyncio
import http
import json
import os
import sys
import time
import subprocess
import websockets

import tipa

def check_model(rm_hostname, rm_user="root"):
    try:
        command = f"ssh -o ConnectTimeout=2 {rm_user}@{rm_hostname} cat /proc/device-tree/model"
        model = subprocess.run(command, shell=True, check=True, capture_output=True)
        return model.stdout[:14].decode("utf-8")
    except subprocess.CalledProcessError:
        print(f"Error: Can't connect to reMarkable tablet on hostname : {rm_hostname}")
        os._exit(1)


#########################################################################
# Ground truth collection
#########################################################################
async def screenshotter(rm_model):
    filepath_old = None
    while True:
        ts = int(round(time.time()*10**3) ) #% 10**7)
        filepath = f'./images/bg_{ts}.png'
        try:
            if rm_model == "reMarkable 1.0":
                # TODO: the command for screenshotting on a rm1 should be much easier than for rm2:
                # basically just take a look at /dev/fb0?
                raise NotImplementedError
            elif rm_model == "reMarkable 2.0":
                command = f'''
                    ssh remarkable './screenshot.arm /proc/$(pidof xochitl)/mem' 2&> /dev/null
                    scp -q remarkable:/home/root/image.png {filepath}
                    convert {filepath} -gaussian-blur 3x0.45 -channel RGBA {filepath}
                    cp {filepath} ./images/bg.png
                    '''
            proc = await asyncio.create_subprocess_shell(command) 
            await proc.wait()
            diff = await(diff_detector(filepath, filepath_old))
            if  diff > 0:
                print(f'A change of {diff} pixels in the framebuffer, pushing new bg_image {filepath}')
                websockets_push_event(bg_wss, json.dumps((ts, filepath)))
                filepath_old = filepath
            else:
                os.remove(filepath)
            await asyncio.sleep(1.5)
        except:
            await asyncio.sleep(0.25)

async def diff_detector(f1,f2):
    if f2 is None:
        return 1878*1404
    command = f"compare -metric AE {f1} {f2} /dev/null"
    compare = await asyncio.create_subprocess_shell(command, stderr=asyncio.subprocess.PIPE)
    return int((await compare.communicate())[1])


#########################################################################
# Input Handling 
#########################################################################
packagelist = []
async def input_grabber(rm_host='remarkable', rm_model="reMarkable 2.0", rm_user="root", skip_events=4):
    i = 0
    try:
        async for package in tipa.get_canvas_input(rm_host, rm_model):
            i = (i+1) % skip_events
            if i == 0:
                packagelist.append(package) 
    except:
        print('TODO: ssh neustarten')


async def input_sender(interval=0.033): #roughly 25Hz refresh rate
    while True:
        await asyncio.sleep(interval)
        if len(packagelist) > 0:
            #print(f'send input event package of length {len(packagelist)}')
            websockets_push_event(inp_wss, json.dumps((packagelist)))
            packagelist.clear()


#########################################################################
# Websocket connection handling
#########################################################################
bg_wss = set()
inp_wss = set()
def websocket_handler(ws, path):
    if path == "/websocketBackground":
        bg_wss.add(ws)
    if path == "/websocketInput":
        inp_wss.add(ws)
    return ws.recv() # whackyhacky 


def websockets_push_event(wss, data):
    async def send(wss, ws, data):
        try:
            await ws.send(data)
        except websockets.exceptions.ConnectionClosed:
            print(f"disconnected {ws}")
            wss.remove(ws)

    for ws in wss:
        asyncio.create_task(send(wss, ws, data))


#########################################################################
# HTTP handling
#########################################################################
async def http_handler(path, request):
    # only serve index file and images or defer to websocket handler.
    path = os.path.normpath(path).lstrip("/") #TODO: FIX
    if path == "websocketInput":
        return None
    elif path == ("websocketBackground"):
        return None
    elif path.startswith("images/"):
        return get_file(path, 'image/png')
    elif path != "":
        return (http.HTTPStatus.NOT_FOUND, [], "")
    return get_file("index.html", "text/html")


def get_file(path, mimetype):
    body = open(path, "rb").read()
    headers = [
        ("Content-Type", mimetype),
        ("Content-Length", str(len(body))),
        ("Connection", "close"),
    ]
    print(f'delivered {path}')
    return (http.HTTPStatus.OK, headers, body)


#########################################################################
# Main loop
#########################################################################
def run(rm_host="remarkable", host="localhost", port=7622, rm_user="root"):
    rm_model = check_model(rm_host, rm_user)

    start_server = websockets.serve(websocket_handler, host, port, ping_interval=1000, process_request=http_handler)

    print(f"Visit http://[{host}]:{port}/ if using an IPv6 address or")
    print(f"Visit http://{host}:{port}/ if using and IPv4 adsress or alias.")           #TODO: Autodetect

    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.ensure_future(input_grabber())
    asyncio.ensure_future(input_sender())
    asyncio.get_event_loop().run_until_complete(screenshotter(rm_model))
    asyncio.get_event_loop().run_forever(debug = True)


if __name__ == "__main__":
    os.makedirs('./images/', exist_ok=True)
    if len(sys.argv) == 1:
        host = None
    else:
        host = f"{sys.argv[1]}"
    run(host=host)
