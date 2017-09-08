import boto.ec2

def get_instances_by_auto_scaling_group (name, status = None):
	return get_instances_by_tag ("aws:autoscaling:groupName", name, status)	

def get_instances_by_tag (name, key = None, status = None, region = 'us-east-1'):
	fl = {'tag:' + name: key}
	conn = boto.ec2.connect_to_region (region)
	reservations = conn.get_all_instances (filters = fl)
	if not reservations:
		return []
	instances = [r.instances [0] for r in reservations]
	if status:
		return [i for i in instances if i.update () == status]
	return instances

def get_instance_by_id (instance_id, region = 'us-east-1'):
	conn = boto.ec2.connect_to_region (region)
	reservations = conn.get_all_instances ([instance_id])
	if not reservations:
		return []
	instances = reservations [0].instances
	return instances [0]
