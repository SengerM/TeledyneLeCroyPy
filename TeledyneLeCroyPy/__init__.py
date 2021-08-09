from time import sleep
import numpy as np
from pyvisa.resources import Resource

def _validate_channel_number(channel):
	CHANNEL_NUMBERS = {1,2,3,4}
	if channel not in CHANNEL_NUMBERS:
		raise ValueError(f'<channel> must be in {CHANNEL_NUMBERS}')

class LeCroyWaveRunner:
	def __init__(self, instrument):
		"""This is a wrapper class for a pyvisa Resource object to communicate
		with a LeCroy oscilloscope.
		- instrument: A pyvisa Resource object. If for some reason you
		want to access the Resource object, it is stored in `LeCroyWaveRunner.resource`."""
		if not isinstance(instrument, Resource):
			raise TypeError(f'<instrument> must be an instance of {Resource}, i.e. you have to connect to this instrument using pyvisa and provide me the instrument. For example `instrument = pyvisa.ResourceManager().open_resource("USB0::bla::bla::bla::INSTR")`.')
		self.resource = instrument
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
		response = self.resource.read()
		if response[-1] == '\n':
			response = response[:-1]
		return response
	
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
		sampling_rate = float(self.query("VBS? 'return=app.Acquisition.Horizontal.SamplingRate'")) # This line is a combination of http://cdn.teledynelecroy.com/files/manuals/maui-remote-control-and-automation-manual.pdf and p. 1-20 http://cdn.teledynelecroy.com/files/manuals/automation_command_ref_manual_ws.pdf
		vdiv = self.get_vdiv(channel)
		ofst = float(self.query('c1:ofst?'))
		times = np.arange(len(raw_data))
		volts = np.array(raw_data)
		volts[volts>127] -= 255
		volts = volts/25*vdiv-ofst
		return {'time': np.array(times), 'volt': np.array(volts)}
	
	def set_trig_mode(self, mode: str):
		"""Sets the trigger mode."""
		OPTIONS = ['AUTO', 'NORM', 'STOP', 'SINGLE']
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
