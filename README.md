# TeledyneLeCroyPy

Easily control a Teledyne LeCroy WaveRunner oscilloscope from Python.

![LeCroy WaveRunner oscilloscope](https://marvel-b1-cdn.bc0a.com/f00000000073308/assets.lcry.net/images/oscilloscopes/wr8000-1.png)

## Installation

```
pip install git+https://github.com/SengerM/TeledyneLeCroyPy
```

## Usage

Example:

```Python
import TeledyneLeCroyPy

osc = TeledyneLeCroyPy.LeCroyWaveRunner('USB0::bla::bla::bla::INSTR')

print(osc.idn) # Prints e.g. LECROY,WR640ZI,LCRY2810N60091,7.7.1

osc.wait_for_single_trigger() # Blocks until there is a trigger.
data = osc.get_waveform(channel=2) # Gets the data from channel 2 with the proper scaling to volts.
print(data['Time (s)'])
print(data['Amplitude (V)'])
```
