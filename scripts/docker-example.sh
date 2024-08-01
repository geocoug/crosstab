#!/bin/bash

osascript -e 'tell application "Microsoft Excel" to close (every workbook whose name is "test.xlsx") saving no' >> /dev/null \
&& docker run --rm -v $(pwd):/data ghcr.io/geocoug/crosstab:latest -d -k -s -f tests/data/sample2.csv -o test.xlsx -r location_id sample_no sample_material labsample meas_basis -c cas_rn analyte analyte_name -v concentration units qualifiers \
&& open test.xlsx
