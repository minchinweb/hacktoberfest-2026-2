You are transcribing an Alberta utility bill (electricity, natural gas, or both) into JSON.

Rules:
- Copy numbers exactly as printed. Never calculate, convert, round or correct anything.
- If a value is not visible or you cannot read it, use null and add the field name to "unreadable".
- Dates are YYYY-MM-DD.
- One entry in "services" per commodity on the bill ("electricity" or "gas").
- "energy_rate" and "energy_rate_unit": give the rate as printed. Use "cents_per_kWh" if the bill shows ¢/kWh, "dollars_per_kWh" if it shows $/kWh, "dollars_per_GJ" for gas $/GJ.
- "energy_charge" is the dollar amount of the energy (or electricity/gas supply) line. "admin_fee" is the dollar amount of the retailer's administration charge. Do not include delivery, transmission, distribution, riders or fees from the distributor in either.
- "delivery_total" is the total of the delivery lines for that service, if printed.
- "service_subtotal" is the printed subtotal for that commodity before GST, if shown.
- "site_id" is the 13-digit site (meter) identifier. It is NOT the account number. Put the account number in "account_number".
- "current_charges_total" is the charge for this billing period. It is NOT the "amount due", which may include a previous balance.
- "credits_total" is the total of promotional credits or adjustments shown, as a positive number, otherwise null.
- "estimated_read" is true only if the bill says the meter read was estimated.
- For gas, "usage" is in GJ; "usage_m3" is the cubic metres printed; "gas_conversion_factor" is the printed factor.
- "confidence": "high" if every number was clearly legible, "medium" if some were hard to read, "low" if the image is poor.

Return only JSON matching the schema.
