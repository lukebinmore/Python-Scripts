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


skip_list = ["Card Mastery"]

script_dir = os.path.dirname(os.path.abspath(__file__))
wiki_url = "https://the-tower-idle-tower-defense.fandom.com"

all_data = requests.get(wiki_url + "/wiki/Lab_Upgrades")
soup = BeautifulSoup(all_data.content, "html.parser")
main_table = soup.select("table")[3]
sub_tables = main_table.select("table")

root = ET.Element("LabUpgrades")

for sub_table in sub_tables:
    header = sub_table.select("th")[0].get_text(strip=True)
    sub_table_element = ET.SubElement(root, "Category", name=header)
    rows = sub_table.select("tr")
    print("------------------")
    print(f"\n###{header}###")

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

            cell_element = ET.SubElement(sub_table_element, "Upgrade", name=upgrade_name, current_level="0", max_level=upgrade_max)
            levels_element = ET.SubElement(cell_element, "Levels")
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

            index = [0, 0, 0, 0]
            rows = table.find_all("tr")
            header_col = rows[0].find_all("th")
            for i in range(len(header_col)):
                header = header_col[i].get_text(strip=True)
                match header:
                    case "Level":
                        index[0] = i
                    case "Time":
                        index[1] = i
                    case "Cost":
                        index[2] = i
                    case "Value":
                        index[3] = i
                    case "Ability":
                        index[3] = i

            for r in range(len(rows)):
                if r == 0:
                    continue
                col = rows[r].find_all("td")
                row_data = []
                for c in range(len(col)):
                    row_data.append(col[c].get_text(strip=True))

                level_element = ET.SubElement(levels_element, "Details", Level=row_data[0], Time=row_data[1], Cost=row_data[2], Value=row_data[3])


for error in errors:
    print(error)

tree = ET.ElementTree(root)
output_file_path = os.path.join(script_dir, "lab_upgrades.xml")

with open(output_file_path, "wb") as xml_file:
    tree.write(xml_file, encoding="utf-8", xml_declaration=True)
