#!/bin/bash

# osascript -e 'tell application "Microsoft Excel" to close (every workbook whose name is "test.xlsx") saving no' >> /dev/null \
# && uv pip install -e . \
# && crosstab -d -k -f tests/data/sample2.csv -o test.xlsx -r location_id sample_no sample_material labsample meas_basis -c cas_rn analyte analyte_name -v concentration units qualifiers \
# && open test.xlsx

osascript -e 'tell application "Microsoft Excel" to close (every workbook whose name is "test.xlsx") saving no' >> /dev/null \
&& uv pip install -e . \
&& crosstab -d -k -f sample.csv -o test.xlsx -r location sample -c cas_rn parameter -v concentration units \
&& open test.xlsx
