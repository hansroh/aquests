import boto.ec2
import time
from boto.ec2.elb import ELBConnection
from . import iquery, metrics

class LoadBalancer:
	def __init__ (self, name, region = "us-east-1"):
		self.name = name
		self.region = region
		self.conn = boto.ec2.connect_to_region (region)
		self.image_id = None
		
	def create_instance (self, param):
		self.image_id = param ['image_id']		
		param ['monitoring_enabled'] = False
		param ['monitoring_enabled'] = False
		param ['dry_run'] = False
	
		reservation = self.conn.run_instances (**param)
		instance = reservation.instances [0]
		while instance.update() == 'pending':
			print ('waiting...')
			time.sleep(10)	
		
		status = instance.update()
		if status == 'running':
			instance.add_tag("Name", self.name + "-" + self.image_id [4:])
			instance.add_tag("ami-id", self.image_id)
			instance.add_tag("system", "skitai")
		else:
			print('instance status: ' + status)		
		
		return instance
			
	def register_to_elb (self, instance_id):
		elb = ELBConnection()
		elb.register_instances (self.name, instance_id)
	
	def deregister_to_elb (self, instance_id):
		elb = ELBConnection()
		elb.deregister_instances (self.name, instance_id)
			
	def terminate (self, instance_id):
		instance = iquery.get_instance_by_id (instance_id)
		instance.terminate ()
	
	def get_instance_id (self):
		instance = [i for i in iquery.get_instances_by_tag ("system", 'skitai') if i.update () == "running"][0]
		instance = iquery.get_instance_by_id (instance.id)
		return instance.id
	
	def get_status (self):
		g = {}
		for h in self.get_health ():
			g [h.instance_id] = (h.state, metrics.get_latest (h.instance_id))
		return g
	
	def get_health (self):
		elb = ELBConnection()
		this = elb.get_all_load_balancers ([self.name])[0]
		return this.get_instance_health ()			
		
	def get_instance_ids (self):
		return [h.instance_id for h in self.get_health ()]
