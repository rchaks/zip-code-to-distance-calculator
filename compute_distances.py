import logging
import typer
import csv
import sys
from typing import Dict, Optional, Tuple, IO, Union, Iterable
import requests
from os import path, listdir
from tempfile import TemporaryDirectory
import zipfile
from tqdm import tqdm
from geopy import distance

ZIP_LAT_TO_LONG_LOOKUP_FILE = "http://download.geonames.org/export/zip/US.zip"


def _download_and_extract_file(from_url: str, to_dir: str) -> str:
    r = requests.get(from_url)
    logging.info(f"Downloading lookup for zip codes from {from_url}")

    zip_archive_file = path.join(to_dir, path.basename(from_url))

    with open(zip_archive_file, 'wb') as output_file:
        output_file.write(r.content)

    logging.debug(f"Downloaded file to {zip_archive_file}. Extracting file from zip archive.")
    with zipfile.ZipFile(zip_archive_file, 'r') as zip_ref:
        zip_ref.extractall(to_dir)

    zip_to_lat_long_txt_file = path.join(to_dir, f"{path.basename(from_url).split('.')[0]}.txt")
    if not path.isfile(zip_to_lat_long_txt_file):
        raise ValueError(f"Expected the zip archive {zip_archive_file} to contain "
                         f"{zip_to_lat_long_txt_file}. But found: {listdir(to_dir)}")
    return zip_to_lat_long_txt_file


def _generate_lat_long_lookup_by_zip(infile: Union[typer.FileText, IO]) -> Dict[str, Tuple[float, float]]:
    """
    Function to create a lookup from zip code to lat/long pair from a tab delimited file with the following fields :
        1. country code      : iso country code, 2 characters -- OPTIONAL
        2. postal code       : varchar(20)
        3. place name        : varchar(180) -- OPTIONAL
        4. admin name1       : 1. order subdivision (state) varchar(100)  -- OPTIONAL
        5. admin code1       : 1. order subdivision (state) varchar(20)  -- OPTIONAL
        6. admin name2       : 2. order subdivision (county/province) varchar(100)  -- OPTIONAL
        7. admin code2       : 2. order subdivision (county/province) varchar(20)  -- OPTIONAL
        8. admin name3       : 3. order subdivision (community) varchar(100)  -- OPTIONAL
        9. admin code3       : 3. order subdivision (community) varchar(20)  -- OPTIONAL
        10. latitude          : estimated latitude (wgs84)
        11. longitude         : estimated longitude (wgs84)

    """
    zip_to_lat_long = dict()
    for i, row in enumerate(tqdm(csv.reader(infile, delimiter="\t"),
                                 desc=f'Reading latitudes and longtitudes for each zip from {infile.name}')):
        column_idx_for_long = 10
        column_idx_for_lat = 9
        column_idx_for_zip = 1
        max_index = max(column_idx_for_lat, column_idx_for_zip, column_idx_for_long)
        if row and len(row) > max_index:
            try:
                zip_to_lat_long[row[column_idx_for_zip].strip()] = (float(row[column_idx_for_lat]),
                                                                    float(row[column_idx_for_long]))
            except ValueError as ex:
                raise ValueError(f"Error trying to parse values from line {i+1} of file: {row}."
                                 f"Expected to parse zip from column {column_idx_for_zip+1}, "
                                 f"latitude from column {column_idx_for_lat+1} or "
                                 f"longtitude from column {column_idx_for_long+1}") from ex
        else:
            logging.warning(f"Expected tab delimited row with at least {max_index + 1} columns, but found: {row}")
    logging.info(f"Read {len(zip_to_lat_long)} zip codes worth of latitutdes and longtitudes")
    return zip_to_lat_long


def _read_zip_to_lat_long_lookup(zip_to_lat_long_lookup_file: Optional[typer.FileText]) -> Dict[str,Tuple[float, float]]:
    if not zip_to_lat_long_lookup_file:
        with TemporaryDirectory() as temp_dir:
            input_lookup_file = _download_and_extract_file(from_url=ZIP_LAT_TO_LONG_LOOKUP_FILE, to_dir=temp_dir)
            with open(input_lookup_file) as infile:
                return _generate_lat_long_lookup_by_zip(infile)
    else:

        return _generate_lat_long_lookup_by_zip(zip_to_lat_long_lookup_file)


def _read_zip_codes(infile: typer.FileText) -> Iterable[str]:
    reader = csv.reader(infile)
    header = next(reader)
    try:
        zip_code_column_index = [x.strip().lower() for x in header].index("zip code")
    except ValueError as ex:
        raise ValueError(f"Expected to find a header row with Zip Code, but found: {header}") from ex

    num_zip_codes = 0
    for i, row in enumerate(tqdm(reader, desc=f"Reading zip codes from {infile.name}")):
        if row and len(row) > zip_code_column_index:
            num_zip_codes += 1
            yield row[zip_code_column_index].strip()
        else:
            logging.warning(f"Ignoring line {i + 1} b/c expected to find at least {zip_code_column_index + 1} "
                            f"columns but from row: {row}")

    if num_zip_codes > 0:
        logging.info(f"Read {num_zip_codes} zip codes from {infile.name}")
    else:
        raise ValueError(f"No zip codes read from {infile.name}")


def _compute_distance(source_lat, source_long, dst_lat, dst_long) -> float:
    """
    See docs for geopy to modify this to use other types of distance calculations:
    https://geopy.readthedocs.io/en/stable/#module-geopy.distance
    """
    return distance.distance((source_lat, source_long), (dst_lat, dst_long)).miles


def main(src: typer.FileText = typer.Option(default="sample_address_file_a.csv", help="source address csv filepath"),
         dst: typer.FileText = typer.Option(default="sample_address_file_b.csv",
                                            help="destination address csv filepath"),
         outfile: Optional[typer.FileTextWrite] = typer.Option(
             default=sys.stdout, help="output file path (if none provided, prints output to stdout"),
         zip_to_lat_long_lookup_file: typer.FileText = typer.Option(
             default=None, help=f"Optionally a path to a csv file containing a mapping from zip code to lat/long. "
                                f"If none provided, we will download the file from {ZIP_LAT_TO_LONG_LOOKUP_FILE}"),
         loglevel: str = typer.Option('INFO', help='log level')):
    logging.basicConfig(level=loglevel)

    logging.info('Starting Script')
    zip_to_lat_long_lookup = _read_zip_to_lat_long_lookup(zip_to_lat_long_lookup_file)
    destination_lat_longs = list((zip_code, zip_to_lat_long_lookup[zip_code]) for zip_code in _read_zip_codes(dst))

    writer = csv.writer(outfile)
    writer.writerow(["Source Zip Code", "Destination Zip Code", "Geodic Distance"])
    num_written = 0
    for source_zip in _read_zip_codes(src):
        source_lat, source_long = zip_to_lat_long_lookup[source_zip]
        for dst_zip, (dst_lat, dst_long) in destination_lat_longs:
            num_written += 1
            writer.writerow([source_zip, dst_zip, _compute_distance(source_lat, source_long, dst_lat, dst_long)])

    logging.info(f"Computed {num_written} distances")


if __name__ == '__main__':
    typer.run(main)
