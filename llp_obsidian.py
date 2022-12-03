from ics import Calendar
import requests
import pandas as pd
import re

# Settings
## Studenplan URL CAVE: replace webcal with HTTP
cal_url = "http://lernziele.charite.de/zend/plan/ical/studiengang/Modellstudiengang2/zeitsemester/SoSe2022/fachsemester/ind/sid/10613/token/4e9f27a3bfcb-djeVz2aC"
## Lernziel-Datei aus LLP
file_lernziele = "files/export.xlsx"

only_future_events = True
ignore_holiday = True # Work-in-progress, no functionality as of now

## Obsidian settings
dailynote_format = "%Y-%m-%d"
dailynote_header = "# Uni"
target_path = "files/obsidian_export/"
write_mode = "w" # Use a+ if files already exist

## Format String for LV-names
name_regex = "(.*! )?([äöüÄÖÜ\w]{1,5}.?):\s([\w\W]*)\s\(([\w\W]*),\s([\w\W]*)\)"


# Get Calendar items and convert to DataFrame
cal = Calendar(requests.get(cal_url).text)

e_names = []
e_begin = []
for e in cal.events:
    e_names.append(e.name)
    e_begin.append(e.begin)

e_dict = {"name":e_names,"start":e_begin}
events = pd.DataFrame(e_dict)

# Basic conversions and preparatory regex to the name column
events["date"] = pd.to_datetime(events.start, utc=True, format="%Y-%m-%dT%H:%M:%S+00:00")
events["name"] = events.name.str.replace("Vorlesung (Prolog|Epilog)","VL",regex=True)
events["name"] = events.name.str.replace("Prolog/ Epilog","P/E")

# Parse LV-name using regex
lv_isHoliday = [] #returns True if event is marked as on holiday (ENTFÄLLT - Feiertag)
lv_type = []
lv_name = []
lv_modul = []
lv_mw = [] #Modulwoche
for lv in events.name:
    result = re.search(name_regex,lv)
    if result.group(1): lv_isHoliday.append(True)
    else: lv_isHoliday.append(False)
    lv_type.append(result.group(2))
    lv_name.append(result.group(3))
    lv_modul.append(result.group(4))
    lv_mw.append(result.group(5))

events["isHoliday"] = lv_isHoliday
events["lv_type"] = lv_type
events["lv_name"] = lv_name
events["lv_modul"] = lv_modul
events["lv_mw"] = lv_mw


# Import Lernziele
lz = pd.read_excel(file_lernziele)
events["Lernziele"] = ""
for i, e in events.iterrows():
    list_lz = []
    lz_select = lz.loc[lz["Veranstaltung: Titel"].str.contains(e.lv_name,regex=False)]
    for lz_e in lz_select["Lernziel"]:
        list_lz.append(lz_e)
    events["Lernziele"].iloc[i] = list_lz


# Group for Obisdian into
# Dailynote
# ├── Veranstaltung
#     ├── Lernziele

events.sort_values(by="date",inplace=True)
events_daily = events.groupby(events.date.dt.date)

for date, items in events_daily:
    print(date)
    path = target_path + date.strftime(dailynote_format) + ".md"
    # Write dailynote files 
    with open(path, write_mode, encoding="utf-8") as f:
        f.write(f"{dailynote_header}\n")
        for i, e in items.iterrows():
            f.write(f"## {e.lv_name}\n")
            for lz in e.Lernziele:
                f.write(f"- {lz}\n")