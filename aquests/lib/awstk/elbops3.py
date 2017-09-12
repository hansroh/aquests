import boto3
import datetime
import time
from botocore.exceptions import ClientError

ec2 = boto3.resource ('ec2')
elb = boto3.client('elb')
cw = boto3.client('cloudwatch')
elb2 = boto3.client('elbv2')

PREF = {
	'CPUUtilization': ('Average', 'Percent'),
	'CPUCreditBalance': ('Average', 'Count'),
	'CPUCreditUsage': ('Average', 'Count'),		
	'DiskReadBytes': ('Average', 'Bytes'),
	'DiskReadOps': ('Sum', 'Bytes'),
	'DiskWriteBytes': ('Average', 'Bytes'),
	'DiskWriteOps': ('Sum', 'Bytes'),		
	'NetworkIn': ('Maximum', 'Bytes'),
	'NetworkOut': ('Maximum', 'Bytes'),
}

class ELBOps:
	def __init__ (self, system, image_id, region = "us-east-1"):
		self.system = system
		self.image_id = image_id
		self.region = region
		
	def get_metric (self, instance_id, metric = 'CPUUtilization'):
		Statistics, Unit = PREF [metric]
		s = cw.get_metric_statistics(       
			Period = 300,
			StartTime = datetime.datetime.utcnow() - datetime.timedelta(seconds=1200),
			EndTime = datetime.datetime.utcnow(),
			MetricName = metric,
			Namespace = 'AWS/EC2',
			Statistics = [Statistics],
			Unit = Unit,
			Dimensions = [{'Name':'InstanceId', 'Value': instance_id}]
		)	
		return [p [Statistics] for p in s ["Datapoints"][:3]]
	
	def create_instance (self, itype, user_data):
		instances = ec2.create_instances (
			ImageId=self.image_id,
			MinCount = 1, 
			MaxCount = 1,
			InstanceType = itype,
			Monitoring = {'Enabled': False},
			SecurityGroups = ['default', '%s-app' % self.system],
			UserData = user_data,
			DryRun=False,
			IamInstanceProfile = {'Name': 'app'},
			InstanceInitiatedShutdownBehavior = 'terminate',
			TagSpecifications = [
				{
					'ResourceType': 'instance',
					'Tags': [
							{'Key': 'Name', 'Value': '%s-app-%s' % (self.system, self.image_id [4:])},
							{'Key': 'system', 'Value': self.system},						
					]
				},
		  ]
		)
		instance = instances [0]
		instance.wait_until_running ()
		return instance.id
		
	def stop (self, *ids):
		self.elb_exists () and self.deregister_instances (*ids)
		ec2.instances.filter(InstanceIds=ids).stop()
	
	def terminate (self, *ids):
		self.elb_exists () and self.deregister_instances (*ids)
		ec2.instances.filter(InstanceIds=ids).terminate()
	
	def find_instances_by_image (self, image_id = None):
		return ec2.instances.filter(
			Filters=[{'Name': 'tag:Name', 'Values': ['%s-app-%s' % (
				self.system, (image_id or self.image_id) [4:]
			)]}]
		)
				
	def find_instances (self):
		return ec2.instances.filter(Filters=[{'Name': 'tag:system', 'Values': [self.system]}])		
		
	def describe_instance_status (self):
		for status in ec2.meta.client.describe_instance_status()['InstanceStatuses']:
			print(status)
	
	def register_instances2 (self, arn, port = 80, *ids):
		elb2.register_targets (
			TargetGroupArn = arn,
			Targets = [{'Id': i, 'Port': port} for i in ids]
		)
	
	def deregister_instances2 (self, arn, port = 80, *ids):
		elb2.deregister_targets (
			TargetGroupArn = arn,
			Targets = [{'Id': i, 'Port': port} for i in ids]
		)
	
	def register_instances (self, *ids):
		elb.register_instances_with_load_balancer(
			LoadBalancerName='%s-app' % self.system,
			Instances=[{'InstanceId': i} for i in ids]
		)
	
	def deregister_instances (self, *ids):
		elb.deregister_instances_from_load_balancer(
			LoadBalancerName='%s-app' % self.system,
			Instances=[{'InstanceId': i} for i in ids]
		)
	
	def create_elb (self, security_groups):
		elb.create_load_balancer (
			LoadBalancerName = '%s-app' % self.system,
			AvailabilityZones = [self.region + 'a', self.region + 'b', self.region + 'c', self.region + 'd', self.region + 'e', self.region + 'f'],
			SecurityGroups = security_groups,
			Tags=[{'Key': 'system', 'Value': self.system }],
			Listeners=[
        {
            'Protocol': 'HTTP',
            'LoadBalancerPort': 80,
            'InstanceProtocol': 'HTTP',
            'InstancePort': 80            
        },
        {
            'Protocol': 'HTTP',
            'LoadBalancerPort': 5000,
            'InstanceProtocol': 'HTTP',
            'InstancePort': 5000            
        }
    	],
		)
	
	def delete_elb (self):	
		elb.delete_load_balancer (
			LoadBalancerName = '%s-app' % self.system
		)
		
	def elb_exists (self):
		try:
			self.elb_health ()
		except ClientError as e:
			if e.response['Error']['Code'] == "LoadBalancerNotFound":
				return 0
			raise
		return 1	
			
	def elb_health (self):
		h =  elb.describe_instance_health (LoadBalancerName = '%s-app' % self.system)
		return dict ([(i ['InstanceId'], i ['State']) for i in h ["InstanceStates"]])
	
	def create (self, instance_type = 't2.nano', user_data = None):
		instance_id = self.create_instance (instance_type, user_data)
		self.register_instances (instance_id)
