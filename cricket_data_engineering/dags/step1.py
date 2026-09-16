import asyncio
import os
import sys
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


def find_browser_binary():
    import glob
    import shutil
    import subprocess

    # 1. Ask Playwright directly for its chromium executable
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            path = p.chromium.executable_path
            if path and os.path.exists(path):
                return path
    except Exception as e:
        logging.warning(f"Playwright API lookup note: {e}")

    # 2. Check system PATH binaries
    for binary in ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"]:
        path = shutil.which(binary)
        if path:
            return path

    # 3. Recursive search in playwright cache & user directories
    patterns = [
        "/home/airflow/.cache/ms-playwright/**/chrome",
        "/root/.cache/ms-playwright/**/chrome",
        os.path.expanduser("~/.cache/ms-playwright/**/chrome"),
        "/tmp/**/chrome",
    ]
    for p in patterns:
        for match in glob.glob(p, recursive=True):
            if os.path.isfile(match) and os.access(match, os.X_OK):
                return match

    # 4. Attempt auto-install via playwright if missing in container
    try:
        logging.info("Attempting on-the-fly 'playwright install chromium'...")
        subprocess.run(["playwright", "install", "chromium"], check=True, timeout=90)
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            if p.chromium.executable_path and os.path.exists(p.chromium.executable_path):
                return p.chromium.executable_path
    except Exception as ex:
        logging.warning(f"Auto-install attempt note: {ex}")

    return None


async def scrape_all_teams():
    """
    Scrapes all T20I caps pages using nodriver (undetected Chrome).
    Step 1: Visit the teams listing page and discover all team slugs.
    Step 2: Visit each team's caps page and extract player URLs.
    """
    output_dir = "/opt/airflow/Data"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "cricket_squad.json")

    # Load existing data if available to retain progress
    squad_data = {}
    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                squad_data = json.load(f)
            logging.info(f"Loaded existing data for {len(squad_data)} teams from {output_path}")
        except Exception:
            squad_data = {}
    elif os.path.exists(os.path.join(output_dir, "Cricket_squad.json")):
        try:
            with open(os.path.join(output_dir, "Cricket_squad.json"), "r", encoding="utf-8") as f:
                squad_data = json.load(f)
        except Exception:
            squad_data = {}

    # Find browser executable (e.g. Playwright Chromium installed in Docker)
    browser_kwargs = {
        "browser_args": ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
    }
    exec_path = find_browser_binary()
    if exec_path:
        logging.info(f"Using browser binary: {exec_path}")
        browser_kwargs["browser_executable_path"] = exec_path
    else:
        logging.warning("No custom browser binary found, attempting default nodriver search...")

    # Launch undetected Chrome
    browser = await uc.start(**browser_kwargs)
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
        try:
            browser.stop()
        except Exception:
            pass
        raise RuntimeError("Could not find the teams grid on the page.")

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
        try:
            browser.stop()
        except Exception:
            pass
        raise RuntimeError("No international teams found on Cricinfo teams page.")

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
            # Also save to Cricket_squad.json for backwards compatibility
            alt_path = os.path.join(output_dir, "Cricket_squad.json")
            with open(alt_path, "w", encoding="utf-8") as f:
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
    except Exception as e:
        logging.error(f"Scraper execution failed: {e}", exc_info=True)
        sys.exit(1)
