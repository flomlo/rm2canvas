import os
import subprocess
import struct
import json
import asyncio



#load max/min X from file TODO
calb_data = { # measured on my rm2
        'min_x': 0,
        'max_x': 20966 ,
        'min_y': 0,        #actually 154, but rm2 seems to use 0.
        'max_y': 15725,        
    'max_pressure': 4095
}


async def get_canvas_input(rm_host='remarkable', rm_model='reMarkable 2.0', rm_user='root'):
    if rm_model == "reMarkable 1.0":
        input_device = "/dev/input/event0"
    elif rm_model == "reMarkable 2.0":
        input_device = "/dev/input/event1"
    else:
        raise NotImplementedError(f"Unsupported reMarkable Device : {rm_model}")

    # set up connection to reMarkable touchscreen input device
    command = f'ssh -o ConnectTimeout=2 {rm_user}@{rm_host} cat {input_device}'
    ssh = await asyncio.create_subprocess_shell(command, stdout=asyncio.subprocess.PIPE)

    # continously parse input
    parser_state = None
    while ssh.returncode == None:
        buf = await ssh.stdout.read(16)
        assert len(buf) == 16
        package, parser_state = parse_input_stream(buf, parser_state)
        if package is not None:
            (s, μs, x, y, pressure, tool) = package
            #package = (ts, *trafo2canvas(*rescale(x,y)), pressure, tool)
            package = (custom_timestamp(s, μs), *rescale(x,y), pressure, tool)
            yield package 
    print("Disconnected from reMarkable.")


def parse_input_stream(buf, parser_state=None):
    if parser_state is None:
        parser_state = (0, 0, 0, -1) 
    x, y, pressure, tool = parser_state

    # Using https://github.com/canselcik/libremarkable/wiki/Reading-from-Wacom-I2C-Digitizer
    # 4 byte unsigned int for ts in s,
    # 4 byte unsigned int for ts in μs,
    # 2 byte unsigned int for type_ (in 0,1,3),
    # 2 byte unsigned int for code, 
    # 4 byte unsigned int for value.

    s, μs, typ, code, val = struct.unpack('<IIHHI', buf)

    # absolute position
    if typ == 3:
        if code == 0:
            x = val
        elif code == 1:
            y = val
        elif code == 24:
            pressure = val
    
    # tool
    if typ == 1:
        if code == 320:
            tool = 1    # pen
        elif code == 321:
            tool = 0    # rubber

    parser_state = x, y, pressure, tool

    # sync request
    if typ == 0:    # send package
        return (s, μs, *parser_state), parser_state
    else:           # just update state
        return None, parser_state


def rescale(x_raw, y_raw):
    ''' rescale x,y according to calibration data and canvas size '''
    x = int((x_raw - calb_data['min_x']) / calb_data['max_x'] * 1872)
    y = int((y_raw - calb_data['min_y']) / calb_data['max_y'] * 1404)
    return x,y

def custom_timestamp(s, μs):
    return int(s*10**3 + μs / 1000) 

async def test():
    async for event in get_canvas_input():
        print(event)

if __name__ == '__main__':
    asyncio.run(test())
