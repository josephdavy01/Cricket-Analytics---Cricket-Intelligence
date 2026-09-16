import asyncio
import os
import json
import random
import logging
import nodriver as uc
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from datetime import date

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def parse_html_content(html, url):

    soup = BeautifulSoup(html, "html.parser")

    # 1. Parse Personal Info Grid from Cricinfo
    info_grid = {}
    for p_tag in soup.find_all("p", class_=lambda x: x and "ds-uppercase" in x):
        label = p_tag.get_text(strip=True)
        val_tag = p_tag.find_next_sibling("span") or (p_tag.parent.find("span") if p_tag.parent else None)
        if val_tag:
            val = val_tag.get_text(strip=True)
            if val:
                info_grid[label] = val

    # Fallback to general label matching
    for tag in soup.find_all(["div", "span", "p"]):
        lbl = tag.get_text(strip=True)
        if lbl in ["Role", "Playing Role", "Batting Style", "Bowling Style"] and lbl not in info_grid:
            val_tag = tag.find_next_sibling()
            if not val_tag and tag.parent:
                val_tag = tag.parent.find_next_sibling()
            if val_tag:
                val_text = val_tag.get_text(strip=True)
                if val_text and len(val_text) > 1:
                    info_grid[lbl] = " ".join(val_text.split())

    personal_info = {
        "Role": info_grid.get("Playing Role") or info_grid.get("Role", ""),
        "Batting Style": info_grid.get("Batting Style", ""),
        "Bowling Style": info_grid.get("Bowling Style", "")
    }

    # 2. Parse Name
    name = ""
    h1 = soup.find("h1")
    if h1:
        name = h1.get_text(strip=True).replace(" HOME", "").replace(" Overview", "").strip()
    if not name and "Full Name" in info_grid:
        name = info_grid["Full Name"]
    if not name:
        name_tag = soup.find("span", class_=lambda x: x and "text-xl" in x and "font-bold" in x)
        if name_tag:
            name = name_tag.get_text(strip=True)
    if not name and url:
        slug = url.rstrip("/").split("/")[-1].rsplit("-", 1)[0]
        name = slug.replace("-", " ").title()

    # 3. Parse Image
    image_url = ""
    if name:
        slug = name.lower().replace(" ", "-").replace("'", "")
        img_tag = soup.find("img", alt=lambda x: x and (slug in x.lower() or name.lower() in x.lower()))
        if img_tag and img_tag.get("src") and not any(k in img_tag.get("src", "") for k in ["flag", "logo", "lazyimage"]):
            image_url = img_tag.get("src") or img_tag.get("data-src") or ""

    if not image_url:
        for img in soup.find_all("img"):
            alt = img.get("alt", "").lower()
            src = img.get("src", "") or img.get("data-src", "")
            if any(k in alt or k in src for k in ["flag", "logo", "lazyimage", "icon", "arrow"]):
                continue
            if "/CMS/" in src and ("square" in src or "320" in src or "160" in src):
                image_url = src
                break
    
    # Parse Statistics Tables (Career Stats: Bowling and Batting & Fielding for T20Is)
    batting_stats = {}
    bowling_stats = {}

    for table in soup.find_all("table"):
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        if not headers:
            first_row = table.find("tr")
            if first_row:
                headers = [c.get_text(strip=True) for c in first_row.find_all(["th", "td"])]
        
        if not headers or len(headers) < 3:
            continue

        # Check table type by column headers
        is_bowling = any(h in ["Wkts", "BBI", "Econ"] for h in headers)
        is_batting = any(h in ["HS", "NO", "BF", "100s", "50s"] for h in headers)

        # Fallback check preceding text/heading
        if not (is_bowling or is_batting):
            prev = table.find_previous(["p", "h2", "h3", "div"])
            if prev:
                pt = prev.get_text(strip=True).upper()
                if "BOWLING" in pt:
                    is_bowling = True
                elif "BATTING" in pt:
                    is_batting = True

        if not (is_bowling or is_batting):
            continue

        for row in table.find_all("tr"):
            cols = [td.get_text(strip=True) for td in row.find_all("td")]
            if not cols:
                continue
            fmt = cols[0].strip().upper()
            if fmt in ["T20IS", "T20I"]:
                stats_dict = {}
                for idx in range(1, min(len(headers), len(cols))):
                    key = headers[idx]
                    if key:
                        stats_dict[key] = cols[idx]
                
                if is_bowling and not bowling_stats:
                    bowling_stats = stats_dict
                elif is_batting and not batting_stats:
                    batting_stats = stats_dict
            
    return {
        "name": name,
        "profile_url": url,
        "image_url": image_url,
        "personal_info": personal_info,
        "batting_career_stats": batting_stats,
        "bowling_career_stats": bowling_stats,
    }


async def get_fresh_browser(old_browser=None):
    if old_browser:
        try:
            old_browser.stop()
        except Exception:
            pass
        await asyncio.sleep(2)
    logging.info("Starting fresh Chrome session via nodriver...")
    b = await uc.start()
    p = await b.get("https://www.cricinfo.com")
    await p.sleep(4)
    return b


def normalize_url(u):
    if not u:
        return ""
    return u.strip().replace("http://", "https://").split("?")[0].rstrip("/")


def extract_player_id(u):
    u = normalize_url(u)
    if not u:
        return ""
    slug = u.split("/")[-1]
    if "-" in slug and slug.split("-")[-1].isdigit():
        return slug.split("-")[-1]
    return slug


async def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Resolve input Cricket_squad.json
    input_file = os.path.join(base_dir, "Cricket", "Data", "Cricket_squad.json")
    if not os.path.exists(input_file):
        input_file = os.path.join(base_dir, "Data", "Cricket_squad.json")
    if not os.path.exists(input_file):
        input_file = "Cricket/Data/Cricket_squad.json"

    if not os.path.exists(input_file):
        logging.error(f"Input squad file not found at: {input_file}")
        return

    # 2. Resolve output cricket_squad_detailed.json
    output_path = os.path.join(base_dir, "Cricket", "Data", "cricket_squad_detailed.json")
    if not os.path.exists(output_path):
        output_path = os.path.join(base_dir, "Data", "cricket_squad_detailed.json")
    if not os.path.exists(os.path.dirname(output_path)):
        output_path = os.path.join(base_dir, "Cricket", "Data", "cricket_squad_detailed.json")
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    logging.info(f"Source squad file: {input_file}")
    logging.info(f"Target detailed file: {output_path}")

    # 3. Load input squad data
    with open(input_file, "r", encoding="utf-8") as f:
        squad_data = json.load(f)

    # 4. Load existing detailed data
    detailed_squad = {}
    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                detailed_squad = json.load(f)
            logging.info(f"Loaded existing detailed squad file with {len(detailed_squad)} team(s).")
        except Exception as e:
            logging.warning(f"Could not load existing detailed squad file: {e}. Starting fresh.")

    # 5. Compare both JSON files to find ONLY missing players
    missing_by_team = {}
    total_squad_players = 0
    total_existing_valid = 0

    for team_name, players in squad_data.items():
        existing_players = detailed_squad.get(team_name, [])
        existing_keys = set()
        
        for p in existing_players:
            if isinstance(p, dict) and p.get("name") and not p.get("error") and p.get("name") != "Access Denied":
                total_existing_valid += 1
                p_url = p.get("profile_url", "")
                if p_url:
                    existing_keys.add(normalize_url(p_url))
                    existing_keys.add(extract_player_id(p_url))
                    existing_keys.add(p_url.split("/")[-1])

        team_missing = []
        for player in players:
            total_squad_players += 1
            if isinstance(player, dict):
                url = player.get("profile_url") or player.get("url")
            else:
                url = str(player)
            if not url:
                continue

            u_norm = normalize_url(url)
            u_id = extract_player_id(url)
            u_slug = url.split("/")[-1]

            # Player is missing if not matched by normalized URL, ID, or slug
            if u_norm not in existing_keys and u_id not in existing_keys and u_slug not in existing_keys:
                team_missing.append(url)

        if team_missing:
            missing_by_team[team_name] = team_missing

    total_missing = sum(len(urls) for urls in missing_by_team.values())

    # 6. Display Comparison Summary
    print("\n" + "=" * 60)
    print("                SQUAD COMPARISON SUMMARY")
    print("=" * 60)
    print(f"  Total teams in Cricket_squad.json        : {len(squad_data)}")
    print(f"  Total player URLs in Cricket_squad.json  : {total_squad_players}")
    print(f"  Existing valid players in detailed JSON  : {total_existing_valid}")
    print(f"  Teams with missing players               : {len(missing_by_team)}")
    print(f"  TOTAL MISSING PLAYERS TO SCRAPE          : {total_missing}")
    print("-" * 60)
    if missing_by_team:
        for team, urls in sorted(missing_by_team.items()):
            print(f"  • {team:<26} : {len(urls)} missing")
    else:
        print("  ✓ All players from Cricket_squad.json exist in detailed JSON!")
    print("=" * 60 + "\n")

    # 7. Short-circuit if nothing missing
    if total_missing == 0:
        logging.info("All players from Cricket_squad.json are already present in cricket_squad_detailed.json. Nothing to fetch!")
        return

    # 8. Start browser ONLY when there are missing players to fetch
    browser = await get_fresh_browser()
    profiles_since_refresh = 0
    scraped_count = 0

    async def fetch_player(player_url):
        nonlocal browser
        if player_url.startswith("http://"):
            player_url = "https://" + player_url[len("http://"):]

        for attempt in range(2):
            try:
                logging.info(f"Fetching profile: {player_url} (attempt {attempt + 1})")
                p = await browser.get(player_url)
                await p.sleep(random.uniform(4.0, 6.0))

                title = await p.evaluate("document.title")
                html = await p.get_content()

                if "access denied" in title.lower() or "access denied" in html.lower() or "sec-if-cpt-container" in html:
                    logging.warning(f"Access Denied on {player_url}! Cooling down for 35s...")
                    browser = await get_fresh_browser(browser)
                    await asyncio.sleep(35)
                    continue

                for _ in range(3):
                    await p.evaluate("window.scrollBy(0, 500)")
                    await p.sleep(0.3)
                await p.evaluate("window.scrollTo(0, 0)")
                await p.sleep(0.4)

                html = await p.get_content()
                res = parse_html_content(html, player_url)
                if not res.get("name") or "access denied" in (res.get("name") or "").lower():
                    raise Exception("Page returned Access Denied or empty name")
                return res
            except Exception as e:
                logging.error(f"Error fetching {player_url} (attempt {attempt + 1}): {e}")
                if attempt == 0:
                    logging.info("Restarting browser session for retry...")
                    browser = await get_fresh_browser(browser)
                    await asyncio.sleep(20)

        return {
            "profile_url": player_url,
            "error": "Access Denied after retry"
        }

    try:
        # 9. Scrape ONLY missing players
        for team_name, missing_urls in missing_by_team.items():
            logging.info(f"Fetching {len(missing_urls)} missing player(s) for: {team_name}")
            detailed_squad.setdefault(team_name, [])

            for url in missing_urls:
                scraped_count += 1
                logging.info(f"[{scraped_count}/{total_missing}] Processing: {url} ({team_name})")
                result = await fetch_player(url)
                profiles_since_refresh += 1

                if not result.get("error") and result.get("name") and "access denied" not in result.get("name", "").lower():
                    # Remove any existing outdated/error entry for this player
                    target_id = extract_player_id(url)
                    detailed_squad[team_name] = [
                        p for p in detailed_squad[team_name]
                        if isinstance(p, dict) and extract_player_id(p.get("profile_url", "")) != target_id
                    ]
                    detailed_squad[team_name].append(result)

                    # Save progress immediately
                    with open(output_path, "w", encoding="utf-8") as f:
                        json.dump(detailed_squad, f, ensure_ascii=False, indent=4)
                    logging.info(f"Successfully saved {result.get('name')} ({team_name}) [{scraped_count}/{total_missing}]")
                else:
                    logging.warning(f"Could not retrieve valid data for {url} ({team_name})")

                # Rotate browser periodically to avoid session fatigue / rate limiting
                if profiles_since_refresh >= 25:
                    logging.info("Periodic browser refresh (25 profiles reached)...")
                    browser = await get_fresh_browser(browser)
                    profiles_since_refresh = 0
                    await asyncio.sleep(random.uniform(5.0, 8.0))
                else:
                    await asyncio.sleep(random.uniform(4.5, 7.5))

            logging.info(f"Finished team {team_name}. Rotating session...")
            browser = await get_fresh_browser(browser)
            profiles_since_refresh = 0
            await asyncio.sleep(random.uniform(5.0, 8.0))

    finally:
        try:
            browser.stop()
        except Exception:
            pass

    logging.info(f"Completed! Updated detailed squads saved to: {output_path}")


if __name__ == "__main__":
    try:
        uc.loop().run_until_complete(main())
    finally:
        os._exit(0)
