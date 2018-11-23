#!/usr/bin/env python3.6
# -*- coding:utf-8 -*-

import random
import unittest
import os
import json
import logging as log
import socket
import threading
import socket
import ipaddress
import werkzeug.exceptions 
from time import time, sleep
from threading import Thread
from logging import getLogger, Formatter, StreamHandler
from flask import Flask, request, jsonify
from google.protobuf.json_format import MessageToDict

import protolib.ipc_pack_pb2 as pb
import protolib.sb_api as sbapi

''' ENVIROMENT VARIABLEs '''
api_ip       =     os.getenv("BIND_IP"    , "0.0.0.0"  )
api_port     = int(os.getenv("BIND_PORT"  , 5000       ))
target_ip    =     os.getenv("SB_API_IP"  , "127.0.0.1")
target_port  = int(os.getenv("SB_API_PORT", 7700       ))
loglevel     = int(os.getenv("LOGLEVEL"  , log.DEBUG  ))
audio_file   =   os.getenv("AUDIO_FILE"  , None       )

''' global variables '''
app = Flask(__name__)
logger = getLogger(__name__)
rscmap = None
sb = None

class ResourceMapManager(object):
  def __init__(self):
    ''' 
    resouce map : like below
    {
      portid:{
        sessionid:{
          "enabled":true,
          "src":{"ip":ipaddr, "port":portnum},
          "dst":{"ip":ipaddr, "port":portnum},
          "start_timestamp":rtp_timestamp_when_started
        }
      }
    }
    '''
    self.resourceMap={}
    self.maxportid=0
    self.maxsessionid=0

  def setMaxSessionid(self, sessionid):
    self.maxsessionid=sessionid

  def setMaxPortid(self, portid):
    rsc=self.resourceMap
    for i in range(0, portid+1):
      rsc[i]={}
    self.maxportid=portid

  def getrsc(self, portid, sessionid):
    """Get resource map value using port id and sessionid
 
    You can get resouce map value like src, dst, is active and started time,
    using port id and session id.
    'None' will be returned if you can not find from resource map.
  
    Args:
      portid (int): Port id in resouce map.
      sessionid (int): Session id in resouce map.
  
    Returns:
      Object: Found resource, included 'enabled(bool)',
              'src(ip,port)', 'dst(ip,port)' and 'start_timestamp(int)'
  
    """
    rsc=self.resourceMap
    if not portid in rsc or not sessionid in rsc[portid]:
      return None
    return rsc[portid][sessionid]

  def srchrsc(self, src, dst):
    """Search portid and sessionid from resource map 
 
    You can find port id and session id from resouce map,
    using src-ip, src-port, dst-ip and dst-port.
    In case of same src and dst in different port id or sessionid,
    you can find only one pair(NOT guaranteed as get same result anytime.).
    'None' will be returned if you can not find from resource map.
    This funciton using liner searching algorithm.
    Order of the function is O(n*m).
    # n=number of portid, m=number of sessionid.
  
    Args:
      src (tuple of (str, int)): Soruce of ip address(as str) and
                                 port number(as int) tuples.
      dst (tuple of (srt, int)): Destination of ip address and port number.
  
    Returns:
      Integer: Found port id
      Integer: Found session id
  
    """
    sip, sport = src
    dip, dport = dst
    rsc=self.resourceMap
    for portid in rsc.keys():
      for sessionid in rsc[portid].keys():
        tgt=rsc[portid][sessionid]
        if sip == tgt['src']['ip'] and sport == tgt['src']['port'] and \
           dip == tgt['dst']['ip'] and dport == tgt['dst']['port'] :
           return portid, sessionid
    return None, None
  
  def addrsc(self, portid, sessionid, src, dst, timestamp):
    """Add a new resource into resource map 
 
    You can add a new resource information such as 'src(ip,port)',
    'dst(ip,port)' and 'start_timestamp(int)' by the port id and the session id.
    And also mark 'enabled' to meaning resource is active.
    'None' will be returned if you can not find port id or session id
    from resource map.
  
    Args:
      portid(int): Target of port id.
      sessionid(int): Target of session id.
      src (tuple of (str, int)): Soruce of ip address(as str) and 
                                 port number(as int) tuples.
      dst (tuple of (srt, int)): Destination of ip address and port number.
      timestamp(int): Set a started time to calculate a duration.
  
    Returns:
      Object: Created resrouce, included 'enabled(bool)', 
              'src(ip,port)', 'dst(ip,port)' and 'start_timestamp(int)'
  
    """
    rsc=self.resourceMap
    if not portid in rsc:
      rsc[portid]={}
    if sessionid in rsc[portid] and rsc[portid][sessionid]['enabled']:
        return None
    sip, sport = src
    dip, dport = dst
    
    rsc[portid][sessionid]={
      "enabled":True,
      "src":{"ip":sip,"port":sport},
      "dst":{"ip":dip,"port":dport},
      "start_timestamp":timestamp
    }
    return rsc[portid][sessionid]
  
  def putrsc(self, portid, sessionid, src, dst, timestamp=None):
    """Update an existing resource into resource map 
 
    You can update a existing resource information such as 'src(ip,port)',
    'dst(ip,port)' and 'start_timestamp(int)' by port id and session id.
    'timestamp' is optional update information(NOT mandatory value).
    'None' will be returned if you can not find port id or session id
    from resource map.
  
    Args:
      portid(int): Target of port id.
      sessionid(int): Target of session id.
      src (tuple of (str, int)): Soruce of ip address(as str) and 
                                 port number(as int) tuples.
      dst (tuple of (srt, int)): Destination of ip address and port number.
      timestamp(int): OPTIONAL. Reset a started time to calculate a duration.
  
    Returns:
      Object: Created resrouce, included 'enabled(bool)', 
              'src(ip,port)', 'dst(ip,port)' and 'start_timestamp(int)'
  
    """
    rsc=self.resourceMap
    if not portid in rsc or not sessionid in rsc[portid]:
      return None
    sip, sport = src
    dip, dport = dst

    rsc[portid][sessionid]["src"]["ip"  ]=sip
    rsc[portid][sessionid]["src"]["port"]=sport
    rsc[portid][sessionid]["dst"]["ip"  ]=dip
    rsc[portid][sessionid]["dst"]["port"]=dport
    if timestamp:
      rsc[portid][sessionid]["start_timestamp"]=timestamp
    return rsc[portid][sessionid]
  
  def delrsc(self, portid, sessionid):
    """Delete an existing resource into resource map 
 
    You can delete a existing resource information by the port id and the session id.
    This function will not flush out an existing resource object,
    it is just mark 'disabled' as resource is inactive.
    'None' will be returned if you can not find port id or session id
    from resource map.
  
    Args:
      portid(int): Target of port id.
      sessionid(int): Target of session id.
  
    Returns:
      Object: Created resrouce, included 'enabled(bool)', 
              'src(ip,port)', 'dst(ip,port)' and 'start_timestamp(int)'
  
    """
    rsc=self.resourceMap
    if not portid in rsc or not sessionid in rsc[portid]:
      return None
    rsc[portid][sessionid]["enabled"]=False
    return rsc[portid][sessionid]

  def validationIds(self, portid, sessionid):
    if not(0 <= portid and portid <= self.maxportid):
      return 416, 'portid range error (0 <= n <= {})'.format(self.maxportid)
    if not(0 <= sessionid and sessionid <= self.maxsessionid):
      return 416, 'sessionid range error (0 <= n <= {})'.format(self.maxsessionid)
    if not(portid in self.resourceMap):
      return 403, 'port id {} does not active'.format(portid)
    if not(sessionid in self.resourceMap[portid]) or not(self.resourceMap[portid][sessionid]['enabled']):
      return 404, 'port id {} : session id {} does not active'.format(portid, sessionid)
    return 200, None

''' API Call '''
@app.route('/api/v1/id/<portid>:<sessionid>',methods=['GET','DELETE','POST','PUT'])
#@app.route('/api/v1/id/<portid>:<sessionid>/<s_ip>:<s_port>/<d_ip>:<d_port>',
#    methods=['POST','PUT'])
def apiid(portid,sessionid,d_ip=None,d_port=None,s_ip=None,s_port=None):
  retCode=200
  result={}
  src=None
  dst=None
  try:
    portid=int(portid)
    sessionid=int(sessionid)
    result['port_id']=portid
    result['session_id']=sessionid

    if request.method in ['PUT','POST']:
      s_ip   = request.args.get('s_ip'  , default=None, type=str)
      s_port = request.args.get('s_port', default=None, type=int)
      d_ip   = request.args.get('d_ip'  , default=None, type=str)
      d_port = request.args.get('d_port', default=None, type=int)

      if not(s_ip and d_ip and s_port and d_port):
        raise KeyError
      s_port=int(s_port)
      if s_port <= 0 or 1<<16 <= s_port:
        raise ValueError
      src=(s_ip, s_port)
      d_port=int(d_port)
      if d_port <= 0 or 1<<16 <= d_port:
        raise ValueError
      dst=(d_ip, d_port)
  except ValueError:
    return returnErrorContent(400, 'invalid argument(Not a valid number)', result)
  except KeyError:
    return returnErrorContent(400, 'mandatory input not found', result)

  try:
    if s_ip:
      ipaddress.ip_address(s_ip)
    if d_ip:
      ipaddress.ip_address(d_ip)
  except ValueError:
    return returnErrorContent(400, 'invalid argument(Not a valid IP address)', result)
  
  error, msg=rscmap.validationIds(portid, sessionid)
  if error != 200 and error != 404:
    return returnErrorContent(error, msg, result)

  try:
    if request.method in ['POST']: 
      if error == 200:
        # Conflict error will reply if resource is existed
        return returnErrorContent(409,
            'port id:{} session id:{} is already exist'.format(portid, sessionid),
            result)

      # Create Southbound and resource map
      tmstmp=random.randint(0,0xffffffff)
      ret=sb.sendmsg(sb.postmsg(portid, sessionid, src=src, dst=dst, timestamp=tmstmp))
      if not ret or ret.response_code != pb.RtpgenIPCmsgV1.SUCCESS:
        return returnErrorContent(500, 'IPC layer error', result)

      rsc=rscmap.addrsc(portid, sessionid, src=src, dst=dst, timestamp=tmstmp)
      retCode=200
      result['state']=rsc
      result['error']=None
    elif request.method in ['PUT','GET','DELETE']:
      if error == 404:
        return returnErrorContent(error, msg, result)
      # Read from resource map
      if request.method == 'GET':
        rsc=rscmap.getrsc(portid, sessionid)
        result['state']=rsc
      # Delete Southbound and resource map
      elif request.method == 'DELETE':
        ret=sb.sendmsg(sb.delmsg(portid,sessionid))
        if not ret or ret.response_code != pb.RtpgenIPCmsgV1.SUCCESS:
          return returnErrorContent(500, 'IPC layer error', result)

        rsc=rscmap.delrsc(portid, sessionid)
        result['state']=rsc
      # Update Southbound and resource map
      elif request.method == 'PUT':
        ret=sb.sendmsg(sb.putmsg(portid, sessionid, src=src, dst=dst))
        if not ret or ret.response_code != pb.RtpgenIPCmsgV1.SUCCESS:
          return returnErrorContent(500, 'IPC layer error', result)

        rsc=rscmap.putrsc(portid, sessionid, src=src, dst=dst)
        result['state']=rsc
  except ValueError as e:
    return returnErrorContent(400, 'input is not a number', result)
  except TypeError as e:
    return returnErrorContent(400, 'invalid argument', result)
  except Exception as e:
    return returnErrorContent(500, 'internal server error', result)
    #return returnErrorContent(500, e.__str__(), result)

  if 'error' in result and not result['error']:
    del result['error']
  result['result']=retCode

  return jsonify(result), retCode

#@app.route('/api/v1/resources/<s_ip>:<s_port>/<d_ip>:<d_port>',
#    methods=['POST','GET','DELETE'])
#def apirsc(d_ip,d_port,s_ip,s_port):
#  retCode=200
#  result={}
#  try:
#    d_port=int(d_port)
#    s_port=int(s_port)
#    if request.method in ['POST']: # ADD
#      pass
#    elif request.method in ['GET','DELETE']:
#      pass
#    result['id']=cic
#  except ValueError as e:
#    retCode=400
#    result['error']='input is not a number'
#  except TypeError as e:
#    retCode=400
#    result['error']=e.__str__()
#  except Exception as e:
#    if retCode==200:
#      retCode=500
#    result['error']=e.__str__()
#  result['result']=retCode
#
#  return jsonify(result), retCode

def returnErrorContent(code, reason, base=None):
  if base:
    base['result']=code
    base['error']=reason
    return jsonify(base), code
  return jsonify({'result':code,'error':reason}), code

@app.errorhandler(400)
@app.errorhandler(401)
@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(405)
@app.errorhandler(409)
@app.errorhandler(500)
@app.errorhandler(501)
@app.errorhandler(503)
def error_handler(error):
  '''
   Description
    - abort(400 - 405) / abort(500 - 503) した時に
    レスポンスをレンダリングするハンドラ
  '''
  response = jsonify({ 'error': error.name.lower(), 'result': error.code })
  return response, error.code

def connectServer(target):
  global rscmap
  sb.createConnection(target)

''' main logic '''
def main():
  global rscmap
  global sb
  rscmap = ResourceMapManager()
  rscmap.setMaxPortid(10)
  rscmap.setMaxSessionid(10)

  target=(target_ip, target_port)
  sb = sbapi.SouthboundApiManager(target)

  logger.setLevel(loglevel)
  sh = StreamHandler()
  logger.addHandler(sh)
  formatter = Formatter('%(asctime)s:%(lineno)d:%(levelname)s:%(message)s')
  sh.setFormatter(formatter)

  logger.info('server started...')

  logger.debug('session informations were initialized...')

  logger.info('API interface is up...')
  logger.debug('API binded {}:{}...'.format(api_ip,api_port))
  app.run(host=api_ip,port=api_port)

  logger.info('server termsinating...')
  if sb:
    sb.connectionClose()
    sb=None
  if rscmap:
    rscmap=None

if __name__ == '__main__':
  main()

''' Unit Test Cases '''

class TestRTPgenRESTGW(unittest.TestCase):
  def setUp(self):
    global rscmap
    global sb
    self.server = None
    self.th = None
    self.c = app.test_client()
    rscmap = ResourceMapManager()
    rscmap.setMaxPortid(10)
    rscmap.setMaxSessionid(10)
    sb = sbapi.SouthboundApiManager()
    self.target=('127.0.0.1', 55077)

  def tearDown(self):
    global rscmap
    global sb
    if sb:
      sb.connectionClose()
      sb=None
    if rscmap:
      rscmap=None
    if self.c:
      self.c=None
    if self.server:
      self.server.shutdown(socket.SHUT_RDWR)
      self.server.close()
    if self.th:
      self.th.join()

  def stubServerLaunch(self, msg, loop=1):
    self.server=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.server.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEPORT, 1,)
    self.server.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEADDR, 1,)
    self.server.bind(self.target)
    self.th=threading.Thread(target=sbapi.Test_SouthboundApiManager.stub_server, 
                           args=(self.server, msg, loop,))
    self.th.start()

  def test_apiid_get(self):
    portid, sessionid=(0, 3)
    s_ip='192.168.0.1'; s_port=5000; src=(s_ip, s_port)
    d_ip='172.16.0.1' ; d_port=8000; dst=(d_ip, d_port)
    tmstmp=random.randint(0,0xffffffff)
    rscmap.addrsc(portid, sessionid, src, dst, tmstmp)
    
    self.stubServerLaunch(self.helperCreateSuccessMsg(portid,sessionid))
    connectServer(self.target)
    
    rs=self.c.get('/api/v1/id/0:3')
    state=200; err=None; enabled=True
    self.helperDataCheck(rs, state, err, portid, sessionid, enabled, tmstmp, src, dst)

  def test_apiid_get_id_notfound(self):
    portid, sessionid=(0, 3)
    s_ip='192.168.0.1'; s_port=5000; src=(s_ip, s_port)
    s_ip='192.168.0.1'; s_port=5000; src=(s_ip, s_port)
    d_ip='172.16.0.1' ; d_port=8000; dst=(d_ip, d_port)
    tmstmp=random.randint(0,0xffffffff)
    rscmap.addrsc(portid, sessionid, src, dst, tmstmp)
    
    self.stubServerLaunch(self.helperCreateSuccessMsg(portid,sessionid))
    connectServer(self.target)
     
    s_ip='10.0.0.1'; s_port=9000; src=(s_ip, s_port)
    rs=self.c.get('/api/v1/id/0:4')
    state=404; err='port id {} : session id {} does not active'.format(0,4)
    self.helperDataCheck(rs, state, err, portid, sessionid=4)

  def test_apiid_del(self):
    portid, sessionid=(0, 3)
    s_ip='192.168.0.1'; s_port=5000; src=(s_ip, s_port)
    d_ip='172.16.0.1' ; d_port=8000; dst=(d_ip, d_port)
    tmstmp=random.randint(0,0xffffffff)
    rscmap.addrsc(portid, sessionid, src, dst, tmstmp)

    self.stubServerLaunch(self.helperCreateSuccessMsg(portid,sessionid))
    connectServer(self.target)
    
    rs=self.c.delete('/api/v1/id/0:3')
    state=200; err=None; enabled=False
    self.helperDataCheck(rs, state, err, portid, sessionid, enabled, tmstmp, src, dst)

  def test_apiid_del_id_notfound(self):
    portid, sessionid=(0, 3)
    s_ip='192.168.0.1'; s_port=5000; src=(s_ip, s_port)
    d_ip='172.16.0.1' ; d_port=8000; dst=(d_ip, d_port)
    tmstmp=random.randint(0,0xffffffff)
    rscmap.addrsc(portid, sessionid, src, dst, tmstmp)
    
    self.stubServerLaunch(self.helperCreateSuccessMsg(portid,sessionid))
    connectServer(self.target)
     
    s_ip='10.0.0.1'; s_port=9000; src=(s_ip, s_port)
    rs=self.c.delete('/api/v1/id/0:4')
    state=404; err='port id {} : session id {} does not active'.format(0,4)
    self.helperDataCheck(rs, state, err, portid, sessionid=4)

  def test_apiid_post(self):
    portid, sessionid=(0, 3)
    s_ip='192.168.0.1'; s_port=5000; src=(s_ip, s_port)
    s_ip='192.168.0.1'; s_port=5000; src=(s_ip, s_port)
    d_ip='172.16.0.1' ; d_port=8000; dst=(d_ip, d_port)

    self.stubServerLaunch(self.helperCreateSuccessMsg(portid,sessionid))
    connectServer(self.target)
    
    suffix='s_ip={}&s_port={}&d_ip={}&d_port={}'.format(s_ip, s_port, d_ip, d_port)
    rs=self.c.post('/api/v1/id/{}:{}?{}'.format(portid, sessionid, suffix))
    state=200; err=None; enabled=True
    self.helperDataCheck(rs, state, err, portid, sessionid, enabled, None, src, dst)

  def test_apiid_post_always_exist(self):
    portid, sessionid=(0, 3)
    s_ip='192.168.0.1'; s_port=5000; src=(s_ip, s_port)
    d_ip='172.16.0.1' ; d_port=8000; dst=(d_ip, d_port)
    tmstmp=random.randint(0,0xffffffff)
    rscmap.addrsc(portid, sessionid, src, dst, tmstmp)

    self.stubServerLaunch(self.helperCreateSuccessMsg(portid,sessionid))
    connectServer(self.target)
    
    suffix='s_ip={}&s_port={}&d_ip={}&d_port={}'.format(s_ip, s_port, d_ip, d_port)
    rs=self.c.post('/api/v1/id/{}:{}?{}'.format(portid, sessionid, suffix))
    state=409; err='port id:{} session id:{} is already exist'.format(portid, sessionid)
    self.helperDataCheck(rs, state, err, portid, sessionid)

  def test_apiid_post_id_invalid_argument_port(self):
    state=400

    err='mandatory input not found'
    suffix='s_ip={}&s_port={}&d_ip={}&d_port={}'.format(
                              '10.0.0.1', 6000, '172.16.0.1', '7l0a0')
    rs=self.c.post('/api/v1/id/0:3?'+suffix)
    self.helperDataCheck(rs, state, err, portid=0, sessionid=3)

    err='invalid argument(Not a valid number)'
    suffix='s_ip={}&s_port={}&d_ip={}&d_port={}'.format(
                              '10.0.0.1', 6000, '172.16.0.1', 99999999)
    rs=self.c.post('/api/v1/id/0:3?'+suffix)
    self.helperDataCheck(rs, state, err, portid=0, sessionid=3)

    suffix='s_ip={}&s_port={}&d_ip={}&d_port={}'.format(
                              '10.0.0.1', -1, '172.16.0.1', 7000)
    rs=self.c.post('/api/v1/id/0:3?'+suffix)
    self.helperDataCheck(rs, state, err, portid=0, sessionid=3)

  def test_apiid_post_id_invalid_argument_ip(self):
    state=400
    err='invalid argument(Not a valid IP address)'

    suffix='s_ip={}&s_port={}&d_ip={}&d_port={}'.format(
                              '10.0.0.1', 6000, '256.0.0.1', 7000)
    rs=self.c.post('/api/v1/id/0:3?'+suffix)
    self.helperDataCheck(rs, state, err, portid=0, sessionid=3)

    suffix='s_ip={}&s_port={}&d_ip={}&d_port={}'.format(
                              '10.0.0.1', 6000, '0.0.1', 7000)
    rs=self.c.post('/api/v1/id/0:3?'+suffix)
    self.helperDataCheck(rs, state, err, portid=0, sessionid=3)

    suffix='s_ip={}&s_port={}&d_ip={}&d_port={}'.format(
                              '10.cd.0.1', 6000, '0.0.1', 7000)
    rs=self.c.post('/api/v1/id/0:3?'+suffix)
    self.helperDataCheck(rs, state, err, portid=0, sessionid=3)

    suffix='s_ip={}&s_port={}&d_ip={}&d_port={}'.format(
                              3000, 6000, '0.0.1', 7000)
    self.helperDataCheck(rs, state, err, portid=0, sessionid=3)

  def test_apiid_put(self):
    portid, sessionid=(0, 3)
    s_ip='192.168.0.1'; s_port=5000; src=(s_ip, s_port)
    s_ip='192.168.0.1'; s_port=5000; src=(s_ip, s_port)
    d_ip='172.16.0.1' ; d_port=8000; dst=(d_ip, d_port)
    tmstmp=random.randint(0,0xffffffff)
    rscmap.addrsc(portid, sessionid, src, dst, tmstmp)

    self.stubServerLaunch(self.helperCreateSuccessMsg(portid,sessionid))
    connectServer(self.target)
    
    s_ip='10.0.0.1'; s_port=9000; src=(s_ip, s_port)
    suffix='s_ip={}&s_port={}&d_ip={}&d_port={}'.format(s_ip, s_port, d_ip, d_port)
    rs=self.c.put('/api/v1/id/0:3?'+suffix)
    state=200; err=None; enabled=True
    self.helperDataCheck(rs, state, err, portid, sessionid, enabled, tmstmp, src, dst)

  def test_apiid_put_id_notfound(self):
    portid, sessionid=(0, 3)
    s_ip='192.168.0.1'; s_port=5000; src=(s_ip, s_port)
    s_ip='192.168.0.1'; s_port=5000; src=(s_ip, s_port)
    d_ip='172.16.0.1' ; d_port=8000; dst=(d_ip, d_port)
    tmstmp=random.randint(0,0xffffffff)
    rscmap.addrsc(portid, sessionid, src, dst, tmstmp)
    
    self.stubServerLaunch(self.helperCreateSuccessMsg(portid,sessionid))
    connectServer(self.target)
    
    s_ip='10.0.0.1'; s_port=9000; src=(s_ip, s_port)
    suffix='s_ip={}&s_port={}&d_ip={}&d_port={}'.format(s_ip, s_port, d_ip, d_port)
    rs=self.c.put('/api/v1/id/0:4?'+suffix)
    state=404; err='port id {} : session id {} does not active'.format(0,4)
    self.helperDataCheck(rs, state, err, portid, sessionid=4)

  def test_apiid_post_get_del_post_get(self):
    portid, sessionid=(0, 3)
    s_ip='192.168.0.1'; s_port=5000; src=(s_ip, s_port)
    s_ip='192.168.0.1'; s_port=5000; src=(s_ip, s_port)
    d_ip='172.16.0.1' ; d_port=8000; dst=(d_ip, d_port)

    self.stubServerLaunch(self.helperCreateSuccessMsg(portid,sessionid),loop=3)
    connectServer(self.target)
    
    suffix='s_ip={}&s_port={}&d_ip={}&d_port={}'.format(s_ip, s_port, d_ip, d_port)
    rs=self.c.post('/api/v1/id/0:3?'+suffix)
    state=200; err=None; enabled=True
    self.helperDataCheck(rs, state, err, portid, sessionid, enabled, None, src, dst)

    rs=self.c.get('/api/v1/id/0:3')
    state=200; err=None; enabled=True
    self.helperDataCheck(rs, state, err, portid, sessionid, enabled, None, src, dst)
    
    rs=self.c.delete('/api/v1/id/0:3')
    state=200; err=None; enabled=False
    self.helperDataCheck(rs, state, err, portid, sessionid, enabled, None, src, dst)

    suffix='s_ip={}&s_port={}&d_ip={}&d_port={}'.format(s_ip, s_port, d_ip, d_port)
    rs=self.c.post('/api/v1/id/0:3?'+suffix)
    state=200; err=None; enabled=True
    self.helperDataCheck(rs, state, err, portid, sessionid, enabled, None, src, dst)

    rs=self.c.get('/api/v1/id/0:3')
    state=200; err=None; enabled=True
    self.helperDataCheck(rs, state, err, portid, sessionid, enabled, None, src, dst)

  def helperDataCheck(self, rs, status_code, error, portid, sessionid,
                      enabled=None, timestamp=None, src=None, dst=None):

    data=json.loads(rs.data.decode('utf-8'))
    self.assertEqual(rs.content_type, 'application/json')
    if 'error' in data: self.assertEqual(data['error'], error)
    self.assertEqual(rs.status_code, status_code)

    if 'state' in data:
      self.assertNotEqual(data['state'], None)
    if enabled:
      self.assertEqual(data['state']['enabled'], enabled)
    if timestamp:
      self.assertEqual(data['state']['start_timestamp'], timestamp)
    if src:
      s_ip, s_port=src; 
      self.assertEqual(data['state']['src']['ip'], s_ip)
      self.assertEqual(data['state']['src']['port'], s_port)
    if dst:
      d_ip, d_port=dst
      self.assertEqual(data['state']['dst']['ip'], d_ip)
      self.assertEqual(data['state']['dst']['port'], d_port)
    self.assertEqual(data['session_id'], sessionid)
    self.assertEqual(data['port_id'], portid)
    self.assertEqual(data['result'], status_code)

  def helperCreateSuccessMsg(self, portid, sessionid):
    expectmsg=pb.RtpgenIPCmsgV1()
    expectmsg.response_code=pb.RtpgenIPCmsgV1.SUCCESS
    expectmsg.portid=portid
    expectmsg.id_selector=sessionid
    return expectmsg


class TestResourceMapManager(unittest.TestCase):

  def setUp(self):
    self.target=('127.0.0.1',43991)
    self.server=None
    self.th=None
    self.rsc=ResourceMapManager()

  def tearDown(self):
    if self.server:
      try:
        self.server.shutdown(socket.SHUT_RDWR)
      except OSError:
        pass
      self.server.close()
    if self.th:
      self.th.join()
    self.rsc=None

  def msgReadSuccess(self):
    msg=pb.RtpgenIPCmsgV1()
    msg.response_code=pb.RtpgenIPCmsgV1.SUCCESS
    msg.portid=1
    msg.id_selector=2
    msg.rtp_config.ip_dst_addr=4
    msg.rtp_config.ip_src_addr=5
    msg.rtp_config.udp_dst_port=6
    msg.rtp_config.udp_src_port=7
    msg.rtp_config.rtp_timestamp=8
    msg.rtp_config.rtp_sequence=9
    msg.rtp_config.rtp_ssrc=10
    return msg

  def msgWriteSuccess(self):
    msg=pb.RtpgenIPCmsgV1()
    msg.response_code=pb.RtpgenIPCmsgV1.SUCCESS
    return msg

  def appendMap(self):
    rsc=self.rsc.resourceMap
    for portid in range(1,254):
      for sessionid in range(1,254):
        if not portid in rsc:
          rsc[portid]={}
        rsc[portid][sessionid]={
          "enabled":True,
          "src":{"ip":"192.168.{}.{}".format(portid,sessionid),"port":portid},
          "dst":{"ip":"192.168.{}.{}".format(sessionid,portid),"port":sessionid},
          "start_timestamp":random.randint(0,0xffffffff)
        }

  def test_addrsc(self):
    portid=43
    sessionid=123
    src=("192.168.0.1", 5006)
    dst=("192.168.9.9", 8831)
    timestamp=random.randint(0,0xffffffff)
    self.assertIsNotNone(self.rsc.addrsc(portid, sessionid, src, dst, timestamp))
    self.assertEqual(self.rsc.resourceMap[portid][sessionid]["enabled"],True)
    self.assertEqual(self.rsc.resourceMap[portid][sessionid]["src"]["ip"], '192.168.0.1')
    self.assertEqual(self.rsc.resourceMap[portid][sessionid]["src"]["port"], 5006)
    self.assertEqual(self.rsc.resourceMap[portid][sessionid]["dst"]["ip"], '192.168.9.9')
    self.assertEqual(self.rsc.resourceMap[portid][sessionid]["dst"]["port"], 8831)
    self.assertEqual(self.rsc.resourceMap[portid][sessionid]["start_timestamp"], timestamp)

  def test_addrsc_error(self):
    self.appendMap()
    portid=43
    sessionid=123
    src=("192.168.0.1", 5006)
    dst=("192.168.9.9", 8831)
    timestamp=random.randint(0,0xffffffff)
    self.assertIsNone(self.rsc.addrsc(portid, sessionid, src, dst, timestamp))

  def test_putrsc(self):
    self.appendMap()
    portid=43
    sessionid=123
    src=("192.168.0.1", 5006)
    dst=("192.168.9.9", 8831)
    timestamp=random.randint(0,0xffffffff)
    self.assertEqual(self.rsc.resourceMap[portid][sessionid]["enabled"],True)
    self.assertEqual(self.rsc.resourceMap[portid][sessionid]["src"]["ip"],'192.168.43.123')
    self.assertEqual(self.rsc.resourceMap[portid][sessionid]["src"]["port"],43)
    self.assertEqual(self.rsc.resourceMap[portid][sessionid]["dst"]["ip"],'192.168.123.43')
    self.assertEqual(self.rsc.resourceMap[portid][sessionid]["dst"]["port"],123)
    self.assertIsNotNone(self.rsc.putrsc(portid, sessionid, src, dst, timestamp))
    self.assertEqual(self.rsc.resourceMap[portid][sessionid]["enabled"],True)
    self.assertEqual(self.rsc.resourceMap[portid][sessionid]["src"]["ip"],'192.168.0.1')
    self.assertEqual(self.rsc.resourceMap[portid][sessionid]["src"]["port"],5006)
    self.assertEqual(self.rsc.resourceMap[portid][sessionid]["dst"]["ip"],'192.168.9.9')
    self.assertEqual(self.rsc.resourceMap[portid][sessionid]["dst"]["port"],8831)
    self.assertEqual(self.rsc.resourceMap[portid][sessionid]["start_timestamp"], timestamp)

  def test_putrsc_error(self):
    portid=43
    sessionid=123
    src=("192.168.0.1", 5006)
    dst=("192.168.9.9", 8831)
    self.assertIsNone(self.rsc.putrsc(portid, sessionid, src, dst))

  def test_delrsc(self):
    self.appendMap()
    portid=43
    sessionid=123
    self.assertEqual(self.rsc.resourceMap[portid][sessionid]["enabled"],True)
    self.assertEqual(self.rsc.resourceMap[portid][sessionid]["src"]["ip"],'192.168.43.123')
    self.assertEqual(self.rsc.resourceMap[portid][sessionid]["src"]["port"],43)
    self.assertEqual(self.rsc.resourceMap[portid][sessionid]["dst"]["ip"],'192.168.123.43')
    self.assertEqual(self.rsc.resourceMap[portid][sessionid]["dst"]["port"],123)
    self.assertIsNotNone(self.rsc.delrsc(portid, sessionid))
    self.assertEqual(self.rsc.resourceMap[portid][sessionid]["enabled"],False)

  def test_delrsc_error(self):
    portid=43
    sessionid=123
    self.assertIsNone(self.rsc.delrsc(portid, sessionid))
    
  def test_srchrsc(self):
    self.appendMap()
    src=("192.168.93.231", 93)
    dst=("192.168.231.93", 231)
    portid, sessionid = self.rsc.srchrsc(src, dst)
    self.assertIsNotNone(portid)
    self.assertIsNotNone(sessionid)
    self.assertEqual(self.rsc.resourceMap[portid][sessionid]["enabled"],True)
    self.assertEqual(self.rsc.resourceMap[portid][sessionid]["src"]["ip"],'192.168.93.231')
    self.assertEqual(self.rsc.resourceMap[portid][sessionid]["src"]["port"],93)
    self.assertEqual(self.rsc.resourceMap[portid][sessionid]["dst"]["ip"],'192.168.231.93')
    self.assertEqual(self.rsc.resourceMap[portid][sessionid]["dst"]["port"],231)

  def test_srchrsc_error(self):
    self.appendMap()
    src=("192.168.92.231", 93)
    dst=("192.168.231.93", 231)
    portid, sessionid = self.rsc.srchrsc(src, dst)
    self.assertIsNone(portid)
    self.assertIsNone(sessionid)
    
  def test_getrsc(self):
    self.appendMap()
    portid=93
    sessionid=231
    ret=self.rsc.getrsc(portid, sessionid)
    self.assertIsNotNone(ret)
    self.assertEqual(ret["enabled"],True)
    self.assertEqual(ret["src"]["ip"],'192.168.93.231')
    self.assertEqual(ret["src"]["port"],93)
    self.assertEqual(ret["dst"]["ip"],'192.168.231.93')
    self.assertEqual(ret["dst"]["port"],231)

  def test_getrsc_error(self):
    self.appendMap()
    portid=283
    sessionid=231
    self.assertIsNone(self.rsc.getrsc(portid, sessionid))

