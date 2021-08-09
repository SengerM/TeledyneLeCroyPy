import pyvisa
from time import sleep
import numpy as np

def _validate_channel_number(channel):
	CHANNEL_NUMBERS = {1,2,3,4}
	if channel not in CHANNEL_NUMBERS:
		raise ValueError(f'<channel> must be in {CHANNEL_NUMBERS}')

class LeCroyWaveRunner:
	def __init__(self, name):
		"""Creates an object to communicate to and control an oscilloscope.
		- name: It is whatever you use to connect to the oscilloscope by
		using pyvisa. I.e. <name> is what is listed by the resource
		manager.
		When the object was created, in LeCroyWaveRunner.resource you can
		find the "pyvisa resource" (or whatever name this has) to directly
		communicate with the instrument if you need it."""
		rm = pyvisa.ResourceManager()
		self.resource = rm.open_resource(name)
		self.write('CHDR OFF') # This is to receive only numerical data in the answers and not also the echo of the command and some other stuff. See p. 22 of http://cdn.teledynelecroy.com/files/manuals/tds031000-2000_programming_manual.pdf
	
	@property
	def idn(self):
		"""Returns the name of the instrument, i.e. its answer to the
		command "*IDN?"."""
		return  self.query('*IDN?')
	
	def write(self, msg):
		"""Sends a command to the instrument."""
		self.resource.write(msg)
	
	def read(self):
		"""Reads the answer from the instrument."""
		return self.resource.read()
	
	def query(self, msg):
		"""Sends a command to the instrument and immediately reads the
		answer."""
		self.write(msg)
		return self.read()
	
	def get_waveform(self, channel: int):
		"""Gets the waveform from the specified channel.
		- channel: int, the number of channel.
		Returns: A dictionary of the form {'time': array, 'volt': array}
		containing the time and voltage values."""
		# Page 223: http://cdn.teledynelecroy.com/files/manuals/tds031000-2000_programming_manual.pdf
		# Page 258: http://cdn.teledynelecroy.com/files/manuals/wr2_rcm_revb.pdf
		_validate_channel_number(channel)
		self.write(f'C{channel}:WF?')
		raw_data = list(self.resource.read_raw())[361:-1] # By some unknown reason the first 360 samples are crap, and also the last one.
		tdiv = float(self.query('TDIV?'))
		sampling_rate = float(self.query(r"""VBS? 'return=app.Acquisition.Horizontal.SamplingRate'""")) # This line is a combination of http://cdn.teledynelecroy.com/files/manuals/maui-remote-control-and-automation-manual.pdf and p. 1-20 http://cdn.teledynelecroy.com/files/manuals/automation_command_ref_manual_ws.pdf
		vdiv = float(self.query('c1:vdiv?'))
		ofst = float(self.query('c1:ofst?'))
		times = []
		volts = []
		for idx,sample in enumerate(raw_data):
			if sample > 127:
				sample -= 255
			volts.append(sample/25*vdiv - ofst)
			times.append(tdiv*14/2+idx/sampling_rate)
		return {'time': np.array(times), 'volt': np.array(volts)}
	
	def set_trig_mode(self, mode: str):
		"""Sets the trigger mode."""
		OPTIONS = ['AUTO', 'NORM', 'STOP', 'SINGLE']
		if not isinstance(mode, str):
			raise TypeError('<mode> must be a string')
		if mode.upper() not in OPTIONS:
			raise ValueError('<mode> must be one of ' + str(OPTIONS))
		self.write('TRIG_MODE ' + mode)
	
	def set_vdiv(self, channel: int, vdiv: float):
		"""Sets the vertical scale for the specified channel."""
		try:
			vdiv = float(vdiv)
		except:
			raise TypeError(f'<vdiv> must be a float number, received object of type {type(vdiv)}.')
		_validate_channel_number(channel)
		self.write(f'C{channel}:VDIV {float(vdiv)}') # http://cdn.teledynelecroy.com/files/manuals/tds031000-2000_programming_manual.pdf#page=47
	
	def get_vdiv(self, channel: int):
		"""Gets the vertical scale of the specified channel. Returns a 
		float number with the volts/div value."""
		_validate_channel_number(channel)
		return float(self.query(f'C{channel}:VDIV?')) # http://cdn.teledynelecroy.com/files/manuals/tds031000-2000_programming_manual.pdf#page=47
