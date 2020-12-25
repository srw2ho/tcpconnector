# from ctypes import create_string_buffer
import json

import logging
import msgpack
import io
# from  ctypes import *
# import umsgpack
from logging.handlers import RotatingFileHandler
from tcpconnector.tcpclient import TCPClient
from tcpconnector.tcptarget import TCPTarget
from tcpconnector.tcpclient import msgPayload
from tcpconnector.tcpclient import msgPayloadType
from tcpconnector.tcpclient import msgConnectionInfo
from tcpconnector.tcpclient import connectionInfoType


import asyncio
import os


LOGFOLDER = "./logs/"
PROJECT_NAME = 'test_client'


# configure logging
logger = logging.getLogger('root')
logger.setLevel(logging.INFO)

# create formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(formatter)
logger.addHandler(ch)

try:  
    os.mkdir(LOGFOLDER)
    logger.info(f'create logfolder: {LOGFOLDER}')
except OSError as error:  
    logger.info(f'create logfolder: {LOGFOLDER}:{error}')
# fl = logging.FileHandler('OPC-UA.log')
# Rotation file handler miit 200 000 bytes pro file und 10 files in rotation
fl = RotatingFileHandler(f'{LOGFOLDER}{PROJECT_NAME}.log',mode='a', maxBytes=2*(10**5), backupCount=10)
fl.setLevel(logging.ERROR)
fl.setFormatter(formatter)
logger.addHandler(fl)


globtcpclient = None
target = TCPTarget ("Zysterne",3005,timeout=10)


# target = TCPTarget ("192.168.1.219",3006,timeout=10)



globtcpclient = TCPClient(target)
    
def createASCIIpayload(payload):
    
    # a = c_wchar_p(payload)
    
    buf = io.BytesIO()
    cmdlen =  len (payload) 
    cmdlenheader = cmdlen.to_bytes(4, byteorder="big")
    buf.write(cmdlenheader)
    header = bytes([0x55,0x55])    
    buf.write(header)
    convertedpayload = bytes(payload, 'utf-8')
    # convertedpayload = bytes(a.value, 'utf-8')
    buf.write(convertedpayload)
    return buf.getvalue()


def msgpackdeserialize(payload):
    try:
        
        # return umsgpack.Unpacker(payload._payload)
        return msgpack.unpackb(payload._payload,encoding="utf-8", raw=False)
        # return msgpack.unpackb(payload._payload)
    
    except Exception as exception:
        logger.error(f'msgpackdeserialize Error: {exception}')
        logger.info(f'msgpackdeserialize Error: {exception}')
        # print(exception)
        return {}
        
def doSolar(payload):
    return 

def domsgPackSolar(data):
    # return msgpack.unpackb(data._payload)
    return msgpackdeserialize(data)

def doJsonPackSolar(data):
    decodeddata = data._payload.decode("utf-8") 
    return json.loads(data._payload)

     
        
async def readinqueue(in_queue): 
    
    while True:
        try:
            data = await in_queue.get()
            if data._msgPayloadType == msgPayloadType.ASCIISOLAR:
                doSolar(data)
            if data._msgPayloadType == msgPayloadType.MSGPACKSOLAR:
                package = domsgPackSolar(data)
                print (package)
            if data._msgPayloadType == msgPayloadType.JSONSOLAR:
                package = doJsonPackSolar(data)
                print (package)


            await asyncio.sleep(0.1)
        except Exception as ex:
            logger.error(f'readinqueue error:{ex}')
            logger.info(f'readinqueue error:{ex}')

async def connected(connectioninfo): 
    try:
        if (connectioninfo._connectionInfoType == connectionInfoType.CONNECTED) or (connectioninfo._connectionInfoType == connectionInfoType.CHECKCONNECTION):
      
            # if (connectioninfo._target.host !="Zysterne"): return
            
            test_string='GPIOServiceClient.Start' 
        #     unicoderes = test_string.encode('unicode-escape')
        
 
   
            xmd = createASCIIpayload(test_string)
            await connectioninfo._TCPClient.writesenddata(xmd)
        
    except Exception as ex:
        logger.error(f'connected:{ex}')
        logger.info(f'connected:{ex}') 
        # await globtcpclient.writesenddata(None)

    return


async def receivedata(in_queue): 
    while True:
        data = await in_queue.get()
        print (f'{data}')
        if globtcpclient!=None:
            await globtcpclient.writesenddata(data)
        await asyncio.sleep(0.1)



async def test_TCPConnectin(in_queue, out_queue):
 
    
    loop = asyncio.get_event_loop()
        
    
    # handle_in_task = asyncio.create_task(receivedata(in_queue))
     
    await globtcpclient.connect(on_reciveEvent_batch=readinqueue, on_connect_event= connected)
    
    logger.error(f'test_TCPConnectin:close by user')    

    



async def multiple_tasks(dummy):
    out_queue = asyncio.Queue()
    in_queue = asyncio.Queue()
    target = TCPTarget ("192.168.1.23",3006,timeout=10)

    globtcpclient = TCPClient(target)
 
    
    input_coroutines = [globtcpclient.connect(on_reciveEvent_batch=readinqueue)]
    res = await asyncio.gather(*input_coroutines, return_exceptions=True)
    return res
    
def  main():
    out_queue = asyncio.Queue()
    in_queue = asyncio.Queue()
    loop = asyncio.get_event_loop()

    loop.run_until_complete(test_TCPConnectin(in_queue,out_queue))
    # loop.run_until_complete(client.close())
    loop.stop()


if  __name__ == '__main__':
    main()
    # unittest.main()

