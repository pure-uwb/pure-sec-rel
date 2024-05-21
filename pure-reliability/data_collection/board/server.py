#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import logging
import signal
import sys
import json
from datetime import datetime
import argparse

sys.path.append(f'{os.getcwd()}/monitor/dwm3000')
from HDF5Storage import HDF5Storage

storage = HDF5Storage(filename="phone_report.hdf5.tmp")

def signal_handler(sig, frame):
    logging.info("Exit!")
    storage.save_buffer_to_file()    
    sys.exit(0)



class S(BaseHTTPRequestHandler):
    post_counter = 0
    def _set_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        logging.info("GET request,\nPath: %s\nHeaders:\n%s\n", str(self.path), str(self.headers))
        self._set_response()
        self.wfile.write("GET request for {}".format(self.path).encode('utf-8'))

    def do_POST(self):
        S.post_counter += 1
        content_length = int(self.headers['Content-Length']) # <--- Gets the size of data
        post_data = self.rfile.read(content_length) # <--- Gets the data itself
        logging.info("\nPOST request %s,\nBody:\n%s\n",
                str(S.post_counter), post_data.decode('utf-8'))
        try:
            storage.save_to_buffer(json.loads(post_data.decode('utf-8')))
        except:
            logging.error(f"Failed to decode {post_data}")
        self._set_response()
        #self.wfile.write("POST request for {}".format(self.path).encode('utf-8'))

def run(server_class=HTTPServer, handler_class=S, port=9000, log=False):
    if log:
        #LOG_FILENAME = datetime.now().strftime("measures_server" + "_%H_%M_%S_%d_%m_%Y.log")
        LOG_FILENAME = "measures_server.log"
        logging.basicConfig(filename = "/tmp/" + LOG_FILENAME, filemode = "w+",  level=logging.INFO)
    else:
        logging.basicConfig(level=logging.INFO)
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    logging.info('Starting httpd...\n')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info('Stopping httpd...\n')

if __name__ == '__main__':
    from sys import argv
    
    signal.signal(signal.SIGINT, signal_handler)
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--log', action='store_true', help = "Flag to set output to log file")  
    parser.add_argument('-p', '--port', action='store', type=int, default=9000)
    args = parser.parse_args()
    run(port=args.port, log = args.log)
