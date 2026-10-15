| Model | Bills read | Quote-critical | Site ID | Fields | Avg s/bill |
|---|---|---|---|---|---|
| gemma4:e4b | 8/8 | 5/8 | 6/8 | 94.3% | 9.1 |
| qwen3-vl:8b | 6/8 | 6/8 | 5/8 | 97.3% | 73.2 |

Per bill (quote-critical correct?):

| Bill | gemma4:e4b | qwen3-vl:8b |
|---|---|---|
| 01_elec_clean.pdf | yes | NO |
| 02_gas_clean.pdf | yes | NO |
| 03_dual_fuel_2page.pdf | yes | yes |
| 04_phone_photo_dual_fuel.jpg | NO | yes |
| 05_estimated_read.pdf | yes | yes |
| 06_credit_dual_fuel.pdf | NO | yes |
| 07_inconsistent.pdf | yes | yes |
| 08_already_cheaper.pdf | NO | yes |
