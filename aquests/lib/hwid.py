import subprocess
import os

def get_id():
    if 'nt' in os.name:
        return subprocess.Popen('dmidecode.exe -s system-uuid'.split())
    else:
        return subprocess.Popen('hal-get-property --udi /org/freedesktop/Hal/devices/computer --key system.hardware.uuid'.split())
		
		
if __name__ == "__main__":
	print (get_id())
	