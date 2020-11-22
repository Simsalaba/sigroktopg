# SigrokToPg - power profiling data collector

SigrokToPg is a executable python script that parses stdout data from "sigrok-cli" and pushes it to a PostgreSQL database to be used for power profiling tests of a given device.

## Installation

cd into the root folder and use the package manager [pip3](https://pip.pypa.io/en/stable/) to install sigrokToPg.

```bash
pip3 install .
```

## Usage

```bash
sigroktopg -deviceName <you-device-name> -user <your-name> -deviceId <UUID or serialnumber of the device> -testSessionName <name-of-your-test> 
```

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License
[MIT](https://choosealicense.com/licenses/mit/)
