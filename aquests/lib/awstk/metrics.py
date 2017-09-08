import boto.ec2.cloudwatch
from boto.ec2.cloudwatch import MetricAlarm
import datetime

STATISTICS = ['Minimum', 'Maximum', 'Sum', 'Average', 'SampleCount']
UNITS = [
	'Seconds', 'Microseconds', 'Milliseconds', 'Bytes', 'Kilobytes', 'Megabytes', 'Gigabytes', 'Terabytes', 
	'Bits', 'Kilobits', 'Megabits', 'Gigabits', 'Terabits', 'Percent', 'Count', 'Bytes/Second', 
	'Kilobytes/Second', 'Megabytes/Second', 'Gigabytes/Second', 'Terabytes/Second', 'Bits/Second', 
	'Kilobits/Second', 'Megabits/Second', 'Gigabits/Second', 'Terabits/Second', 
	'Count/Second', None
]

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

def create_alram (name, metric, comparison, threshold, dimensions, arn, period = 300, evaluation_periods = 2):
	return MetricAlarm(
		name = name, 
		metric = metric, 
		statistic = PREF [metric][0],
		comparison = comparison, 
		alarm_actions = [arn],
		dimensions = dimensions,
		namespace = 'AWS/EC2',
		threshold = str (threshold),
		period = str (period), 
		evaluation_periods = evaluation_periods
	)
	
def get_instance_metric (instance_id,region = 'us-east-1'):
	cw = boto.ec2.cloudwatch.connect_to_region(region)
	return cw.list_metrics(dimensions = {"InstanceId": instance_id})	
	
def get_latest (instance_id, measure = None):	
	end = datetime.datetime.utcnow()
	start = end - datetime.timedelta (minutes = 20)	
	r = {}
	for metric in get_instance_metric (instance_id):
		pref = measure or PREF.get (metric.name)
		if not pref:
			continue
		datapoints = metric.query (start, end, *pref)
		r [metric.name] = datapoints and datapoints [0][pref [0]] or None		
	return r		
