import time
import boto.ec2
import boto.ec2.autoscale
from boto.ec2.autoscale import LaunchConfiguration
from boto.ec2.autoscale import AutoScalingGroup
from boto.ec2.autoscale import ScalingPolicy
import boto.ec2.cloudwatch
from . import iquery, metrics

class AutoScaler:	
	def __init__ (self, name, region = 'us-east-1'):
		self.name = name
		self.region = region
		self.launch_config = None
		self.as_group = None
		self.conn = boto.ec2.autoscale.connect_to_region(self.region)
		
	def create_launch_config (self, param):		
		if len (self.conn.get_all_launch_configurations (names = [self.name])):
			print ('launch configuration already exists')
			return	
		param ["name"] = self.name
		lc = LaunchConfiguration(**param)
		self.conn.create_launch_configuration (lc)
		self.launch_config = lc
		
	def create_auto_scaling_group (self, min_size = 1, max_size = 2):		
		if len (self.conn.get_all_groups (names = [self.name])):
			print ('auto-scaling group already exists')
			return			
		
		if self.launch_config is None:
			try:
				self.launch_config = self.conn.get_all_launch_configurations (names = [self.name])[0]
			except IndexError:
				print ('launch configuration not exists')
				return
			
		self.as_group = AutoScalingGroup(
			group_name=self.name,
			load_balancers=['skitai-app'],
			availability_zones=[self.region + 'a', self.region + 'b', self.region + 'c', self.region + 'd', self.region + 'e', self.region + 'f'],
			launch_config = self.launch_config, 
			min_size = min_size, 
			max_size = max_size,
			connection = self.conn
		)
		self.conn.create_auto_scaling_group (self.as_group)		
	
	def make_policies (self):
		scale_up_policy = ScalingPolicy(
			name='scale-up', adjustment_type='ChangeInCapacity',
			as_name=self.name, scaling_adjustment=1, cooldown=180
		)
		scale_down_policy = ScalingPolicy(
			name='scale-down', adjustment_type='ChangeInCapacity',
			as_name=self.name, scaling_adjustment=-1, cooldown=180
		)
		self.conn.create_scaling_policy(scale_up_policy)
		self.conn.create_scaling_policy(scale_down_policy)

	def get_policies (self):
		scale_up_policy = self.conn.get_all_policies (
			as_group=self.name, policy_names=['scale-up'])[0]            
		scale_down_policy = self.conn.get_all_policies (
			as_group=self.name, policy_names=['scale-down'])[0]
		return scale_up_policy, scale_down_policy

	def create_cpu_alram (self, low = 40, high = 70):
		cloudwatch = boto.ec2.cloudwatch.connect_to_region(self.region)
		alarm_dimensions = {"AutoScalingGroupName": self.name}	
		scale_up_policy, scale_down_policy = self.get_policies ()
		
		alarm = metrics.create_alram (
			'%s-scale-up-on-cpu' % self.name,
			'CPUUtilization',	'>', str (high),
			alarm_dimensions,
			scale_up_policy.policy_arn
		)
		cloudwatch.create_alarm (alarm)
		
		alarm = metrics.create_alram (
			'%s-scale-down-on-cpu' % self.name,
			'CPUUtilization',	'<', str (low),		
			alarm_dimensions,
			scale_down_policy.policy_arn		
		)
		cloudwatch.create_alarm (alarm)
	
	def create_credit_alram (self, low = 20, high = 60):
		cloudwatch = boto.ec2.cloudwatch.connect_to_region(self.region)
		alarm_dimensions = {"AutoScalingGroupName": self.name}	
		scale_up_policy, scale_down_policy = self.get_policies ()	
		
		alarm = metrics.create_alram (
			'%s-scale-up-on-credit' % self.name,
			'CPUCreditBalance',	'<', str (low),
			alarm_dimensions,
			scale_up_policy.policy_arn
		)
		cloudwatch.create_alarm (alarm)
		
		alarm = metrics.create_alram (
			'%s-scale-down-on-credit' % self.name,
			'CPUCreditBalance',	'>', str (high),
			alarm_dimensions,
			scale_down_policy.policy_arn
		)
		cloudwatch.create_alarm (alarm)
	
	def get_instances (self):
		return [inst for inst in iquery.get_instances_by_auto_scaling_group (self.name)]
	
	def get_instance_ids (self):
		return [h.id for h in self.get_instances ()]
			
	def is_empty (self):
		runnings = [1 for inst in iquery.get_instances_by_auto_scaling_group (self.name) if inst.update () != 'terminated']
		return not len (runnings)
		
	def remove (self):		
		ags = self.conn.get_all_groups (names = [self.name])
		if not ags:
			print ('auto scaling group not exists')
			return		
		ag = ags [0]
		ag.shutdown_instances ()
		
		while not self.is_empty ():
			print ('wait for all instances termination...', runnings)
			time.sleep (10)			
		ag.delete()
		
		lcs = self.conn.get_all_launch_configurations (names = [self.name])
		if not lcs:
			print ('launch configuration not exists')
			return		
		lc = lcs [0]
		lc.delete()	
