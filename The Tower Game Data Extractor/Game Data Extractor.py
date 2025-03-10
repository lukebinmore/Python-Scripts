import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import os
import re


errors = []


def compNames(inputs):
    alts = ["poison", "research", "-scatter"]
    values = []
    for i in range(len(inputs)):
        values.append(inputs[i].lower())
        replacements = [
            ("missle", "missile"),
            ("[]", ""),
            ("bot - dur", "bot dur"),
            ("bot - ling", "bot ling"),
            ("thunder bot cooldown", "thunder bot frequency"),
            ("bonus", "research"),
        ]
        for replacement in replacements:
            values[i] = values[i].replace(replacement[0], replacement[1])
        values[i] = re.sub(r"\b(\w+)s\b", lambda match: match.group(1), values[i])
    lists = [[values[0]], [values[1]]]

    for i in range(len(lists)):
        for alt in alts:
            lists[i].append(f"{values[i]} {alt}")
            lists[i].append(f"{alt} {values[i]}")
            lists[i].append(f"{values[i]}{alt}")

    matching_pairs = [(item1, item2) for item1 in lists[0] for item2 in lists[1] if item1 == item2]

    return bool(matching_pairs)


def checkTable(table):
    row = table.select("tr")[0]
    expected_headers = ["level", "time", "cost"]
    alternate_headers = ["value", "ability", "value (%)"]
    table_headers = []
    for header in row.select("th"):
        table_headers.append(header.get_text(strip=True).lower())

    if not all(header in table_headers for header in expected_headers):
        return False

    if not any(header in table_headers for header in alternate_headers):
        return False

    return True


def toTime(input):
    input = input.lower()
    days = hours = minutes = 0
    day_match = re.search(r"(\d+)d", input)
    hour_match = re.search(r"(\d+)h", input)
    minute_match = re.search(r"(\d)m", input)

    if day_match:
        days = int(day_match.group(1))
    if hour_match:
        hours = int(hour_match.group(1))
    if minute_match:
        minutes = int(minute_match.group(1))

    return f"{days}:{hours}:{minutes}"


skip_list = ["Card Mastery"]

script_dir = os.path.dirname(os.path.abspath(__file__))
wiki_url = "https://the-tower-idle-tower-defense.fandom.com"

all_data = requests.get(wiki_url + "/wiki/Lab_Upgrades")
soup = BeautifulSoup(all_data.content, "html.parser")
main_table = soup.select("table")[3]
sub_tables = main_table.select("table")

root = ET.Element("LabUpgrades")

for sub_table in sub_tables:
    category = sub_table.select("th")[0].get_text(strip=True)
    rows = sub_table.select("tr")
    print("------------------")
    print(f"\n###{category}###")

    for row in rows:
        cells = row.select("td")
        for cell in cells:
            link = cell.select("a")
            if not link:
                continue

            upgrade_name = link[0].get_text(strip=True)
            print(" - " + upgrade_name)

            upgrade_max = cell.select("div")[0].get_text(strip=True)
            upgrade_max = re.search(r"\d+", upgrade_max).group()

            if upgrade_name in skip_list:
                continue

            cell_base = [upgrade_name, upgrade_max]
            url = wiki_url + link[0]["href"]

            upgrade_data = BeautifulSoup(requests.get(url).content, "html.parser")
            upgrade_data = upgrade_data.select("main")[0].find_next(class_="mw-content-ltr")

            tables = upgrade_data.find_all("table", recursive=False)
            table_containers = upgrade_data.find_all(class_="tabber wds-tabber")

            table_found = False
            table = None
            for t in tables:
                if checkTable(t):
                    table = t
                    table_found = True
                    break

            for container in table_containers:
                if table_found:
                    break

                tables = container.find_all("table")
                for t in range(len(tables)):
                    if table_found:
                        break

                    if checkTable(tables[t]):
                        if table_found:
                            break

                        lis = tables[t].find_previous("ul").find_all("li")
                        for i in range(len(lis)):
                            tab_text = lis[i].get_text(strip=True)
                            if compNames([tab_text, upgrade_name]):
                                table = tables[i]
                                table_found = True
                                break

            if table is None:
                errors.append(upgrade_name)
                continue

            index = {}
            rows = table.find_all("tr")
            header_col = rows[0].find_all("th")
            header_mapping = {
                "level": ["Level", "level"],
                "time": ["Time", "time", "TIme"],
                "cost": ["Cost", "cost", "Coins", "coins"],
                "value": ["Value", "value", "Value (%)", "value (%)", "Ability", "ability"],
            }

            for i in range(len(header_col)):
                header = header_col[i].get_text(strip=True)
                for key, possible_headers in header_mapping.items():
                    if header in possible_headers:
                        index[key] = i

            for r in range(1, len(rows)):
                col = rows[r].find_all("td")
                row_data = []
                for c in range(len(col)):
                    row_data.append(col[c].get_text(strip=True))

                level_element = ET.SubElement(
                    root,
                    "Upgrade",
                    name=cell_base[0],
                    max_level=cell_base[1],
                    category=category,
                    level=row_data[index["level"]],
                    time=toTime(row_data[index["time"]]),
                    cost=row_data[index["cost"]],
                    value=row_data[index["value"]],
                )


for error in errors:
    print(error)

tree = ET.ElementTree(root)
output_file_path = os.path.join(script_dir, "lab_upgrades.xml")

with open(output_file_path, "wb") as xml_file:
    tree.write(xml_file, encoding="utf-8", xml_declaration=True)
