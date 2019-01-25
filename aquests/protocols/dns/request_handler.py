from .pydns import Base, Type, Class, Lib, Opcode
defaults = Base.defaults
        
class RequestHandler:
    def __init__(self, lock, logger, client_getter):
        self.lock = lock 
        self.logger = logger
        self.client_getter = client_getter
        self.id = 0
        
    def get_id (self):
        with self.lock:
            self.id += 1
            if self.id == 32768:
                self.id = 1    
            return self.id
        
    def argparse (self, name, args):
        args['name'] = name
        if 'errors' not in args:
            args ['errors'] = []
            
        for i in list(defaults.keys()):
            if i not in args:
                args[i]=defaults[i]
        return args
        
    def handle_request (self, name, **args):
        if isinstance (name, str):
            name = name.encode ("utf8")
        args = self.argparse (name, args)

        protocol = args ['protocol']
        opcode = args ['opcode']
        rd = args ['rd']
        
        if type(args['qtype']) in (bytes, str):
            try:
                qtype = getattr (Type, args ['qtype'].upper ())
            except AttributeError:
                raise Base.DNSError('%s unknown query type' % name)
                
        else:
            qtype = args ['qtype']
            
        qname = args ['name']        
        m = Lib.Mpacker()        
        m.addHeader(self.get_id (),
              0, opcode, 0, 0, rd, 0, 0, 0,
              1, 0, 0, 0)
        
        m.addQuestion (qname, qtype, Class.IN)
        request = m.getbuf ()
        
        conn = self.client_getter (args.get ('addr'), args ['protocol'])
        conn.query (request, args, self.process_reply)
        
    def process_reply (self, args, data, timeouted):        
        err = None
        answers = []
        qname = args ['name'].decode ('utf8')
        
        if timeouted:
            err = 'timeout'            
        else:    
            try:
                if not data:
                    err = "no-reply"                    
                else:    
                    if args ["protocol"] == "tcp":
                        header = data [:2]
                        if len (header) < 2:
                            err = 'EOF-invalid-header' % qname
                        count = Lib.unpack16bit(header)
                        reply = data [2: 2 + count]
                        if len (reply) != count:
                            err = "incomplete-reply"                    
                    else:
                        reply = data
                    
            except:
                self.logger.trace ()
                err = 'exception'    
            
            if not err:
                try:    
                    u = Lib.Munpacker(reply)
                    r = Lib.DnsResult(u, args)
                    r.args = args
                    if r.header ['tc']:
                        err = 'truncate'
                        args ['protocol'] = 'tcp'
                        self.logger ('%s, trucated switch to TCP' % qname, 'warn')
                        
                    else:
                        if r.header ['status'] != 'NOERROR':
                            self.logger ('%s, status %s' % (qname, r.header ['status']), 'warn')
                            answers = [{"name": qname, "data": None, "status":  r.header ['status']}]
                        else:    
                            answers = r.answers
                            
                except:
                    self.logger.trace ()
        
        if err:
            if len (args ['errors']) < 2:
                args ['errors'].append (err)
                # switch protocol
                args ['protocol'] = args ['protocol'] == "tcp" and "udp" or "tcp"
                query (**args)
                return
            
            self.logger ('%s, DNS %s errors' % (qname, args ['errors']), 'warn')        
            answers = [{"name": qname, "data": None, "error": err}] 
        
        callback = args.get ("callback", None)
        if callback:
            if type (callback) != type ([]):
                callback = [callback]
            for cb in callback:                
                cb (answers)
        