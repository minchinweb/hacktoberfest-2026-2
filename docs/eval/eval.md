| Model | Bills read | Quote-critical | Site ID | Fields | Avg s/bill |
|---|---|---|---|---|---|
| gemma4:e4b | 8/8 | 5/8 | 7/8 | 95.3% | 9.1 |
| qwen3-vl:8b | 7/8 | 7/8 | 6/8 | 97.2% | 73.1 |

Per bill (quote-critical correct?):

| Bill | gemma4:e4b | qwen3-vl:8b |
|---|---|---|
| 01_elec_clean.pdf | yes | NO |
| 02_gas_clean.pdf | yes | yes |
| 03_dual_fuel_2page.pdf | yes | yes |
| 04_phone_photo_dual_fuel.jpg | NO | yes |
| 05_estimated_read.pdf | yes | yes |
| 06_credit_dual_fuel.pdf | NO | yes |
| 07_inconsistent.pdf | yes | yes |
| 08_already_cheaper.pdf | NO | yes |
