# inky-display
This is the display component of [inky-mbta-tracker](https://github.com/cubismod/inky-mbta-tracker).

## Required Components
* [Yellow Inky wHAT Display](https://shop.pimoroni.com/products/inky-what?variant=21441988558931).
  * Note: this is only yellow right now because I would have to change the colors otherwise to get red
  working. Black and white will not work.
* Compatible Raspberry Pi.
* Configured inky-mbta-tracker Redis accessible over the network.

## Setup
* Setting up your Pi & Inky wHAT is left to the reader.
* Create a `.env` file:
```
REDIS_HOST=<your_host_here>
REDIS_PORT=<port_num>
REDIS_PASS=<password>
```
* Create a virtual environment.
* Follow the I2C/SPI pre-req steps from the [inky GitHub library README](https://github.com/pimoroni/inky?tab=readme-ov-file#install-stable-library-from-pypi-and-configure-manually).
* Install [Taskfile](https://taskfile.dev/installation/) which is used in lieu of a Makefile.
* Run `task install-fonts` to install the required fonts to the `fonts/` directory.
* Run `task run` to watch the display.

