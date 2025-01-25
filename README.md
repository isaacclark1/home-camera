# Home Camera Web Application

For Picamera2 documentation click [here](https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf).

To use this application on your own Raspberry Pi 5, clone this repository and then:

1. Run `sudo apt-get update`.
2. Run `sudo apt-get install python3-picamera2` to install the picamera2 library.
3. Switch to the `home-camera` directory.
4. Run `python3 -m venv --system-site-packages venv` to create a Python virtual environment named venv in the current directory which inherits packages from the system-wide Python installation.
5. Run `source venv/bin/activate` to activate the Python virtual environment which configures the shell to use the Python interpreter and dependencies in the virtual environment.
