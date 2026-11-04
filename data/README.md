# Data files

Rainfall comes live from Open-Meteo. These two files must be filled by hand
with verified numbers for the villages you want to support:

- `groundwater.json`: category and water table depth from the CGWB / India-WRIS
  groundwater report for the block or taluk.
- `guideline_values.json`: rupees per cent from the Tamil Nadu registration
  department guideline value lookup.

Set `"verified": true` only after you copied the number from the official source
and updated `"source"`. While `verified` is false, the agent tells the user the
figure is a placeholder.
