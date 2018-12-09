#!/usr/bin/python3.6
import socket
import select
import threading
import unittest
import protolib.ipc_pack_pb2 as pb

class SouthboundApiManager(object):
  BUF_SIZE=1024

  @staticmethod
  def ip_i2s(ip_addr):
    """Convert from ip address as integer to as string

    You can convert to string value from input value of ip address as integer.

    Args:
      ip_addr_str(int): ip address as integer.
  
    Returns:
      str: ip address as string.
 
    """
    return "{}.{}.{}.{}".format((ip_addr>>24)&0xff,
                                (ip_addr>>16)&0xff,
                                (ip_addr>> 8)&0xff,
                                (ip_addr>> 0)&0xff)
  @staticmethod
  def ip_s2i(ip_addr_str):
    """Convert from ip address as string to as integer

    You can convert to integer value from input value of ip address as string.

    Args:
      ip_addr_str(str): ip address as string.
  
    Returns:
      integer: ip address as integer
 
    """
    try:
      h1,h2,h3,h4=ip_addr_str.split('.',4)
      h1=int(h1)
      h2=int(h2)
      h3=int(h3)
      h4=int(h4)
      return (h1<<24)+(h2<<16)+(h3<<8)+h4
    except:
      return None

  def __init__(self, target=None):
    """Constructor

    Create socket descriptor.
    In case of set the 'target' value, you can create connection(OPTIONAL).

    Args:
      target(tuple(str,int)): A target API endpoint as tuple of ipaddr and port.
  
    Returns:
      voided
 
    """
    self.sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if target:
      self.createConnection(target)

  def createConnection(self, target=('127.0.0.1',77099)):
    """Open the scoket connection

    You can connect to southbound API endpoint.

    Args:
      target(tuple(str,int)): A target API endpoint as tuple of ipaddr and port.
  
    Returns:
      voided
 
    """
    self.target=target
    self.sock.connect(target)

  def connectionClose(self):
    """Close the scoket connection

    You can disconnect to southbound API endpoint.

    Args:
      voided
  
    Returns:
      voided
 
    """
    if self.sock:
      try:
        self.sock.shutdown(socket.SHUT_RDWR)
      except OSError:
        pass
      self.sock.close()
  
  def printVal(self, res):
    """Printing a protobuf message

    You can print a protobuf message object for debugging.

    Args:
      res(Object): A protobuf message object.
  
    Returns:
      voided
 
    """
    print('-'*30)
    if res.HasField("request_code"):
      print('Request code: {}'.format(res.request_code))
    if res.HasField("response_code"):
      print('Response code: {}'.format(res.response_code))
    if res.HasField("id_selector"):
      print('id_selector: {}'.format(res.id_selector))
    if res.HasField("portid"):
      print('portid: {}'.format(res.portid))
    conf=res.rtp_config
    if conf.HasField("ip_dst_addr") and conf.HasField("udp_dst_port"):
      print('dst: {}:{}'.format(ip_i2s(conf.ip_dst_addr),conf.udp_dst_port))
    elif conf.HasField("ip_dst_addr") and not conf.HasField("udp_dst_port"):
      print('dst: {}'.format(ip_i2s(conf.ip_dst_addr)))
    elif not conf.HasField("ip_dst_addr") and conf.HasField("udp_dst_port"):
      print('dst: ?:{}'.format(conf.udp_dst_port))
    if conf.HasField("ip_src_addr") and conf.HasField("udp_src_port"):
      print('src: {}:{}'.format(ip_i2s(conf.ip_src_addr),conf.udp_src_port))
    elif conf.HasField("ip_src_addr") and not conf.HasField("udp_src_port"):
      print('src: {}'.format(ip_i2s(conf.ip_src_addr)))
    elif not conf.HasField("ip_src_addr") and conf.HasField("udp_src_port"):
      print('src: ?:{}'.format(conf.udp_src_port))
  
    if conf.HasField("rtp_timestamp"):
      print('timestamp: {}'.format(conf.rtp_timestamp))
    if conf.HasField("rtp_sequence"):
      print('sequence : {}'.format(conf.rtp_sequence))
    if conf.HasField("rtp_ssrc"):
      print('ssrc     : {}'.format(conf.rtp_ssrc))
  
  def getmsg(self, portid, selector):
    """Generate a protobuf message for read in CRUD operation

    You can generate a protobuf message object for read operation.
    'portid' and 'selector' are mandatory values for identifying resources.

    Args:
      request_code(Enum): The type of request code(Defined by '.proto' file).
      portid(int): Port id for identifying resources.
  
    Returns:
      Object: Generated request message object as protobuf.
 
    """
    pack=pb.RtpgenIPCmsgV1()
    pack.request_code=pb.RtpgenIPCmsgV1.READ
    pack.id_selector=selector
    pack.portid=portid
    return pack

  def delmsg(self, portid, selector):
    """Generate a protobuf message for delete in CRUD operation

    You can generate a protobuf message object for delete operation.
    'portid' and 'selector' are mandatory values for identifying resources.

    Args:
      request_code(Enum): The type of request code(Defined by '.proto' file).
      portid(int): Port id for identifying resources.
  
    Returns:
      Object: Generated request message object as protobuf.
 
    """
    pack=pb.RtpgenIPCmsgV1()
    pack.request_code=pb.RtpgenIPCmsgV1.DELETE
    pack.id_selector=selector
    pack.portid=portid
    return pack

  def postmsg(self, portid, selector, src=None, dst=None, timestamp=None, sequence=None, ssrc=None):
    """Generate a protobuf message for create in CRUD operation
    
    Details shown below 'writemsg' function.

    Args:
      portid(int): Port id for identifying resources.
      selector(int): Session id for identifying resources.
      src(tuple(str,int)): OPTIONAL. Source ip and port as updating data.
      dst(tuple(str,int)): OPTIONAL. Destination ip and port as updating data.
      timestamp(int): OPTIONAL. RTP timestamp as updating data.
      sequence(int): OPTIONAL. RTP sequence number as updating data.
      ssrc(int): OPTIONAL. RTP SSRC as updating data.
  
    Returns:
      Object: Generated request message object as protobuf.
 
    """
    return self.writemsg(pb.RtpgenIPCmsgV1.CREATE, portid,selector,src,dst,timestamp,sequence,ssrc)
  
  def putmsg(self, portid, selector, src=None, dst=None, timestamp=None, sequence=None, ssrc=None):
    """Generate a protobuf message for update in CRUD operation
    
    Details shown below 'writemsg' function.

    Args:
      portid(int): Port id for identifying resources.
      selector(int): Session id for identifying resources.
      src(tuple(str,int)): OPTIONAL. Source ip and port as updating data.
      dst(tuple(str,int)): OPTIONAL. Destination ip and port as updating data.
      timestamp(int): OPTIONAL. RTP timestamp as updating data.
      sequence(int): OPTIONAL. RTP sequence number as updating data.
      ssrc(int): OPTIONAL. RTP SSRC as updating data.
  
    Returns:
      Object: Generated request message object as protobuf.
 
    """
    return self.writemsg(pb.RtpgenIPCmsgV1.UPDATE, portid,selector,src,dst,timestamp,sequence,ssrc)
  
  def writemsg(self, request_code, portid, selector,
               src=None, dst=None, timestamp=None, sequence=None, ssrc=None):
    """Generate a protobuf message for create or update in CRUD operation

    You can generate a protobuf message object for create or update operation.
    This choise is made possible by set Enum value in 'request_code'.
    'portid' and 'selector' are mandatory values for identifying resources.
    Which 'src' to 'ssrc' are optional value, you set if needed update that value.

    Args:
      request_code(Enum): The type of request code(Defined by '.proto' file).
      portid(int): Port id for identifying resources.
      selector(int): Session id for identifying resources.
      src(tuple(str,int)): OPTIONAL. Source ip and port as updating data.
      dst(tuple(str,int)): OPTIONAL. Destination ip and port as updating data.
      timestamp(int): OPTIONAL. RTP timestamp as updating data.
      sequence(int): OPTIONAL. RTP sequence number as updating data.
      ssrc(int): OPTIONAL. RTP SSRC as updating data.
  
    Returns:
      Object: Generated request message object as protobuf.
 
    """
    pack=pb.RtpgenIPCmsgV1()
    pack.request_code=request_code
    pack.id_selector=selector
    pack.portid=portid
  
    if(src!=None):
        ip, port=src;
        pack.rtp_config.ip_src_addr=SouthboundApiManager.ip_s2i(ip)
        pack.rtp_config.udp_src_port=port
    if(dst!=None):
        ip, port=dst;
        pack.rtp_config.ip_dst_addr=SouthboundApiManager.ip_s2i(ip)
        pack.rtp_config.udp_dst_port=port
    if(timestamp!=None):
        pack.rtp_config.rtp_timestamp=timestamp
    if(sequence!=None):
        pack.rtp_config.rtp_sequence=sequence
    if(ssrc!=None):
        pack.rtp_config.rtp_ssrc=ssrc

    return pack

  def sendmsg(self, msg):
    """Send a protobuf message thorough the southbound API

    You can send a protobuf message thorough the southbound API.
    The message is serialized by protobuf method and transported by socket liblary.
    'None' will be returned if any exception raised or malformed packet returned.

    Args:
      msg(Object): A sending request protobuf message object.
  
    Returns:
      Object: A received response protobuf message object.
 
    """
    res=None
    try:
      self.sock.send(msg.SerializeToString())
    except (BrokenPipeError, ConnectionResetError) as e:
      refuseerror=None
      for retryCnt in range(3,0,-1):
        try:
          self.connectionClose()
          self.sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
          self.createConnection(self.target)
          raise ConnectionResetError
        except ConnectionRefusedError as e2:
          refuseerror=e2
          continue
        except ConnectionResetError as e2:
          raise e2
      else:
        raise refuseerror

    try:
      res=pb.RtpgenIPCmsgV1()
      res.ParseFromString(self.sock.recv(SouthboundApiManager.BUF_SIZE))

      if not res.HasField("response_code"):
        res=None
    except:
      res=None

    return res

  def searchBounds(self):
    """Search active port ids and max sessions

    You can know the active ports list and max sessions size that
    was configured in southbound program.

    Args:
      voided

    Returns:
      tuple(list, int): The pair of active ports list and max session size
    """
    portlist=[]
    maxsessios=0

    portid=99
    maxsessios=99999

    ret=self.sendmsg(self.getmsg(portid, maxsessios))
    if ret.response_code != pb.RtpgenIPCmsgV1.ERROR_NOT_FOUND or not ret.HasField('id_selector'):
      return None, None

    maxsessios=ret.id_selector
    ret=self.sendmsg(self.getmsg(portid, maxsessios))
    if ret.response_code != pb.RtpgenIPCmsgV1.ERROR_NOT_FOUND or not ret.HasField('portid'):
      return None, None

    for i in range(ret.portid+1):
      ret=self.sendmsg(self.getmsg(i, maxsessios))
      if ret.response_code == pb.RtpgenIPCmsgV1.ERROR_FORBIDDEN:
        continue
      portlist.append(i)

    return portlist, maxsessios+1

  def rscSync(self, portlist, session_size):
    data=[]
    for portid in portlist:
      for sessionid in range(session_size):
        ret=self.sendmsg(self.getmsg(portid, sessionid))
        if ret.response_code == pb.RtpgenIPCmsgV1.SUCCESS:
          s_ip=ret.rtp_config.ip_src_addr
          d_ip=ret.rtp_config.ip_dst_addr
          s_port=ret.rtp_config.udp_src_port
          d_port=ret.rtp_config.udp_dst_port
          timestamp=ret.rtp_config.rtp_timestamp
          subdata={portid: {sessionid: {}}}
          subdata={"portid": portid, "sessionid": sessionid}
          subdata["src"]={"ip": SouthboundApiManager.ip_i2s(s_ip), "port": s_port}
          subdata["dst"]={"ip": SouthboundApiManager.ip_i2s(d_ip), "port": d_port}
          subdata["enabled"]=True
          subdata["start_timestamp"]=timestamp
          data.append(subdata)
    return data

class Test_SouthboundApiManager(unittest.TestCase):
  ipc=None
  def setUp(self):
    self.ipc=SouthboundApiManager()
  
  def tearDown(self):
    self.ipc.connectionClose()
    self.ipc=None

  def checkHasField(self, msg, *args):
    ret=True
    for arg in args:
      ret &= msg.HasField(arg)
    return ret

  def checkHasNotField(self, msg, *args):
    ret=True
    for arg in args:
      ret &= not msg.HasField(arg)
    return ret
  
  def test_ip_i2s(self):
    self.assertEqual(SouthboundApiManager.ip_i2s(0xffffff00), '255.255.255.0')
    self.assertEqual(SouthboundApiManager.ip_i2s(0xff00ff00), '255.0.255.0')
    self.assertEqual(SouthboundApiManager.ip_i2s(0x7f500010), '127.80.0.16')

  def test_ip_s2i(self):
    self.assertEqual(0xffffff00, SouthboundApiManager.ip_s2i('255.255.255.0'))
    self.assertEqual(0xff00ff00, SouthboundApiManager.ip_s2i('255.0.255.0'  ))
    self.assertEqual(0x7f500010, SouthboundApiManager.ip_s2i('127.80.0.16'  ))

  def test_getmsg(self):
    portid=67
    selector=99
    pack=self.ipc.getmsg(portid, selector)
    self.assertTrue(self.checkHasField(pack,"request_code", "portid", "id_selector"))
    self.assertTrue(self.checkHasNotField(pack,"response_code", "size","rtp_config"))
    self.assertEqual(pack.request_code, pb.RtpgenIPCmsgV1.READ)
    self.assertEqual(pack.portid, portid)
    self.assertEqual(pack.id_selector, selector)

  def test_delmsg(self):
    portid=67
    selector=99
    pack=self.ipc.delmsg(portid, selector)
    self.assertTrue(self.checkHasField(pack,"request_code", "portid", "id_selector"))
    self.assertTrue(self.checkHasNotField(pack,"response_code", "size","rtp_config"))
    self.assertEqual(pack.request_code, pb.RtpgenIPCmsgV1.DELETE)
    self.assertEqual(pack.portid, portid)
    self.assertEqual(pack.id_selector, selector)

  def test_writemsg(self):
    request_code=pb.RtpgenIPCmsgV1.READ
    portid=67
    selector=99
    src=('255.255.255.0',9341)
    dst=('127.0.0.1',7813)
    pack=self.ipc.writemsg(request_code, portid, selector, src=src, dst=dst)
    self.assertTrue(self.checkHasField(pack,"request_code", "portid", "id_selector", "rtp_config"))
    self.assertTrue(self.checkHasNotField(pack,"response_code", "size"))
    self.assertTrue(self.checkHasField(pack.rtp_config,"ip_src_addr", "ip_dst_addr", "udp_src_port", "udp_dst_port"))
    self.assertTrue(self.checkHasNotField(pack.rtp_config,"rtp_timestamp", "rtp_sequence","rtp_ssrc"))
    self.assertEqual(pack.request_code, pb.RtpgenIPCmsgV1.READ)
    self.assertEqual(pack.portid, portid)
    self.assertEqual(pack.id_selector, selector)
    self.assertEqual(pack.rtp_config.ip_dst_addr, 0x7f000001)
    self.assertEqual(pack.rtp_config.ip_src_addr, 0xffffff00)
    self.assertEqual(pack.rtp_config.udp_dst_port, 7813)
    self.assertEqual(pack.rtp_config.udp_src_port, 9341)

  def test_writemsg_full(self):
    request_code=pb.RtpgenIPCmsgV1.READ
    portid=67
    selector=99
    src=('255.255.255.0',9341)
    dst=('127.0.0.1',7813)
    timestamp=135
    ssrc=0x38fd93a1
    sequence=791
    pack=self.ipc.writemsg(request_code, portid, selector, src=src, dst=dst,
                           ssrc=ssrc, sequence=sequence, timestamp=timestamp)
    self.assertTrue(self.checkHasField(pack,"request_code", "portid", "id_selector", "rtp_config"))
    self.assertTrue(self.checkHasNotField(pack,"response_code", "size"))
    self.assertTrue(self.checkHasField(pack.rtp_config,"ip_src_addr", "ip_dst_addr", "udp_src_port", "udp_dst_port",
                                                       "rtp_timestamp", "rtp_sequence","rtp_ssrc"))
    self.assertEqual(pack.request_code, pb.RtpgenIPCmsgV1.READ)
    self.assertEqual(pack.portid, portid)
    self.assertEqual(pack.id_selector, selector)
    self.assertEqual(pack.rtp_config.ip_dst_addr,   0x7f000001)
    self.assertEqual(pack.rtp_config.ip_src_addr,   0xffffff00)
    self.assertEqual(pack.rtp_config.udp_dst_port,  7813)
    self.assertEqual(pack.rtp_config.udp_src_port,  9341)
    self.assertEqual(pack.rtp_config.rtp_timestamp, 135)
    self.assertEqual(pack.rtp_config.rtp_sequence,  791)
    self.assertEqual(pack.rtp_config.rtp_ssrc,      0x38fd93a1)

  def test_postmsg(self):
    portid=67
    selector=99
    pack=self.ipc.postmsg(portid, selector)
    self.assertEqual(pack.request_code, pb.RtpgenIPCmsgV1.CREATE)

  def test_putmsg(self):
    portid=67
    selector=99
    pack=self.ipc.putmsg(portid, selector)
    self.assertEqual(pack.request_code, pb.RtpgenIPCmsgV1.UPDATE)

  def stub_server(sock, msg, loop=1, msgs=None):
    ssock=None
    sock.listen(1)
    try:
      ssock, remoteaddrs = sock.accept() 
      for i in range(loop):
        ssock.recv(SouthboundApiManager.BUF_SIZE)
        if msgs!=None:
          msg=msgs[i]
        ssock.send(msg.SerializeToString())
    except OSError:
      pass
    finally:
      if ssock:
        ssock.close()
    
  def test_sendmsg(self):
    th=None
    sock=None
    server=None
    target=('127.0.0.1',43991)

    expectmsg=pb.RtpgenIPCmsgV1()
    expectmsg.response_code=pb.RtpgenIPCmsgV1.SUCCESS
    expectmsg.portid=1
    expectmsg.id_selector=2
    expectmsg.size=3
    expectmsg.rtp_config.ip_dst_addr=4
    expectmsg.rtp_config.ip_src_addr=5
    expectmsg.rtp_config.udp_dst_port=6
    expectmsg.rtp_config.udp_src_port=7
    expectmsg.rtp_config.rtp_timestamp=8
    expectmsg.rtp_config.rtp_sequence=9
    expectmsg.rtp_config.rtp_ssrc=10

    try:
      server=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      server.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEPORT, 1,)
      server.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEADDR, 1,)
      server.bind(target)
      th=threading.Thread(target=Test_SouthboundApiManager.stub_server, args=(server, expectmsg, ))
      th.start()
      self.ipc.createConnection(target)
      res=self.ipc.sendmsg(self.ipc.getmsg(0,1))
      self.assertEqual(res.response_code, pb.RtpgenIPCmsgV1.SUCCESS)
      self.assertEqual(res.portid,      1)
      self.assertEqual(res.id_selector, 2)
      self.assertEqual(res.size,        3)
      self.assertEqual(res.rtp_config.ip_dst_addr,   4)
      self.assertEqual(res.rtp_config.ip_src_addr,   5)
      self.assertEqual(res.rtp_config.udp_dst_port,  6)
      self.assertEqual(res.rtp_config.udp_src_port,  7)
      self.assertEqual(res.rtp_config.rtp_timestamp, 8)
      self.assertEqual(res.rtp_config.rtp_sequence,  9)
      self.assertEqual(res.rtp_config.rtp_ssrc,     10)
    finally:
      if th:
        th.join()
      if sock:
        sock.close()
      if server:
        server.close()

  def test_sendmsgReconnect(self):
    th=None
    sock=None
    server=None
    target=('127.0.0.1',43991)

    expectmsg=pb.RtpgenIPCmsgV1()
    expectmsg.response_code=pb.RtpgenIPCmsgV1.SUCCESS
    expectmsg.portid=1
    expectmsg.id_selector=2
    expectmsg.size=3
    expectmsg.rtp_config.ip_dst_addr=4
    expectmsg.rtp_config.ip_src_addr=5
    expectmsg.rtp_config.udp_dst_port=6
    expectmsg.rtp_config.udp_src_port=7
    expectmsg.rtp_config.rtp_timestamp=8
    expectmsg.rtp_config.rtp_sequence=9
    expectmsg.rtp_config.rtp_ssrc=10

    try:
      server=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      server.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEPORT, 1,)
      server.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEADDR, 1,)
      server.bind(target)
      th=threading.Thread(target=Test_SouthboundApiManager.stub_server, args=(server, expectmsg, ))
      th.start()
      self.ipc.createConnection(target)
      server.shutdown(socket.SHUT_RDWR)
      server.close()
      th.join()

      server=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      server.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEPORT, 1,)
      server.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEADDR, 1,)
      server.bind(target)
      th=threading.Thread(target=Test_SouthboundApiManager.stub_server, args=(server, expectmsg, ))
      th.start()

      self.assertRaises(ConnectionResetError, lambda: self.ipc.sendmsg(self.ipc.getmsg(0,1)))

      res=self.ipc.sendmsg(self.ipc.getmsg(0,1))
      self.assertEqual(res.response_code, pb.RtpgenIPCmsgV1.SUCCESS)
      self.assertEqual(res.portid,      1)
      self.assertEqual(res.id_selector, 2)
      self.assertEqual(res.size,        3)
      self.assertEqual(res.rtp_config.ip_dst_addr,   4)
      self.assertEqual(res.rtp_config.ip_src_addr,   5)
      self.assertEqual(res.rtp_config.udp_dst_port,  6)
      self.assertEqual(res.rtp_config.udp_src_port,  7)
      self.assertEqual(res.rtp_config.rtp_timestamp, 8)
      self.assertEqual(res.rtp_config.rtp_sequence,  9)
      self.assertEqual(res.rtp_config.rtp_ssrc,     10)
    finally:
      if sock:
        sock.close()
      if server:
        server.shutdown(socket.SHUT_RDWR)
        server.close()
      if th:
        th.join()


  def test_sendmsgReconnectFail(self):
    th=None
    sock=None
    server=None
    target=('127.0.0.1',43991)

    expectmsg=pb.RtpgenIPCmsgV1()
    expectmsg.response_code=pb.RtpgenIPCmsgV1.SUCCESS
    expectmsg.portid=1
    expectmsg.id_selector=2
    expectmsg.size=3
    expectmsg.rtp_config.ip_dst_addr=4
    expectmsg.rtp_config.ip_src_addr=5
    expectmsg.rtp_config.udp_dst_port=6
    expectmsg.rtp_config.udp_src_port=7
    expectmsg.rtp_config.rtp_timestamp=8
    expectmsg.rtp_config.rtp_sequence=9
    expectmsg.rtp_config.rtp_ssrc=10

    try:
      server=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      server.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEPORT, 1,)
      server.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEADDR, 1,)
      server.bind(target)
      th=threading.Thread(target=Test_SouthboundApiManager.stub_server, args=(server, expectmsg, ))
      th.start()
      self.ipc.createConnection(target)
      server.shutdown(socket.SHUT_RDWR)
      server.close()
      th.join()

      self.assertRaises(ConnectionRefusedError, lambda: self.ipc.sendmsg(self.ipc.getmsg(0,1)))
    finally:
      if sock:
        sock.close()
      if server:
        try:
          server.shutdown(socket.SHUT_RDWR)
        except OSError:
          pass
        server.close()
      if th:
        th.join()

  def test_searchBounds(self):
    th=None
    sock=None
    server=None
    target=('127.0.0.1',43991)

    msgs=[]

    expectmsg=pb.RtpgenIPCmsgV1()
    expectmsg.response_code=pb.RtpgenIPCmsgV1.ERROR_NOT_FOUND
    expectmsg.id_selector=84
    msgs.append(expectmsg)

    expectmsg=pb.RtpgenIPCmsgV1()
    expectmsg.response_code=pb.RtpgenIPCmsgV1.ERROR_NOT_FOUND
    expectmsg.portid=31
    msgs.append(expectmsg)

    for i in range(32):
      expectmsg=pb.RtpgenIPCmsgV1()
      if i in [0,4,9,31]:
        expectmsg.response_code=pb.RtpgenIPCmsgV1.ERROR_NOT_FOUND
      else:
        expectmsg.response_code=pb.RtpgenIPCmsgV1.ERROR_FORBIDDEN
        expectmsg.portid=i
      msgs.append(expectmsg)

    try:
      server=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      server.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEPORT, 1,)
      server.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEADDR, 1,)
      server.bind(target)
      th=threading.Thread(target=Test_SouthboundApiManager.stub_server,
                          args=(server, expectmsg, len(msgs), msgs, ))
      th.start()
      self.ipc.createConnection(target)
      ports, sessionsize=self.ipc.searchBounds()
      self.assertEqual(ports, [0,4,9,31])
      self.assertEqual(sessionsize, 85)
    finally:
      if th:
        th.join()
      if sock:
        sock.close()
      if server:
        server.close()

  def test_rscSync(self):
    th=None
    sock=None
    server=None
    target=('127.0.0.1',43991)

    msgs=[]

    portlist=[0, 4, 9, 31]
    activeSessions=[4, 8]

    for j in portlist:
      for i in range(10):
        expectmsg=pb.RtpgenIPCmsgV1()
        if i in activeSessions:
          expectmsg.response_code=pb.RtpgenIPCmsgV1.SUCCESS
          expectmsg.portid=j
          expectmsg.id_selector=i
          expectmsg.rtp_config.ip_dst_addr=SouthboundApiManager.ip_s2i("192.168.0.1")
          expectmsg.rtp_config.ip_src_addr=SouthboundApiManager.ip_s2i("172.16.0.155")
          expectmsg.rtp_config.udp_dst_port=5000+i
          expectmsg.rtp_config.udp_src_port=8000+i
          expectmsg.rtp_config.rtp_timestamp=12345
          expectmsg.rtp_config.rtp_sequence=5678
          expectmsg.rtp_config.rtp_ssrc=12345
        else:
          expectmsg.response_code=pb.RtpgenIPCmsgV1.ERROR_NOT_FOUND
        msgs.append(expectmsg)


    try:
      server=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      server.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEPORT, 1,)
      server.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEADDR, 1,)
      server.bind(target)
      th=threading.Thread(target=Test_SouthboundApiManager.stub_server,
                          args=(server, expectmsg, len(msgs), msgs, ))
      th.start()
      self.ipc.createConnection(target)
      rsclist=self.ipc.rscSync(portlist, 10)

      for portid in portlist:
        for sessionid in activeSessions:
          data=rsclist.pop(0)
          self.assertEqual(data["portid"], portid)
          self.assertEqual(data["sessionid"], sessionid)
          self.assertEqual(data["enabled"], True)
          self.assertEqual(data['src']['ip'], "172.16.0.155")
          self.assertEqual(data['dst']['ip'], "192.168.0.1")
          self.assertEqual(data['src']['port'], 8000+sessionid)
          self.assertEqual(data['dst']['port'], 5000+sessionid)
          self.assertEqual(data['start_timestamp'], 12345)
    finally:
      if th:
        th.join()
      if sock:
        sock.close()
      if server:
        server.close()
