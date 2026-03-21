# Sources

## Datasets

### Mortgage Delinquency Data

**Source:** Consumer Financial Protection Bureau (CFPB), *Mortgage Performance Trends*

The delinquency rates used in this project come from the **National Mortgage Database (NMDB)**, a joint project of the CFPB and the Federal Housing Finance Agency (FHFA).
The NMDB is a nationally representative, 5 percent sample of all outstanding, closed-end, first-lien, 1–4 family residential mortgages.
Core data are maintained by one of the top three nationwide credit repositories.

- **30–89 day delinquency rate** (`Early_Delinquency_Rate`): share of borrowers 30–89 days past due. An early indicator of mortgage market health; seasonally volatile and sensitive to temporary economic shocks.
- **90+ day delinquency rate** (`Late_Delinquency_Rate`): share of borrowers 90+ days past due (excluding foreclosure). A measure of more severe economic distress.

County-level monthly CSVs are available from January 2008 onward. Some counties are suppressed due to small sample sizes.

**Links:**
- CFPB Mortgage Performance Trends: https://www.consumerfinance.gov/data-research/mortgage-performance-trends/
- NMDB Program Page (FHFA): https://www.fhfa.gov/programs/nmdb
- NMDB Technical Reports: https://www.consumerfinance.gov/data-research/research-reports/technical-reports-national-survey-of-mortgage-borrowers-and-national-mortgage-database/

### Disaster Data

**Source:** National Oceanic and Atmospheric Administration (NOAA), *Storm Events Database*

Event-level records of storms and significant weather phenomena across the United States, compiled by the National Weather Service (NWS).
Each record contains event type, location (state and county FIPS), date, property and crop damage estimates, injuries, and fatalities.

The database covers events from 1950 onward; this project uses records from 1980–2025.
Event types are defined by NWS Directive 10-1605, Section 2.1.1.

**Links:**
- NOAA Storm Events Database: https://www.ncdc.noaa.gov/stormevents/
- Storm Data Bulk Data: https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/

---

## Data Cleaning and Preparation

The raw data cleaning pipeline was developed by Anupam Ghosh as part of the following working paper:
> Ghosh, Anupam, *Do Storms Bring Crime? Evidence from US Counties* (October 01, 2025). Available at SSRN: https://ssrn.com/abstract=6165266 or http://dx.doi.org/10.2139/ssrn.6165266

The Stata do-files and their Python translation are documented in [docs/Cleaning.md](Cleaning.md).
