#!/usr/bin/env python3.6
# -*- coding:utf-8 -*-

import random
import unittest
import os
import json
import logging as log
import socket
import werkzeug.exceptions 
from time import time, sleep
from threading import Thread
from logging import getLogger, Formatter, StreamHandler
from flask import Flask, request, jsonify

import protolib.ipc_pack_pb2 as pb
import protolib.sb_api as sbapi

''' ENVIROMENT VARIABLEs '''
api_ip     =   os.getenv("API_IP"    , "0.0.0.0"  )
api_port     = int(os.getenv("API_PORT"    , 5000    ))
loglevel     = int(os.getenv("LOGLEVEL"    , log.DEBUG   ))
audio_file   =   os.getenv("AUDIO_FILE"  , None     )

''' global variables '''
app = Flask(__name__)
logger = getLogger(__name__)


class RtpgenRestGW(object):
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

  def getrsc(self, portid, sessionid):
    rsc=self.resourceMap
    if not portid in rsc or not sessionid in rsc[portid]:
      return None
    return rsc[portid][sessionid]

  def srchrsc(self, src, dst):
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
  
  def addrsc(self, portid, sessionid, src, dst):
    rsc=self.resourceMap
    if not portid in rsc:
      rsc[portid]={}
    if sessionid in rsc[portid]:
      return None
    sip, sport = src
    dip, dport = dst
    timesatmp=random.randint(0,0xffffffff)
    rsc[portid][sessionid]={
      "enabled":True,
      "src":{"ip":sip,"port":sport},
      "dst":{"ip":dip,"port":dport},
      "start_timestamp":timesatmp
    }
    return rsc[portid][sessionid]
  
  def putrsc(self, portid, sessionid, src, dst):
    rsc=self.resourceMap
    if not portid in rsc or not sessionid in rsc[portid]:
      return None
    sip, sport = src
    dip, dport = dst
    rsc[portid][sessionid]["src"]["ip"  ]=sip
    rsc[portid][sessionid]["src"]["port"]=sport
    rsc[portid][sessionid]["dst"]["ip"  ]=dip
    rsc[portid][sessionid]["dst"]["port"]=dport
    return rsc[portid][sessionid]
  
  def delrsc(self, portid, sessionid):
    rsc=self.resourceMap
    if not portid in rsc or not sessionid in rsc[portid]:
      return None
    rsc[portid][sessionid]["enabled"]=False
    return rsc[portid][sessionid]


''' API Call '''
@app.route('/api/v1/resources/<srcIP>:<srcPort>/<destIP>:<destPort>',
    methods=['POST','GET','DELETE'])
def rsc(destIP,destPort,srcIP,srcPort):
  retCode=200
  result={}
  try:
    destPort=int(destPort)
    srcPort=int(srcPort)
    if request.method in ['POST']: # ADD
      pass
    elif request.method in ['GET','DELETE']:
      pass
    result['id']=cic
  except ValueError as e:
    retCode=400
    result['error']='input is not a number'
  except TypeError as e:
    retCode=400
    result['error']=e.__str__()
  except Exception as e:
    if retCode==200:
      retCode=500
    result['error']=e.__str__()
  result['result']=retCode

  return jsonify(result), retCode

def returnErrorContent(code, reason):
  return jsonify({'result':code,'error':reason}), code

@app.errorhandler(400)
@app.errorhandler(401)
@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(405)
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

''' main logic '''
def main():
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

  th.join()
  logger.info('server termsinating...')

if __name__ == '__main__':
  main()

''' Unit Test Cases '''
class TestRtpGen_RESTGW(unittest.TestCase):
  restgw=None
  def setUp(self):
    self.restgw=RtpgenRestGW()

  def tearDown(self):
    self.restgw=None

  def appendMap(self):
    rsc=self.restgw.resourceMap
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
    self.assertIsNotNone(self.restgw.addrsc(portid, sessionid, src, dst))
    self.assertEqual(self.restgw.resourceMap[portid][sessionid]["enabled"],True)
    self.assertEqual(self.restgw.resourceMap[portid][sessionid]["src"]["ip"],'192.168.0.1')
    self.assertEqual(self.restgw.resourceMap[portid][sessionid]["src"]["port"],5006)
    self.assertEqual(self.restgw.resourceMap[portid][sessionid]["dst"]["ip"],'192.168.9.9')
    self.assertEqual(self.restgw.resourceMap[portid][sessionid]["dst"]["port"],8831)

  def test_addrsc_error(self):
    self.appendMap()
    portid=43
    sessionid=123
    src=("192.168.0.1", 5006)
    dst=("192.168.9.9", 8831)
    self.assertIsNone(self.restgw.addrsc(portid, sessionid, src, dst))

  def test_putrsc(self):
    self.appendMap()
    portid=43
    sessionid=123
    src=("192.168.0.1", 5006)
    dst=("192.168.9.9", 8831)
    self.assertEqual(self.restgw.resourceMap[portid][sessionid]["enabled"],True)
    self.assertEqual(self.restgw.resourceMap[portid][sessionid]["src"]["ip"],'192.168.43.123')
    self.assertEqual(self.restgw.resourceMap[portid][sessionid]["src"]["port"],43)
    self.assertEqual(self.restgw.resourceMap[portid][sessionid]["dst"]["ip"],'192.168.123.43')
    self.assertEqual(self.restgw.resourceMap[portid][sessionid]["dst"]["port"],123)
    self.assertIsNotNone(self.restgw.putrsc(portid, sessionid, src, dst))
    self.assertEqual(self.restgw.resourceMap[portid][sessionid]["enabled"],True)
    self.assertEqual(self.restgw.resourceMap[portid][sessionid]["src"]["ip"],'192.168.0.1')
    self.assertEqual(self.restgw.resourceMap[portid][sessionid]["src"]["port"],5006)
    self.assertEqual(self.restgw.resourceMap[portid][sessionid]["dst"]["ip"],'192.168.9.9')
    self.assertEqual(self.restgw.resourceMap[portid][sessionid]["dst"]["port"],8831)

  def test_putrsc_error(self):
    portid=43
    sessionid=123
    src=("192.168.0.1", 5006)
    dst=("192.168.9.9", 8831)
    self.assertIsNone(self.restgw.putrsc(portid, sessionid, src, dst))

  def test_delrsc(self):
    self.appendMap()
    portid=43
    sessionid=123
    self.assertEqual(self.restgw.resourceMap[portid][sessionid]["enabled"],True)
    self.assertEqual(self.restgw.resourceMap[portid][sessionid]["src"]["ip"],'192.168.43.123')
    self.assertEqual(self.restgw.resourceMap[portid][sessionid]["src"]["port"],43)
    self.assertEqual(self.restgw.resourceMap[portid][sessionid]["dst"]["ip"],'192.168.123.43')
    self.assertEqual(self.restgw.resourceMap[portid][sessionid]["dst"]["port"],123)
    self.assertIsNotNone(self.restgw.delrsc(portid, sessionid))
    self.assertEqual(self.restgw.resourceMap[portid][sessionid]["enabled"],False)

  def test_delrsc_error(self):
    portid=43
    sessionid=123
    self.assertIsNone(self.restgw.delrsc(portid, sessionid))
    
  def test_srchrsc(self):
    self.appendMap()
    src=("192.168.93.231", 93)
    dst=("192.168.231.93", 231)
    portid, sessionid = self.restgw.srchrsc(src, dst)
    self.assertIsNotNone(portid)
    self.assertIsNotNone(sessionid)
    self.assertEqual(self.restgw.resourceMap[portid][sessionid]["enabled"],True)
    self.assertEqual(self.restgw.resourceMap[portid][sessionid]["src"]["ip"],'192.168.93.231')
    self.assertEqual(self.restgw.resourceMap[portid][sessionid]["src"]["port"],93)
    self.assertEqual(self.restgw.resourceMap[portid][sessionid]["dst"]["ip"],'192.168.231.93')
    self.assertEqual(self.restgw.resourceMap[portid][sessionid]["dst"]["port"],231)

  def test_srchrsc_error(self):
    self.appendMap()
    src=("192.168.92.231", 93)
    dst=("192.168.231.93", 231)
    portid, sessionid = self.restgw.srchrsc(src, dst)
    self.assertIsNone(portid)
    self.assertIsNone(sessionid)
    
  def test_getrsc(self):
    self.appendMap()
    portid=93
    sessionid=231
    ret=self.restgw.getrsc(portid, sessionid)
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
    self.assertIsNone(self.restgw.getrsc(portid, sessionid))
