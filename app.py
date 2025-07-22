import os
from flask import Flask, jsonify, request, send_from_directory
import requests

app = Flask(__name__, static_folder="")

PUBG_API_KEY = os.environ.get("PUBG_API_KEY")  # ใช้ API KEY ของคุณเอง
PUBG_BASE = "https://api.pubg.com/shards/steam"
HEADERS = {
    "Authorization": f"Bearer {PUBG_API_KEY}",
    "Accept": "application/vnd.api+json"
}

def get_player_id(player_name):
    url = f"{PUBG_BASE}/players?filter[playerNames]={player_name}"
    r = requests.get(url, headers=HEADERS)
    data = r.json()
    if "data" in data and data["data"]:
        return data["data"][0]["id"], data["data"][0]["attributes"]["name"]
    return None, None

def get_recent_match_ids(player_id, max_matches=5):
    url = f"{PUBG_BASE}/players/{player_id}"
    r = requests.get(url, headers=HEADERS)
    data = r.json()
    matches = data.get("data", {}).get("relationships", {}).get("matches", {}).get("data", [])
    return [m["id"] for m in matches][:max_matches]

def parse_player_stats(match_json, player_name):
    stats = {
        "weapon": "-",
        "kills": 0,
        "damage": 0,
        "dbno": 0,
        "traveled": "0.00",
        "timeAlive": "-",
        "longest": "-",
        "rank": "-",
        "team": [],
        "player": player_name,
        "match_id": match_json["data"]["id"]
    }
    included = match_json.get("included", [])
    player_part = None
    for p in included:
        if p["type"] == "participant" and p["attributes"]["stats"]["name"].lower() == player_name.lower():
            player_part = p
            break
    if not player_part:
        return stats
    s = player_part["attributes"]["stats"]
    stats.update({
        "weapon": s.get("most_damage_cause", "-"),
        "kills": s.get("kills", 0),
        "damage": s.get("damageDealt", 0),
        "dbno": s.get("DBNOs", 0),
        "traveled": f"{((s.get('rideDistance',0)+s.get('walkDistance',0))/1000):.2f}",
        "timeAlive": f"{int(s.get('timeSurvived',0)//60)}m {int(s.get('timeSurvived',0)%60)}s",
        "longest": f"{int(s.get('longestTimeSurvived',0)//60)}m",
        "rank": s.get("winPlace", "-"),
    })
    return stats

def get_match_info(match_id, player_name):
    url = f"{PUBG_BASE}/matches/{match_id}"
    r = requests.get(url, headers=HEADERS)
    mdata = r.json()
    match_info = mdata["data"]["attributes"]
    mode = match_info.get("gameMode", "-")
    mapname = match_info.get("mapName", "-")
    match_type = "Normal" if "normal" in mode else "Ranked" if "ranked" in mode else "-"
    stats = parse_player_stats(mdata, player_name)
    stats.update({
        "mode": mode,
        "type": match_type,
        "map": mapname,
    })
    return stats

@app.route("/api/matches/<player_name>")
def api_matches(player_name):
    page = int(request.args.get("page", 0))
    PER_PAGE = 5
    pid, pname = get_player_id(player_name)
    if not pid:
        return jsonify({"matches": []})
    match_ids = get_recent_match_ids(pid, max_matches=5)
    page_ids = match_ids[page*PER_PAGE:(page+1)*PER_PAGE]
    matches = []
    for mid in page_ids:
        try:
            m = get_match_info(mid, pname)
            matches.append(m)
        except Exception as e:
            continue
    return jsonify({"matches": matches})

def get_player_participant(included, player_name):
    for obj in included:
        if obj["type"] == "participant":
            stats = obj["attributes"]["stats"]
            if stats.get("name", "").lower() == player_name.lower():
                return stats
    return None

@app.route("/api/match/<match_id>")
def match_detail(match_id):
    player = request.args.get("player", "")
    if not player:
        return jsonify({"error": "missing player param"}), 400

    url = f"{PUBG_BASE}/matches/{match_id}"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code != 200:
        return jsonify({"error": "match not found"}), 404
    data = resp.json()
    attr = data["data"]["attributes"]
    map_code = attr.get("mapName", "-")

    stats = get_player_participant(data.get("included", []), player)
    if not stats:
        return jsonify({"error": "player not found in match"}), 404

    def km(v):
        return f"{float(v)/1000:.2f} km" if v else "0.00 km"
    def time_str(sec):
        return f"{int(sec//60)}m {int(sec%60)}s" if sec else "-"

    result = {
        "server": attr.get("shardId", "Steam"),
        "map": map_code,
        "damage": int(stats.get("damageDealt", 0)),
        "kills": int(stats.get("kills", 0)),
        "headshots": int(stats.get("headshotKills", 0)),
        "assists": int(stats.get("assists", 0)),
        "roadKills": int(stats.get("roadKills", 0)),
        "vehiclesDestroyed": int(stats.get("vehicleDestroys", 0)),
        "dbnos": int(stats.get("DBNOs", 0)),
        "revives": int(stats.get("revives", 0)),
        "timeAlive": time_str(stats.get("timeSurvived", 0)),
        "boosts": int(stats.get("boosts", 0)),
        "heals": int(stats.get("heals", 0)),
        "weaponsAcquired": int(stats.get("weaponsAcquired", 0)),
        "traveled": km(stats.get("rideDistance",0) + stats.get("walkDistance",0) + stats.get("swimDistance",0)),
        "walked": km(stats.get("walkDistance", 0)),
        "vehicle": km(stats.get("rideDistance", 0)),
        "swim": km(stats.get("swimDistance", 0)),
    }
    return jsonify(result)

@app.route("/api/teamstats/<match_id>")
def team_stats(match_id):
    player = request.args.get("player", "")
    url = f"{PUBG_BASE}/matches/{match_id}"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code != 200:
        return jsonify({"error": "match not found"}), 404
    data = resp.json()
    included = data.get("included", [])
    player_participant = None
    for obj in included:
        if obj["type"] == "participant":
            stats = obj["attributes"]["stats"]
            if stats.get("name", "").lower() == player.lower():
                player_participant = obj
                break
    if not player_participant:
        return jsonify({"error": "player not found"}), 404

    roster_id = None
    for obj in included:
        if obj["type"] == "roster":
            p_ids = [p["id"] for p in obj["relationships"]["participants"]["data"]]
            if player_participant["id"] in p_ids:
                roster_id = obj["id"]
                break
    if not roster_id:
        return jsonify({"error": "team not found"}), 404

    team_participants = []
    for obj in included:
        if obj["type"] == "roster" and obj["id"] == roster_id:
            p_ids = [p["id"] for p in obj["relationships"]["participants"]["data"]]
            for obj2 in included:
                if obj2["type"] == "participant" and obj2["id"] in p_ids:
                    team_participants.append(obj2)
    total_kills = sum(p["attributes"]["stats"].get("kills", 0) for p in team_participants)
    total_damage = sum(int(p["attributes"]["stats"].get("damageDealt", 0)) for p in team_participants)
    avg_distance = (
        sum(
            float(p["attributes"]["stats"].get("rideDistance", 0)) +
            float(p["attributes"]["stats"].get("walkDistance", 0)) +
            float(p["attributes"]["stats"].get("swimDistance", 0))
            for p in team_participants
        ) / len(team_participants) if team_participants else 0
    )

    team_rank = None
    for obj in included:
        if obj["type"] == "roster" and obj["id"] == roster_id:
            team_rank = obj["attributes"].get("stats", {}).get("rank", "-")
            break

    members = []
    for p in team_participants:
        s = p["attributes"]["stats"]
        members.append({
            "name": s.get("name", "-"),
            "weapon": s.get("most_damage_cause", "-"),
            "kills": s.get("kills", 0),
            "headshots": s.get("headshotKills", 0),
            "assists": s.get("assists", 0),
            "damage": int(s.get("damageDealt", 0)),
            "dbnos": s.get("DBNOs", 0),
            "traveled": f"{((s.get('rideDistance',0)+s.get('walkDistance',0))/1000):.2f} km",
            "longest": f"{int(s.get('longestTimeSurvived',0)//60)}m" if s.get('longestTimeSurvived', 0) else "-",
            "timeAlive": f"{int(s.get('timeSurvived',0)//60):02d}:{int(s.get('timeSurvived',0)%60):02d}",
        })

    return jsonify({
        "team_rank": team_rank,
        "total_kills": total_kills,
        "total_damage": total_damage,
        "avg_distance": int(avg_distance),
        "members": members,
        "player": player
    })

# TIER LOGIC
def get_tier_from_stats(stats):
    dmg = stats.get("damage", 0)
    kd = stats.get("kd", 1)
    survived_min = stats.get("survived_min", 0)
    win = stats.get("win", False)
    dbnos = stats.get("dbnos", 0)
    survived_factor = min(survived_min, 35) / 35
    score = (dmg*0.6) + (kd*15) + (survived_factor*100)
    if win and dbnos == 0:
        return "SSS+"
    if score >= 950:
        return "SSS"
    if score >= 820:
        return "SS+"
    if score >= 720:
        return "SS"
    if score >= 640:
        return "S+"
    if score >= 560:
        return "S"
    if score >= 480:
        return "A+"
    if score >= 420:
        return "A"
    if score >= 360:
        return "B+"
    if score >= 290:
        return "B"
    if score >= 240:
        return "C+"
    if score >= 180:
        return "C"
    if score >= 120:
        return "D+"
    if score >= 60:
        return "D"
    return "E"

@app.route("/api/rankings/<match_id>")
def total_rankings(match_id):
    player = request.args.get("player", "")
    url = f"{PUBG_BASE}/matches/{match_id}"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code != 200:
        return jsonify({"error": "match not found"}), 404
    data = resp.json()
    included = data.get("included", [])
    participants = []
    roster_part = {}
    team_number_table = {}
    for obj in included:
        if obj["type"] == "roster":
            team_id = obj["id"]
            team_rank = obj["attributes"].get("stats", {}).get("rank", "-")
            team_number_table[team_id] = team_rank
            for p in obj["relationships"]["participants"]["data"]:
                roster_part[p["id"]] = team_id
    for obj in included:
        if obj["type"] == "participant":
            s = obj["attributes"]["stats"]
            damage = int(s.get("damageDealt", 0))
            kills = s.get("kills", 0)
            kd = kills
            survived_min = int(s.get("timeSurvived", 0)) // 60
            win = s.get("winPlace", 999) == 1
            dbnos = s.get("DBNOs", 0)
            team_id = roster_part.get(obj["id"], "-")
            tier = get_tier_from_stats({
                "damage": damage,
                "kd": kd,
                "survived_min": survived_min,
                "win": win,
                "dbnos": dbnos
            })
            participants.append({
                "name": s.get("name", "-"),
                "weapon": s.get("most_damage_cause", "-"),
                "kills": kills,
                "headshots": s.get("headshotKills", 0),
                "assists": s.get("assists", 0),
                "damage": damage,
                "dbnos": dbnos,
                "traveled": f"{((s.get('rideDistance',0)+s.get('walkDistance',0))/1000):.2f}km",
                "tier": tier,
                "timeAlive": f"{int(s.get('timeSurvived',0)//60):02d}:{int(s.get('timeSurvived',0)%60):02d}",
                "rank": s.get("winPlace", 999),
                "alive": dbnos == 0 and win,
                "team": team_number_table.get(team_id, team_id)
            })
    participants.sort(key=lambda x: x["rank"])
    for idx, p in enumerate(participants, 1):
        p["no"] = idx
        p["highlight"] = (p["name"].lower() == player.lower())
    return jsonify({"rankings": participants, "player": player})

@app.route("/api/playercompare")
def api_player_compare():
    player1 = request.args.get("player1")
    player2 = request.args.get("player2")
    def fetch_stat(name):
        pid, _ = get_player_id(name)
        if not pid:
            return {"name": name, "kd": 0, "damage": 0, "survived": 0, "tier": "E"}
        mids = get_recent_match_ids(pid, max_matches=5)
        kills, damage, survived, wins, dbnos = 0, 0, 0, 0, 0
        for mid in mids:
            url = f"{PUBG_BASE}/matches/{mid}"
            r = requests.get(url, headers=HEADERS)
            if r.status_code != 200: continue
            mdata = r.json()
            for part in mdata.get("included", []):
                if part["type"]=="participant" and part["attributes"]["stats"]["name"].lower()==name.lower():
                    s = part["attributes"]["stats"]
                    kills += s.get("kills",0)
                    damage += s.get("damageDealt",0)
                    survived += s.get("timeSurvived",0)
                    if s.get("winPlace",999) == 1:
                        wins += 1
                    dbnos += s.get("DBNOs",0)
        n = len(mids) or 1
        kd = kills / n
        survived_min = int(survived / 60 / n)
        win = wins == n and n > 0
        tier = get_tier_from_stats({
            "damage": damage/n,
            "kd": kd,
            "survived_min": survived_min,
            "win": win,
            "dbnos": dbnos // n
        })
        stat = {
            "name": name,
            "kd": round(kd,2),
            "damage": int(damage/n),
            "survived": f"{survived_min}m",
            "tier": tier
        }
        return stat
    stat1 = fetch_stat(player1)
    stat2 = fetch_stat(player2)
    tier_order = ["E","D","D+","C","C+","B","B+","A","A+","S","S+","SS","SS+","SSS","SSS+"]
    win1 = 50 + 8*(tier_order.index(stat1["tier"])-tier_order.index(stat2["tier"]))
    win1 = min(max(win1,5),95)
    win2 = 100 - win1
    return jsonify({"player1":stat1,"player2":stat2,"win1":win1,"win2":win2})

@app.route("/api/teamcompare")
def api_team_compare():
    team1 = [n.strip() for n in request.args.get("team1", "").split(",") if n.strip()]
    team2 = [n.strip() for n in request.args.get("team2", "").split(",") if n.strip()]
    def get_team_stats(names):
        kills, damage, survived, wins, dbnos, count = 0,0,0,0,0,0
        members = []
        for n in names:
            if not n: continue
            pid, _ = get_player_id(n)
            if not pid: continue
            mids = get_recent_match_ids(pid, max_matches=5)
            k,d,s,w,db = 0,0,0,0,0
            for mid in mids:
                url = f"{PUBG_BASE}/matches/{mid}"
                r = requests.get(url, headers=HEADERS)
                if r.status_code != 200: continue
                mdata = r.json()
                for part in mdata.get("included", []):
                    if part["type"]=="participant" and part["attributes"]["stats"]["name"].lower()==n.lower():
                        sdata = part["attributes"]["stats"]
                        k += sdata.get("kills",0)
                        d += sdata.get("damageDealt",0)
                        s += sdata.get("timeSurvived",0)
                        if sdata.get("winPlace",999)==1:
                            w += 1
                        db += sdata.get("DBNOs",0)
            n_match = len(mids) or 1
            kills += k/n_match
            damage += d/n_match
            survived += s/n_match
            wins += w
            dbnos += db/n_match
            members.append(n)
            count += 1
        avg_kd = round(kills/(count or 1),2)
        avg_damage = int(damage/(count or 1))
        avg_survived_min = int((survived/(count or 1))//60)
        avg_win = wins == count and count > 0
        avg_dbnos = int(dbnos/(count or 1))
        tier = get_tier_from_stats({
            "damage": avg_damage,
            "kd": avg_kd,
            "survived_min": avg_survived_min,
            "win": avg_win,
            "dbnos": avg_dbnos
        })
        return {
            "name": " / ".join(members[:2]) + (" ..." if len(members)>2 else ""),
            "kd": avg_kd,
            "damage": avg_damage,
            "survived": f"{avg_survived_min}m",
            "tier": tier,
            "members": members
        }
    t1 = get_team_stats(team1)
    t2 = get_team_stats(team2)
    tier_order = ["E","D","D+","C","C+","B","B+","A","A+","S","S+","SS","SS+","SSS","SSS+"]
    win1 = 50 + 8*(tier_order.index(t1["tier"])-tier_order.index(t2["tier"]))
    win1 = min(max(win1,5),95)
    win2 = 100 - win1
    return jsonify({"team1":t1,"team2":t2,"win1":win1,"win2":win2, "members1": t1["members"], "members2": t2["members"]})

# ----------- Static file serving -----------
@app.route("/")
def root():
    return send_from_directory(".", "index.html")
@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(".", path)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000, threaded=True)
