#!/usr/bin/env python3.6
# -*- coding:utf-8 -*-

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
  def setUp(self): pass

  def tearDown(self):
    pass


