********************************************************************************
**# Handling Finance Dataset
// Early Delinquency
********************************************************************************
cd "C:\Users\ghosh\OneDrive - University of Nebraska\2-Erdos\1-Climate Finance Project\Data\Raw Data"
gl pathA "C:\Users\ghosh\OneDrive - University of Nebraska\2-Erdos\1-Climate Finance Project\Data\Figures"
*
import delimited "Finance_30_89_EarlyDelinquency.csv", varnames(1) case(preserve) asfloat clear
*
local vnum = 4

* Full years: 2008-2024
forvalues y = 2008/2024 {
    forvalues m = 1/12 {
        local mstr = string(`m', "%02.0f")
        rename v`vnum' m`y'_`mstr'
        local vnum = `vnum' + 1
    }
}

* Partial year: 2025 (Jan-Mar)
forvalues m = 1/3 {
    local mstr = string(`m', "%02.0f")
    rename v`vnum' m2025_`mstr'
    local vnum = `vnum' + 1
}
*
ren Name County
gen fips_clean = ustrregexra(FIPSCode, "[^0-9]", ""), after(County)
drop FIPSCode
rename fips_clean fips
destring fips, force replace
*
gen Delinquency_Status = "Early_30_89Day_Delinquency" , after(County)
*
save "Early_30_89Day_Delinquency.dta", replace 
********************************************************************************
// Late Delinquency
********************************************************************************
import delimited "Finance_90_LateDelinquency.csv", varnames(1) case(preserve) asfloat clear
*
local vnum = 4

* Full years: 2008-2024
forvalues y = 2008/2024 {
    forvalues m = 1/12 {
        local mstr = string(`m', "%02.0f")
        rename v`vnum' m`y'_`mstr'
        local vnum = `vnum' + 1
    }
}

* Partial year: 2025 (Jan-Mar)
forvalues m = 1/3 {
    local mstr = string(`m', "%02.0f")
    rename v`vnum' m2025_`mstr'
    local vnum = `vnum' + 1
}
*
ren Name County
gen fips_clean = ustrregexra(FIPSCode, "[^0-9]", ""), after(County)
drop FIPSCode
rename fips_clean fips
destring fips, force replace
*
gen Delinquency_Status = "Late_>90Day_Delinquency" , after(County)
*
save "Late_90Day_Delinquency.dta", replace 
********************************************************************************
**# Merging Both Finance Datasets
********************************************************************************
append using "Early_30_89Day_Delinquency.dta", force
*
sort fips Delinquency_Status
* Reshape wide to long
reshape long m, i(State County Delinquency_Status fips) j(yearmonth) string

* Clean up the yearmonth variable: "2008_01" → "2008m1"
replace yearmonth = subinstr(yearmonth, "_", "m", 1)

* Convert to Stata monthly date
gen month = monthly(yearmonth, "YM")
format month %tm

* Optional: rename the value variable
rename m delinquency_rate

* Sort
sort fips Delinquency_Status month
*
gen Early_Delinquency_Rate = delinquency_rate if Delinquency_Status=="Early_30_89Day_Delinquency"
gen Late_Delinquency_Rate = delinquency_rate if Delinquency_Status=="Late_>90Day_Delinquency"
*
collapse (mean) Early_Delinquency_Rate Late_Delinquency_Rate, by(State County fips month)
sort fips month State County
*
ren month time
xtset fips time
duplicates drop fips time, force
*
save "Finance_Dataset.dta", replace
********************************************************************************
**# Handling Disaster Data
********************************************************************************
use "Disaster_Dataset.dta", clear
*
g property_damage_billions = (property_damage_value/(10^9))
*
graph bar (sum) property_damage_billions, ///
    over(event_type, sort(1) descending label(angle(45))) ///
    ytitle("Total Property Damage Value (Billions $)") ///
    title("Property Damage by Disaster Type") ///
    bar(1, color("59 130 186")) ///
    scheme(s1color)
	graph export "$pathA/Property_Damage_by_DisasterType.png", replace
********************************************************************************














********************************************************************************
**# Merging Climate Data
********************************************************************************
*********************************************************************************
use "Finance_Cleaned.dta", clear
merge m:m fips time using "Disaster_Dataset_Cleaned.dta"
drop if _merge==2
drop _merge
*
duplicates drop fips time, force
xtset fips time
*
gen Event_Occur = cond(!missing(event_type),1,0), before(event_id)
label var Event_Occur "A disaster event occurs if =1 else 0"
*
************************************************************
* Check for repeated events within 12 months in same county
sort fips time
bysort fips (time): gen time_to_next = time[_n+1] - time if _n < _N & Event_Occur == 1 & Event_Occur[_n+1] == 1
bysort fips (time): gen time_to_prev = time - time[_n-1] if _n > 1 & Event_Occur == 1 & Event_Occur[_n-1] == 1

gen contaminated = 0
replace contaminated = 1 if time_to_next <= 12 & !missing(time_to_next)
replace contaminated = 1 if time_to_prev <= 12 & !missing(time_to_prev)

bysort fips: egen county_contaminated = max(contaminated)
drop if county_contaminated == 1
drop time_to_next time_to_prev contaminated county_contaminated
*
xtset fips time
*
merge m:m fips using "County_Area.dta"
keep if _merge==3
drop _merge
*
*
merge m:m fips using "Coastal_Counties.dta"
drop if _merge==2
drop _merge
*
merge m:m fips using "County_CoastDist.dta"
keep if _merge==3
drop _merge
*
duplicates drop fips time, force
xtset fips time
*
g Coastal_County = "Coastal" if !missing(COASTLINEREGION), after(time)
replace Coastal_County="Non-Coastal" if missing(COASTLINEREGION)
*
* Temporarily save event medians and classify
gen Event_Damage_Indicator = "", after(event_type)
label var Event_Damage_Indicator "High_Cost_Event = >Median Property Damage"

foreach event in "Hurricane" "Tornado" "Tropical Storm" "Thunderstorm" "Flood" "Winter Wave" "Wildfire" "Hail" {
    sum property_damage_value if event_type == "`event'", detail
    local med = r(p50)
    replace Event_Damage_Indicator = "High_Cost_Event" if event_type == "`event'" & property_damage_value > `med'
    replace Event_Damage_Indicator = "Low_Cost_Event"  if event_type == "`event'" & property_damage_value <= `med'
}
*
drop COUNTYNAME STATENAME stateFIPS countyFIPS county state
ren COASTLINEREGION Coastline_Region
ren tor_f_scale Tornado_Intensity_Scale
rename *, lower
rename _all, proper
ren Fips fips
ren Time time
*
save "Finance_Disaster_Master.dta", replace 
********************************************************************************
**# EDA
********************************************************************************
********************************************************************************
gl pathA "C:\Users\ghosh\OneDrive - University of Nebraska\2-Erdos\1-Climate Finance Project\Data\Figures"
************************************************************
* Descriptive Event Plots by Event Type
************************************************************

use "Finance_Disaster_Master.dta", clear
************************************************************
* Event Study Plots by Event Type
************************************************************
foreach event in "Hurricane" "Tornado" "Tropical Storm" "Thunderstorm" "Flood" "Winter Wave" "Wildfire" "Hail" {
    
    use "Finance_Disaster.dta", clear
    
    local fname = subinstr("`event'", " ", "_", .)
    
    * Identify treated counties
    gen treated = (Event_Type == "`event'" & Event_Occur == 1)
    bysort fips: egen Treated_Ever = max(treated)
    
    * Flag states that have at least one treated county
    bysort State: egen State_Treated = max(Treated_Ever)
    
    * Keep only states impacted by this event
    keep if State_Treated == 1
    drop State_Treated
    
    * Get event time for treated counties
    gen event_time = time if treated == 1
    bysort fips: egen Event_Time = min(event_time)
    drop event_time treated
    
    * Create relative time
    gen Rel_Time = time - Event_Time
    
    * Keep 12-month window for treated, keep controls
    keep if (Treated_Ever == 1 & inrange(Rel_Time, -12, 12)) | Treated_Ever == 0
    
    * For controls: stack around each cohort event time
    levelsof Event_Time if Treated_Ever == 1, local(etimes)
    
    tempfile stacked
    local first = 1
    foreach et of local etimes {
        preserve
        keep if (Treated_Ever == 1 & Event_Time == `et') | Treated_Ever == 0
        replace Rel_Time = time - `et' if Treated_Ever == 0
        keep if inrange(Rel_Time, -12, 12)
        gen cohort = `et'
        if `first' == 1 {
            save `stacked', replace
            local first = 0
        }
        else {
            append using `stacked'
            save `stacked', replace
        }
        restore
    }
    
    use `stacked', clear
    duplicates drop fips time cohort, force
    
    * Loop over both delinquency rates
    local vars "Early_Delinquency_Rate Late_Delinquency_Rate"
    foreach x of local vars {
        preserve
        collapse (mean) `x', by(Rel_Time Treated_Ever)
        
        twoway ///
            (line `x' Rel_Time if Treated_Ever==1, sort lcolor(blue) lwidth(medthick) lpattern(solid)) ///
            (line `x' Rel_Time if Treated_Ever==0, sort lcolor(green) lpattern(dash)) ///
            , xline(0, lcolor(red) lpattern(dash)) ///
            legend(label(1 "Treated") label(2 "Control") position(12) ring(1) col(2) nobox region(lstyle(none))) ///
            ytitle("`x'") xtitle("Months to Event") ///
            xlabel(-12(1)12) ///
            title("`event'") ///
            graphregion(color(white)) plotregion(fcolor(white))
        
        graph export "$pathA/`fname'_`x'.png", replace
        restore
    }
}