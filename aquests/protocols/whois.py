from rs4 import asyncore
import socket

class WhoisRequest(asyncore.dispatcher_with_send):
    # simple whois requestor

    def __init__(self, consumer, query, host, port=43):
        asyncore.dispatcher_with_send.__init__(self)

        self.consumer = consumer
        self.query = query

        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect((host, port))

    def handle_connect(self):
        self.send(self.query.encode ("utf8") + b"\r\n")

    def handle_expt(self):
        self.close() # connection failed, shutdown
        self.consumer.abort()

    def handle_read(self):
        # get data from server
        self.consumer.feed(self.recv(2048))

    def handle_close(self):
        self.close()
        self.consumer.close()

class WhoisConsumer:

    def __init__(self, host):
        self.text = ""
        self.host = host

    def feed(self, text):
        self.text = self.text + text

    def abort(self):
        print(self.host, "=>", "failed")

    def close(self):
        print(self.host, "=>")
        print(self.text)

#
# try it out
for host in []:
    consumer = WhoisConsumer(host)
    request = WhoisRequest(consumer, host, "whois.internic.net")

# loop returns when all requests have been processed
asyncore.loop()
