# TeledyneLeCroyPy

Easily control a Teledyne LeCroy WaveRunner oscilloscope with pure Python. 

## Installation

```
pip3 install git+https://github.com/SengerM/TeledyneLeCroyPy
```
or clone in `my_favourite_directory` and then `pip3 install -e my_favourite_directory`.

## Usage

Simple example:
```Python
import pyvisa
import TeledyneLeCroyPy

osc = TeledyneLeCroyPy.LeCroyWaveRunner(pyvisa.ResourceManager().open_resource('USB0::bla::bla::bla::INSTR'))

print(osc.idn) # Prints e.g. LECROY,WR640ZI,LCRY2810N60091,7.7.1

osc.wait_for_single_trigger() # Blocks until a signal is acquired.
data = osc.get_waveform(channel=2) # Gets the data from channel 2 with the proper scaling to volts.
print(data['Time (s)'])
print(data['Amplitude (V)'])
```
