import os
import json
import glob
import logging
import argparse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Default file paths relative to script location
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Squad JSON location
DEFAULT_SQUAD_JSON = os.path.join(BASE_DIR, "Cricket", "Data", "cricket_squad_detailed.json")
if not os.path.exists(DEFAULT_SQUAD_JSON):
    DEFAULT_SQUAD_JSON = os.path.join(BASE_DIR, "Data", "cricket_squad_detailed.json")

# Match JSON directory
DEFAULT_JSON_DIR = os.path.join(BASE_DIR, "t20s_json")
if not os.path.exists(DEFAULT_JSON_DIR):
    DEFAULT_JSON_DIR = os.path.join(BASE_DIR, "t20s_json_2024_plus")
if not os.path.exists(DEFAULT_JSON_DIR):
    DEFAULT_JSON_DIR = os.path.join(BASE_DIR, "Data")

# Specific registry ID overrides (handles cases where a name was previously misassigned)
REGISTRY_ID_MAP = {
    "5d1e7582": "Kusal Mendis",        # Balapuwaduge Kusal Gimhan Mendis (WK)
    "08548b13": "Kamindu Mendis",      # Pasqual Handi Kamindu Dilanka Mendis
    "4ec96094": "Ross Adair",          # George Ross Adair
    "fc55ec67": "Mark Adair",          # Mark Richard Adair
    "85e0cf10": "Prasidh Krishna",     # Murali Prasidh Krishna
}

# Explicit overrides for special, initial, or multi-word cases
EXPLICIT_MAP = {
    # India
    "M Prasidh Krishna": "Prasidh Krishna",
    "V Kohli": "Virat Kohli",
    "RG Sharma": "Rohit Sharma",
    "M Shahrukh Khan": "Shahrukh Khan",
    "RK Singh": "Rinku Singh",
    "SB Dubey": "Shubham Dubey",
    "SR Dubey": "Saurabh Dubey",
    "SN Khan": "Sarfaraz Khan",
    "MP Yadav": "Mayank Yadav",
    "MD Choudhary": "Mukul Choudhary",
    "CV Varun": "Varun Chakravarthy",
    "Varun Chakaravarthy": "Varun Chakravarthy",
    "R Smaran": "Smaran Ravichandran",
    "Rasikh Salam": "Rasikh Salam Dar",
    "V Suryavanshi": "Vaibhav Sooryavanshi",
    "B Sai Sudharsan": "Sai Sudharsan",
    "KK Ahmed": "Khaleel Ahmed",
    "JM Sharma": "Jitesh Sharma",
    "RS Ghosh": "Ramakrishna Ghosh",
    "Ramakrishna Shekhar Ghosh": "Ramakrishna Ghosh",
    # England
    "JC Buttler": "Jos Buttler",
    "JM Bairstow": "Jonny Bairstow",
    "MM Ali": "Moeen Ali",
    "AU Rashid": "Adil Rashid",
    "CJ Jordan": "Chris Jordan",
    "AAP Atkinson": "Gus Atkinson",
    "BA Carse": "Brydon Carse",
    "BM Duckett": "Ben Duckett",
    "DR Mousley": "Dan Mousley",
    "HC Brook": "Harry Brook",
    "JA Turner": "John Turner",
    "JC Archer": "Jofra Archer",
    "JC Tongue": "Josh Tongue",
    "JG Bethell": "Jacob Bethell",
    "JL Smith": "Jamie Smith",
    "JM Cox": "Jordan Cox",
    "LA Dawson": "Liam Dawson",
    "LS Livingstone": "Liam Livingstone",
    "MA Wood": "Mark Wood",
    "MJ Potts": "Matthew Potts",
    "PD Salt": "Phil Salt",
    "RJW Topley": "Reece Topley",
    "SM Curran": "Sam Curran",
    "WG Jacks": "Will Jacks",
    "DA Payne": "David Payne",
    # Sri Lanka
    "AD Mathews": "Angelo Mathews",
    "PWH de Silva": "Wanindu Hasaranga",
    "MDKJ Perera": "Kusal Perera",
    "BKG Mendis": "Kusal Mendis",
    "PHKD Mendis": "Kamindu Mendis",
    "WIA Fernando": "Avishka Fernando",
    "AM Fernando": "Asitha Fernando",
    "B Rajapaksa": "Bhanuka Rajapaksa",
    "PBB Rajapaksa": "Bhanuka Rajapaksa",
    "P Nissanka": "Pathum Nissanka",
    "KIC Asalanka": "Charith Asalanka",
    "LD Chandimal": "Dinesh Chandimal",
    "MADI Hemantha": "Dushan Hemantha",
    "MD Shanaka": "Dasun Shanaka",
    "MNK Fernando": "Nuwanidu Fernando",
    "PM Liyanagamage": "Pramod Madushan",
    "PVD Chameera": "Dushmantha Chameera",
    # South Africa
    "HE van der Dussen": "Rassie van der Dussen",
    "PWA Mulder": "Wiaan Mulder",
    "Quinton De Kock": "Quinton de Kock",
    "RA Herman": "Rubin Hermann",
    "Tony De Zorzi": "Tony de Zorzi",
    "Lhuan Dre Pretorius": "Lhuan-dre Pretorius",
    # Scotland
    "Brandon Mcmullen": "Brandon McMullen",
    "Christopher Mcbride": "Christopher McBride",
    "Finlay Mccreath": "Finlay McCreath",
    "HG Munsey": "George Munsey",
    "MW Jones": "Michael Jones",
    "MA Jones": "Michael Jones",
    # Ireland
    "GR Adair": "Ross Adair",
    # Australia
    "C Green": "Cameron Green",
    # New Zealand
    "W O'Rourke": "Will O'Rourke",
    "SPD Smith": "Steven Smith",
    "MJ Santner": "Mitchell Santner",
    "KD Clarke": "Katene Clarke",
    "KDC Clarke": "Kristian Clarke",
    # Zimbabwe
    "AG Cremer": "Graeme Cremer",
    "M Faraz Akram": "Faraz Akram",
    # Netherlands
    "AT Nidamanuru": "Teja Nidamanuru",
    # Namibia
    "MG Erasmus": "Gerhard Erasmus",
    # Oman
    "B Siddharth": "Siddharth Bukkapatnam",
    "LN Saishiv": "Narayan Saishiv",
    # United Arab Emirates
    "J Figy John": "Jonathan Figy",
    "SS Kang": "Simranjeet Singh",
    "Waseem Muhammad": "Muhammad Waseem",
    # Pakistan
    "Agha Salman": "Salman Agha",
    "Sufiyan Muqeem": "Sufyan Moqim",
    "B Bhandari": "Binod Bhandari",
    "Zuhaib Zubair": "Muhammad Zuhaib",
    "K Macheka": "Kudakwashe Macheka",
    "O Muzondo": "Owen Muzondo",
    "TZ Chataira": "Takudzwa Chataira",
    "WT Mubayiwa": "Wallace Mubayiwa",
    "R Mupfudza": "Rodney Mupfudza",
    # Associate / other
    "Yasir Ali Chowdhury": "Yasir Ali",
    "Sompal Kami": "Sompal Kami",
    "Karan KC": "Karan KC",
}

def load_squad_data(squad_path):
    with open(squad_path, 'r', encoding='utf-8') as f:
        squad_data = json.load(f)

    squad_players_by_team = {}
    all_squad_names = set()

    for team, players in squad_data.items():
        squad_players_by_team[team] = []
        for p in players:
            if isinstance(p, dict) and 'name' in p:
                fn = p['name'].strip().replace('\u2019', "'")
                if not fn or any(x in fn.lower() for x in ['press space', 'site can', 'overview', 'home', '404', 'not found', 'error']):
                    url = p.get('profile_url', '')
                    if url:
                        slug = url.rstrip('/').split('/')[-1].rsplit('-', 1)[0]
                        fn = ' '.join(w.capitalize() for w in slug.split('-'))
                        if fn.startswith('O '):
                            fn = "O'" + fn[2:]
                        elif fn.startswith('D '):
                            fn = "D'" + fn[2:]
                if fn:
                    squad_players_by_team[team].append(fn)
                    all_squad_names.add(fn)

    return squad_players_by_team, all_squad_names

def build_player_name_map(json_dir, squad_players_by_team, all_squad_names):
    json_files = glob.glob(os.path.join(json_dir, "*.json"))
    json_players = set()
    player_teams = {}

    for jf in json_files:
        with open(jf, 'r', encoding='utf-8') as f:
            data = json.load(f)
            players = data.get('info', {}).get('players', {})
            for team, plist in players.items():
                for p in plist:
                    json_players.add(p)
                    if p not in player_teams:
                        player_teams[p] = set()
                    player_teams[p].add(team)

    name_map = {}

    for jp in sorted(list(json_players)):
        if jp in EXPLICIT_MAP:
            name_map[jp] = EXPLICIT_MAP[jp]
            continue

        if jp in all_squad_names:
            name_map[jp] = jp
            continue

        teams = player_teams.get(jp, set())
        team_squad_players = []
        for t in teams:
            if t in squad_players_by_team:
                team_squad_players.extend(squad_players_by_team[t])

        matched_fn = None
        jp_tokens = jp.replace('-', ' ').split()
        jp_last = jp_tokens[-1].lower()
        jp_first_char = jp_tokens[0][0].lower()

        # 1. Match within team by last name AND first initial
        candidates = [fn for fn in team_squad_players if fn.split()[-1].lower() == jp_last and fn.split()[0][0].lower() == jp_first_char]
        if len(candidates) == 1:
            matched_fn = candidates[0]

        # 2. Match across all squad names by last name AND first initial
        if not matched_fn:
            candidates = [fn for fn in all_squad_names if fn.split()[-1].lower() == jp_last and fn.split()[0][0].lower() == jp_first_char]
            if len(candidates) == 1:
                matched_fn = candidates[0]

        # 3. Match by token subset within team (e.g. non-initial tokens match)
        if not matched_fn:
            non_initial_tokens = [t.lower() for t in jp_tokens if len(t) > 1]
            if non_initial_tokens:
                team_cands = [
                    fn for fn in team_squad_players
                    if all(t in fn.lower().replace('-', ' ').split() for t in non_initial_tokens)
                ]
                if len(team_cands) == 1:
                    matched_fn = team_cands[0]

        # 4. Match by token subset across all squads
        if not matched_fn:
            non_initial_tokens = [t.lower() for t in jp_tokens if len(t) > 1]
            if non_initial_tokens:
                all_cands = [
                    fn for fn in all_squad_names
                    if all(t in fn.lower().replace('-', ' ').split() for t in non_initial_tokens)
                ]
                if len(all_cands) == 1:
                    matched_fn = all_cands[0]

        name_map[jp] = matched_fn if matched_fn else jp

    return name_map

def replace_player_names(obj, mapping):
    if isinstance(obj, dict):
        new_dict = {}
        for k, v in obj.items():
            new_k = mapping.get(k, k)
            new_v = replace_player_names(v, mapping)
            new_dict[new_k] = new_v
        return new_dict
    elif isinstance(obj, list):
        return [replace_player_names(item, mapping) for item in obj]
    elif isinstance(obj, str):
        return mapping.get(obj, obj)
    else:
        return obj

def main():
    parser = argparse.ArgumentParser(description="Update player names in cricket match JSON files.")
    parser.add_argument("--dir", default=DEFAULT_JSON_DIR, help=f"Directory of match JSON files (default: {DEFAULT_JSON_DIR})")
    parser.add_argument("--squad", default=DEFAULT_SQUAD_JSON, help=f"Path to squad JSON (default: {DEFAULT_SQUAD_JSON})")
    parser.add_argument("--dry-run", action="store_true", help="Build and show mapping without modifying files")
    args = parser.parse_args()

    logging.info(f"Loading squad data from: {args.squad}")
    squad_players_by_team, all_squad_names = load_squad_data(args.squad)
    logging.info(f"Loaded {len(squad_players_by_team)} teams with {len(all_squad_names)} unique squad players.")

    logging.info(f"Building player name map from JSON files in: {args.dir}")
    name_map = build_player_name_map(args.dir, squad_players_by_team, all_squad_names)

    replacements = {k: v for k, v in name_map.items() if k != v}
    logging.info(f"Created general mapping with {len(replacements)} player name replacements out of {len(name_map)} total players.")

    json_files = glob.glob(os.path.join(args.dir, "*.json"))
    logging.info(f"Processing {len(json_files)} JSON files...")

    updated_count = 0
    sample_file_replacements = {}

    for jf in json_files:
        with open(jf, 'r', encoding='utf-8') as f:
            data = json.load(f)

        file_map = dict(name_map)
        people = data.get('info', {}).get('registry', {}).get('people', {})
        for curr_name, pid in people.items():
            if pid in REGISTRY_ID_MAP:
                target = REGISTRY_ID_MAP[pid]
                if curr_name != target:
                    file_map[curr_name] = target

        actual_file_replaces = {k: v for k, v in file_map.items() if k != v and (k in str(data))}
        if actual_file_replaces:
            for k, v in actual_file_replaces.items():
                if k not in sample_file_replacements:
                    sample_file_replacements[k] = v

        if args.dry_run:
            test_data = replace_player_names(data, file_map)
            if test_data != data:
                updated_count += 1
            continue

        updated_data = replace_player_names(data, file_map)
        if updated_data != data:
            with open(jf, 'w', encoding='utf-8') as f:
                json.dump(updated_data, f, indent=2, ensure_ascii=False)
            updated_count += 1

    if args.dry_run:
        logging.info("Dry-run mode enabled. Sample replacements:")
        for k in sorted(list(sample_file_replacements.keys()))[:30]:
            logging.info(f"  {k} -> {sample_file_replacements[k]}")
        logging.info(f"Dry-run complete. Would update {updated_count} out of {len(json_files)} JSON files.")
    else:
        logging.info(f"Successfully updated {updated_count} out of {len(json_files)} JSON files.")

if __name__ == '__main__':
    main()