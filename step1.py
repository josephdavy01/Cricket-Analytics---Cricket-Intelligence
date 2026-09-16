import asyncio
import os
import json
import random
import logging
import nodriver as uc
from urllib.parse import urljoin
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

TEAMS_PAGE = "https://www.cricinfo.com/team"
CAPS_SUFFIX = "caps/twenty20-international-3"


async def scrape_all_teams():
    """
    Scrapes all T20I caps pages using nodriver (undetected Chrome).
    Step 1: Visit the teams listing page and discover all team slugs.
    Step 2: Visit each team's caps page and extract player URLs.
    """
    output_dir = os.path.join("Cricket", "Data")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "Cricket_squad.json")

    # Load existing data if available to retain progress
    squad_data = {}
    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                squad_data = json.load(f)
            logging.info(f"Loaded existing data for {len(squad_data)} teams from {output_path}")
        except Exception:
            squad_data = {}

    # Launch undetected Chrome
    browser = await uc.start()
    page = await browser.get(TEAMS_PAGE)

    # ----------------------------------------------------------
    # Step 1: Visit teams page and discover all team slugs
    # ----------------------------------------------------------
    logging.info(f"Discovering teams from: {TEAMS_PAGE}")
    await page.sleep(5)

    title = await page.evaluate("document.title")
    logging.info(f"Teams page title: {title}")

    html = await page.get_content()
    soup = BeautifulSoup(html, "html.parser")

    # Extract team links ONLY from the FIRST ds-grid (international teams).
    # Later grids contain franchise / women's teams we don't want.
    first_grid = soup.select_one("div.ds-grid")
    if not first_grid:
        logging.error("Could not find the teams grid on the page — aborting.")
        browser.stop()
        return

    team_urls = {}
    for a_tag in first_grid.select('a[href^="/team/"]'):
        href = a_tag.get("href", "")  # e.g. /team/india-6
        if not href or href == "/team":
            continue
        slug = href.strip("/").replace("team/", "")  # e.g. india-6
        # Get team name from the span inside the link
        span = a_tag.select_one("span")
        team_name = span.get_text(strip=True) if span else slug.rsplit("-", 1)[0].replace("-", " ").title()
        team_urls[team_name] = slug

    logging.info(f"Discovered {len(team_urls)} international teams: {list(team_urls.keys())}")

    if not team_urls:
        logging.error("No teams found — aborting.")
        browser.stop()
        return

    # Check if all teams are already collected
    teams_to_scrape = [name for name in team_urls if not (name in squad_data and len(squad_data[name]) > 0)]
    if not teams_to_scrape:
        logging.info("All teams are already scraped and saved in JSON! Stopping.")
        try:
            browser.stop()
        except Exception:
            pass
        return

    # ----------------------------------------------------------
    # Step 2: Scrape each team's caps page
    # ----------------------------------------------------------
    for team_name, slug in team_urls.items():
        # Skip if this team is already scraped
        if team_name in squad_data and len(squad_data[team_name]) > 0:
            logging.info(f"{team_name} already has {len(squad_data[team_name])} players, skipping...")
            continue

        team_page_url = f"https://www.cricinfo.com/team/{slug}"
        caps_url = f"https://www.cricinfo.com/cricketers/team/{slug}/{CAPS_SUFFIX}"
        logging.info(f"Scraping {team_name}: {team_page_url} → {caps_url}")
        try:
            # Visit the team's main page first (natural navigation)
            page = await browser.get(team_page_url)
            await page.sleep(random.randint(3, 5))

            # Now navigate to the caps page
            page = await browser.get(caps_url)
            await page.sleep(random.randint(5, 8))

            title = await page.evaluate("document.title")
            logging.info(f"Page title: {title}")

            if "access denied" in title.lower():
                logging.warning(f"Blocked for {team_name}, waiting 30s and retrying...")
                await page.sleep(30)
                # Go back to team page, then retry caps
                page = await browser.get(team_page_url)
                await page.sleep(random.randint(3, 5))
                page = await browser.get(caps_url)
                await page.sleep(random.randint(5, 8))
                title = await page.evaluate("document.title")
                logging.info(f"Retry title: {title}")

            # Scroll to trigger lazy loading
            for _ in range(8):
                await page.evaluate("window.scrollBy(0, 600)")
                await page.sleep(0.3)
            await page.evaluate("window.scrollTo(0, 0)")
            await page.sleep(1)

            # Parse HTML
            html = await page.get_content()
            soup = BeautifulSoup(html, "html.parser")

            seen_urls = set()
            players = []

            # Only extract player links from the caps table (avoids sidebar widgets like "Most Viewed Players")
            caps_table = soup.select_one("table")
            container = caps_table if caps_table else soup

            for a_tag in container.select("a[href*='/cricketers/']"):
                href = a_tag.get("href", "")
                if href and "/cricketers/" in href and href not in seen_urls:
                    if "/team/" in href or "/caps/" in href:
                        continue
                    parts = href.rstrip("/").split("-")
                    if parts and parts[-1].isdigit():
                        seen_urls.add(href)
                        full_url = urljoin("https://www.cricinfo.com", href)
                        players.append(full_url)

            squad_data[team_name] = players
            logging.info(f"Found {len(players)} players for {team_name}")

            # Save immediately to JSON after scraping each team
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(squad_data, f, ensure_ascii=False, indent=4)
            logging.info(f"Updated {output_path} with {team_name}")

            await page.sleep(random.randint(5, 10))

        except Exception as ex:
            logging.error(f"Error scraping {team_name}: {ex}")
            if team_name not in squad_data:
                squad_data[team_name] = []

    try:
        browser.stop()
    except Exception:
        pass

    logging.info(f"All scraping completed. File saved at {output_path}")
    total_players = sum(len(v) for v in squad_data.values())
    logging.info(f"Total: {len(squad_data)} teams, {total_players} players")


if __name__ == "__main__":
    try:
        uc.loop().run_until_complete(scrape_all_teams())
    finally:
        os._exit(0)