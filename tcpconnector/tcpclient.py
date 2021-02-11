# import socket
import asyncio
import time
import re
import logging
import tcpconnector.tcptarget
from enum import Enum


logger = logging.getLogger('root')

class msgPayloadType(Enum):
    UNDEF = 0
    STRING = 1
    BINARY = 2
    MSGPACK= 3
    MSGPACKSOLAR= 4
    ASCIISOLAR= 5
    JSONSOLAR= 6

class connectionInfoType(Enum):
    UNDEF = 0
    CONNECTED = 1
    CHECKCONNECTION = 2
    DISCONNECTED = 3
    ERROR= 4

class msgPayload(object):

    def __init__(self, msgPayloadType,payoad,tcpClient):
        self._msgPayloadType = msgPayloadType
        self._payload = payoad
        # self._target = target
        self._TCPClient = tcpClient
    
    def getTCPClient(self):
        return  self._TCPClient

class msgConnectionInfo(object):
    
    def __init__(self, connectionInfoType,_connectioninfo,tcpClient):
        self._connectionInfoType = connectionInfoType
        self._connectioninfo = _connectioninfo
        # self._target = target
        self._TCPClient = tcpClient

        
class TCPClient(object):

    def __init__(self, _target):

        self.target = _target

        self._isconnected = False

        self.out_queue = asyncio.Queue()
        self.in_queue = asyncio.Queue()
  
        self.loop =None
        self.timeout = None
        self.handle_receive_task = None
        self.handle_send_task = None
 
       
        self.on_connect_event = None
     
        self.handle_on_reciveEvent_batch = None
        
        self._writer = None
        self._reader = None
        # self._Lock = asyncio.Lock()
        
        self._closeClient = False



    def calcualte_length(self, data):
        # len = int.from_bytes(data, byteorder = 'little', signed = False)
        len = int.from_bytes(data[0:4], byteorder = 'big', signed = False)
        return len

    async def clearReader(self):
        try:
            while not self._reader.at_eof():
                lb = await asyncio.wait_for(self._reader.read(1), 0.1)      
                if lb == b'':
                      break;
        except asyncio.TimeoutError as err:
            return
        except Exception as err:  
            raise err
        
    async def readPayload(self):
        try:
            
            lb = await asyncio.wait_for(self._reader.readexactly(4), self.target.timeout)
            if lb is None:
                logger.info('readPayload: Server timed out!')
                return None
            
            if lb == b'':
                logger.info('readPayload: Server finished!')
                self.handle_receive_task.cancel()
                return None
            
            # read len first
            msglen = self.calcualte_length(lb)
            # check for correct streaming
            checkByte1 = await asyncio.wait_for(self._reader.readexactly(1), self.target.timeout)
    
            checkByte2 = await asyncio.wait_for(self._reader.readexactly(1), self.target.timeout)

            PayloadType = msgPayloadType.UNDEF
            wrongdata = True
            if checkByte1[0] == 0x55:
                #  prufen, ob stream richtig ist
                wrongdata = False
                if checkByte2[0] == 0x55:
                    PayloadType = msgPayloadType.STRING
                elif  checkByte2[0] == 0x50:
                    PayloadType = msgPayloadType.BINARY
                elif  checkByte2[0] == 0x51:
                    PayloadType = msgPayloadType.MSGPACK
                elif  checkByte2[0] == 0x52:
                    PayloadType = msgPayloadType.MSGPACKSOLAR
                elif  checkByte2[0] == 0x53:
                    PayloadType = msgPayloadType.JSONSOLAR                
                else:
                    wrongdata = True
            elif  checkByte1[0] == 0x3A: #':'
                wrongdata = False
                if checkByte2[0] == 0x20: #' '
                    PayloadType = msgPayloadType.ASCIISOLAR
                else:
                    wrongdata = True
        
            if  wrongdata:
                await self.clearReader()
                return None
            else:
                lb = await asyncio.wait_for(self._reader.readexactly(msglen), self.timeout)
                payload= msgPayload(PayloadType, lb, self)
                return payload
            
        except asyncio.TimeoutError:
                if self.on_connect_event!=None:
                    connectionInfo = msgConnectionInfo(connectionInfoType.CHECKCONNECTION,"",self)
                    await self.on_connect_event(connectionInfo)
                await self.clearReader()
        except Exception as err:  
            raise err


    async def connect(self,on_reciveEvent_batch=None, on_connect_event=None):
        ret = True
        while ret:
            logger.info(f'Connecting to server {self.target.host}:{self.target.port}')
            try:
                ret = await self.connecttoServer(on_reciveEvent_batch=on_reciveEvent_batch,on_connect_event=on_connect_event )
   
            
            except ConnectionRefusedError as err:
                logger.info(f'Connecting to server: {self.target.host} ConnectionRefusedError failed: {err}')  
            except asyncio.TimeoutError as err:
                logger.info(f'Connecting to server: {self.target.host} TimeoutError failed: {err}')        
            except Exception as err:  
                logger.info(f'Connecting to server: {self.target.host} Exception failed: {err}')       
            else:
                logger.info(f'Connecting to server: {self.target.host} is not connected')    
                    
            if (ret): await asyncio.sleep(4.0)


    async def connecttoServer(self,on_reciveEvent_batch=None,on_connect_event=None):

        # open up connection
        try:

            self._closeClient = False
            self._TimeoutCounter  = 0
            host = self.target.serverip if self.target.serverip is not None else self.target.host

            connect = asyncio.open_connection(host, self.target.port,loop=self.loop, ssl=None)
   
            self._reader, self._writer = await asyncio.wait_for( connect, timeout = self.target.timeout )


            self.handle_receive_task = asyncio.create_task(self.receivedata())
            self.handle_send_task = asyncio.create_task(self.senddata())
    
            if on_reciveEvent_batch!=None:
                self.on_reciveEvent_batch = on_reciveEvent_batch 
                self.handle_on_reciveEvent_batch = asyncio.create_task(self.on_reciveEvent_batch(self.in_queue)) 

            self._isconnected = True

            if on_connect_event!=None:
                self.on_connect_event = on_connect_event 
                connectionInfo = msgConnectionInfo(connectionInfoType.CONNECTED,"",self)
                await self.on_connect_event(connectionInfo)

                
            await self.handle_receive_task
            
            if self.on_connect_event!=None:
                connectionInfo = msgConnectionInfo(connectionInfoType.DISCONNECTED,"",self)
                await self.on_connect_event(connectionInfo)
            
            self._isconnected = False
            
            if (self._closeClient):
                return False
            else:
                return True

        except Exception as err:
            logger.error(f'connecttoServer-TCP-Error: {err}')
            raise err
            return True
        finally:
            self._isconnected = False
            if self.handle_receive_task!=None: self.handle_receive_task.cancel()
            if self.handle_send_task!=None: self.handle_send_task.cancel()
            if self.handle_on_reciveEvent_batch !=None: self.handle_on_reciveEvent_batch.cancel()
            
            if self._writer!=None:
                self._writer.close()
                self._writer.wait_closed()


     
    async def receivedata(self):
        try:
            while True:
                payload= await self.readPayload()
                if payload!=None:
                    await self.in_queue.put(payload)
                    print (f'{payload._payload}')
                    logger.info(f'{payload._payload}')
               
        except asyncio.CancelledError:
            return
        except asyncio.IncompleteReadError as e:
            await self.clearReader()
            logger.error(f'receivedata error:{e}')
            logger.info(f'receivedata error:{e}')  
        except Exception as e:
            logger.error(f'receivedata error:{e}')
            logger.info(f'receivedata error:{e}')   
        finally:
            self.handle_send_task.cancel()
                
     
    async def writesenddata(self,data):
        await self.out_queue.put(data)
     
    async def senddata(self):
        try:
            while True:
                try:
                    data = await self.out_queue.get()
                    if data is None:
                        logger.debug('Client finished!')
                        self._closeClient = True
                        self.handle_send_task.cancel()
                    else:
                        self._writer.write(data)
                        await self._writer.drain()
                    
                except Exception as exc:
                    logger.error(f'senddata:{exc}')
  
        
        except asyncio.CancelledError:
            return

        finally:
            self._writer.close()
            self.handle_receive_task.cancel()


    def isConnected(self):
        return     (self._writer!=None and self._reader!=None)

