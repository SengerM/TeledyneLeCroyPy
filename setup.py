import setuptools

setuptools.setup(
	name = "TeledyneLeCroyPy",
	version = "0.1",
	author = "Matias H. Senger",
	author_email = "m.senger@hotmail.com",
	description = "Control Teledyne LeCroy oscilloscopes easily from Python",
	url = "https://github.com/SengerM/TeledyneLeCroyPy",
	packages = setuptools.find_packages(),
	classifiers = [
		"Programming Language :: Python :: 3",
		"License :: OSI Approved :: MIT License",
		"Operating System :: OS Independent",
	],
)
