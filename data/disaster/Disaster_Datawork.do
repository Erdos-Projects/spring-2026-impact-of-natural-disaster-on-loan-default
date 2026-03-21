cd "D:\Academic\1-UNL\1-Research\1-Projects\1-US Studies\1-Hurricanes and Crime\1-Data\2-Disaster Data\NWS\Raw Data\Excel"
gl path "C:\Users\ghosh\OneDrive - University of Nebraska\2-Erdos\1-Climate Finance Project\Data\Raw Data"
*
clear
forvalues i = 1980/2025 {
    import delimited "`i'.csv", clear
    
    if `i' == 1980 {
        tempfile combined
        save `combined', replace
    }
    else {
        append using `combined', force
        save `combined', replace
    }
}
*

*
save "NWS_temp.dta", replace
************************************************************
// Using CountyCode

use CountyCode.dta, clear
duplicates drop FIPS, force 
keep FIPS* *NAME*
destring FIPS_ST FIPS_COUNTY FIPS, force replace
*
drop UANAME-DISTNAME
drop NAME
save FIPS.dta, replace
************************************************************
**# Bookmark #2
************************************************************
// Cleaning
use "NWS_temp.dta", clear
*
*keep if cz_type=="C"
ren state_fips FIPS_ST
ren cz_fips FIPS_COUNTY
*
merge m:m FIPS_ST FIPS_COUNTY using FIPS.dta
keep if _merge==3
drop _merge
*
g day=begin_day
ren month_name month
*
// Generate month number using month() function on a date
gen temp_date = date(month + " 1, " + string(year), "MDY")
gen month_num = month(temp_date)
drop temp_date

// Create monthly time variable
gen time = ym(year, month_num), before(year)
format time %tm
//
order FIPS_ST STATENAME FIPS_COUNTY COUNTYNAME FIPS time day month year ///
event_id event_type tor_f_scale injuries_indirect deaths_direct deaths_indirect ///
damage_property damage_crops
//
ren FIPS fips
label var fips "County-level fips code. Used for linking datasets"
//
sort fips time
duplicates drop fips time event_id, force
//
************************************************************
* Keep only rows ending in K, M, or B (case-insensitive)
gen last_char = upper(substr(damage_property, -1, 1))

* Extract the numeric part (everything except the last character)
gen num_part = substr(damage_property, 1, strlen(damage_property) - 1)
destring num_part, replace force

* Create multiplier
gen multiplier = 1
replace multiplier = 1000        if last_char == "K"
replace multiplier = 1000000     if last_char == "M"
replace multiplier = 1000000000  if last_char == "B"

* Final monetary variable
gen property_damage_value = num_part * multiplier, before(damage_property)

* Clean up
drop if missing(damage_property) | damage_property=="0.00K"| damage_property=="0" | damage_property=="0K"
drop if last_char != "K" & last_char != "M" & last_char != "B"
drop last_char num_part multiplier
//
gen Event_Subtype =event_type, before(event_type)
//
replace event_type = "Thunderstorm" if strpos(event_type, "THUNDER") |  ///
strpos(event_type, "Thunder") | strpos(event_type, "THUNDERSTORM WIND/ TREE") |  ///
strpos(event_type, "THUNDERSTORM WIND/ TREES")  | strpos(event_type, "THUNDERSTORM WINDS LIGHTNING") |  ///
strpos(event_type, "THUNDERSTORM WINDS/ FLOOD") | strpos(event_type, "THUNDERSTORM WINDS/FLOODING") |  ///
strpos(event_type, "Thunderstorm Wind") | strpos(event_type, "Thunderstorm Wind")
*
replace event_type = "Dust Storm" if strpos(event_type, "Dust Devil") | strpos(event_type, "Dust Storm")
*
replace event_type = "Hurricane" if strpos(event_type, "Hurricane (Typhoon)") | ///
strpos(event_type, "Storm Surge/Tide") | strpos(event_type, "High Surf") | strpos(event_type, "Marine High Wind")
*
replace event_type = "Winter Wave" if strpos(event_type, "Winter Storm") | strpos(event_type, "Sleet") | ///
strpos(event_type, "Winter Weather") | strpos(event_type, "Ice Storm") | ///
strpos(event_type, "Frost/Freeze") | strpos(event_type, "Freezing Fog") | strpos(event_type, "Extreme Cold/Wind Chill") | ///
strpos(event_type, "Heavy Snow") | strpos(event_type, "Blizzard") | strpos(event_type, "Cold/Wind Chill")
*
replace event_type = "Flood" if strpos(event_type, "Flash Flood") | strpos(event_type, "Lakeshore Flood") | ///
strpos(event_type, "Coastal Flood")
*
replace event_type = "Heat Wave" if strpos(event_type, "Excessive Heat") | strpos(event_type, "Heat")
//
keep fips time Event_Subtype event_type event_id tor_f_scale injuries_indirect injuries_direct deaths_direct ///
deaths_indirect property_damage_value damage_property damage_crops event_narrative
//
save "Disaster_Dataset.dta", replace
save "$path\Disaster_Dataset.dta", replace
************************************************************
**# Bookmark #1
************************************************************
foreach event in "Hurricane" "Tornado" "Tropical Storm" "Thunderstorm" "Flood" "Winter Wave" "Wildfire" "Hail" {
    use "Disaster_Dataset_Cleaned.dta", clear
    keep if event_type == "`event'"
    
    * Get median property damage
    sum property_damage_value, detail
    local med = r(p50)
    
    * Label as high or low cost
    gen event_damage_indicator = "", after(event_type)
    replace event_damage_indicator = "High_Cost_Event" if property_damage_value > `med'
    replace event_damage_indicator = "Low_Cost_Event"  if property_damage_value <= `med'
    *
	label var event_damage_indicator "High_Cost_Event = >Median Property Damage" 
	*
    local fname = subinstr("`event'", " ", "_", .)
    save "C:\Users\ghosh\OneDrive - University of Nebraska\2-Erdos\1-Climate Finance Project\Data\Individual Disasters\\`fname'.dta", replace
}