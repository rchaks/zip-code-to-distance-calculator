# zip-code-to-distance-calculator
A simple python script which reads in a set of zip codes from one csv file 
(source addresses) and a set of zip codes from a second csv file (destination
addresses) and computes a distance between each pair of source and destination
zip codes. The output is written to an output csv file.

Currently, the distance calculation is the [vincenty distance](https://en.wikipedia.org/wiki/Vincenty's_formulae)
based on a mapping to 
[the latitude and longtitude associated with each zip code](http://download.geonames.org/export/zip/).


## Setup

_All commands should be executed from directory root_

### (Optional) Setup Python 3 Virtualenv

- Install [python 3.x](https://www.python.org/downloads/) if not already installed
  * Code tested with 3.8; but presumably any Python 3 version should work
- Install [pip](https://pip.pypa.io/en/stable/) if not already installed (should be part of python install)
- Install [virtualenv](https://virtualenv.pypa.io/en/latest/) if desired for environment isolation
- Create & activate virtualenv:
  ```
  virtualenv -p python3 venv
  source venv/bin/activate
  ```

### Install dependencies

```
pip install -r requirements.txt
```

### Format input files

You will need 2 csv files both w/ the same format.  One w/ the source addresses
and the other with destination addresses.  Each file should have a header row
with a column named Zip Code:
```
Zip Code,Zip Code Name,State
10552,Mount Vernon, NY
``` 

Two sample files (sample_address_file_a.csv and sample_address_file_b.csv) are provided for testing.

## Run script

### Sample command
```
python compute_distances.py --src sample_address_file_a.csv \
 --dst sample_address_file_b.csv \
 --outfile output_distances.csv
```

Running the above command should yield an output csv file at `output_distances.csv` 
with the following contents:

```
Source Zip Code,Destination Zip Code,Geodic Distance
10552,10550,1.131330300414714
10552,53013,740.3885268206351
```

Run `python compute_distances.py --help` for more parameter details/options.