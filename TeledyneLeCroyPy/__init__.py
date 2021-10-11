import time
import numpy as np
from pyvisa.resources import Resource



def _validate_channel_number(channel):
	CHANNEL_NUMBERS = {1,2,3,4}
	if channel not in CHANNEL_NUMBERS:
		raise ValueError(f'<channel> must be in {CHANNEL_NUMBERS}')

def _validate_trig_source(trig_source):
	TRIG_SOURCES_VALID = {'C1','C2','C3','C4','Ext','Line','FastEdge'}
	if not isinstance(trig_source, str):
		raise TypeError(f'The trigger source must be a string, received object of type {type(trig_source)}.')
	if trig_source.lower() not in {t.lower() for t in TRIG_SOURCES_VALID}:
		raise ValueError(f'The trigger source must be one of {TRIG_SOURCES_VALID}, received {repr(trig_source)}...')

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
		if 'lecroy' not in self.idn.lower():
			raise RuntimeError(f'The instrument you provided does not seem to be a LeCroy oscilloscope, its name is {self.idn}. Please check this.')
	
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
		"""Gets the waveform from the specified channel in SI units.
		- channel: int, the number of channel.
		Returns: A dictionary of the form {'Time (s)': array, 'Amplitude (V)': array}
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
		times = np.arange(len(raw_data))/sampling_rate + tdiv*14/2 # See page 223 in http://cdn.teledynelecroy.com/files/manuals/tds031000-2000_programming_manual.pdf
		volts = np.array(raw_data).astype(float)
		volts[volts>127] -= 255
		volts[volts>127-1] = float('NaN') # This means that there was overflow towards positive voltages. I don't want this to pass without notice.
		volts[volts<128-255+1] = float('NaN') # This means that there was overflow towards negative voltages. I don't want this to pass without notice.
		volts = volts/25*vdiv-ofst
		return {'Time (s)': np.array(times), 'Amplitude (V)': np.array(volts)}
	
	def wait_for_single_trigger(self,timeout=-1):
		"""Sets the trigger in 'SINGLE' and blocks the execution of the
		program until the oscilloscope triggers.
		- timeout: float, number of seconds to wait until rising a 
		RuntimeError exception. If timeout=-1 it is infinite."""
		try:
			timeout = float(timeout)
		except:
			raise TypeError(f'<timeout> must be a float number, received object of type {type(timeout)}.')
		self.set_trig_mode('SINGLE')
		start = time.time()
		while self.query('TRIG_MODE?') != 'STOP':
			time.sleep(.1)
			if timeout >= 0 and time.time() - start > timeout:
				raise RuntimeError(f'Timed out waiting for oscilloscope to trigger after {timeout} seconds.')
	
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
	
	def get_trig_source(self):
		"""Returns the trigger source as a string."""
		# See http://cdn.teledynelecroy.com/files/manuals/automation_command_ref_manual_ws.pdf#page=34
		return str(self.query("VBS? 'return=app.Acquisition.Trigger.Source'"))
	
	def set_trig_source(self, source: str):
		"""Sets the trigger source (C1, C2, Ext, etc.)."""
		# See http://cdn.teledynelecroy.com/files/manuals/automation_command_ref_manual_ws.pdf#page=34
		_validate_trig_source(source)
		string = "VBS 'app.Acquisition.Trigger.Source = "
		string += '"' + source + '"'
		string += "'"
		print(string)
		self.write(string)
	
	def set_trig_coupling(self, trig_source: str, trig_coupling: str):
		"""Set the trigger coupling (DC, AC, etc.)."""
		# See http://cdn.teledynelecroy.com/files/manuals/automation_command_ref_manual_ws.pdf#page=37
		_validate_trig_source(trig_source)
		VALID_TRIG_COUPLINGS = {'AC','DC','HFREJ','LFREJ'}
		if not isinstance(trig_coupling, str) or trig_coupling.lower() not in {tc.lower() for tc in VALID_TRIG_COUPLINGS}:
			raise ValueError(f'The trigger coupling must be one of {VALID_TRIG_COUPLINGS}, received {repr(trig_coupling)}...')
		string = f"VBS 'app.Acquisition.Trigger.{trig_source}.Coupling = "
		string += '"' + trig_coupling + '"'
		string += "'"
		self.write(string)
	
	def set_trig_level(self, trig_source: str, level: float):
		"""Set the trigger level."""
		# See http://cdn.teledynelecroy.com/files/manuals/automation_command_ref_manual_ws.pdf#page=36
		_validate_trig_source(trig_source)
		if not isinstance(level, (float, int)):
			raise ValueError(f'The trigger level must be a float number, received object of type {type(level)}.')
		string = f"VBS 'app.Acquisition.Trigger.{trig_source}.Level = "
		string += '"' + str(level) + '"'
		string += "'"
		self.write(string)
	
	def set_trig_slope(self, trig_source: str, trig_slope: str):
		"""Set the trigger slope (Positive, negative, either)."""
		# See http://cdn.teledynelecroy.com/files/manuals/automation_command_ref_manual_ws.pdf#page=36
		_validate_trig_source(trig_source)
		VALID_TRIG_SLOPES = {'Positive', 'Negative', 'Either'}
		if not isinstance(trig_slope, str) or trig_slope.lower() not in {tslp.lower() for tslp in VALID_TRIG_SLOPES}:
			raise ValueError(f'The trigger coupling must be one of {VALID_TRIG_SLOPES}, received {repr(trig_slope)}...')
		string = f"VBS 'app.Acquisition.Trigger.{trig_source}.Slope = "
		string += '"' + trig_slope + '"'
		string += "'"
		self.write(string)

class LeCroyWaveRunner640Zi(LeCroyWaveRunner):
	def __init__(self, instrument):
		super().__init__(instrument)
		if 'wr640zi' not in self.idn.lower():
			raise RuntimeError(f'The instrument you provided does not seem to be a LeCroy WaveRunner 640Zi, its name is {self.idn}. Please check.')

if __name__ == '__main__':
	# I am just testing...
	import pyvisa
	
	osc = LeCroyWaveRunner(pyvisa.ResourceManager().open_resource('USB0::0x05FF::0x1023::4751N40408::INSTR'))
	print(osc.idn)
	osc.set_trig_coupling('ext', 'DC')
	osc.set_trig_level('ext', -50e-3)
	osc.set_trig_slope('ext', 'Negative')
