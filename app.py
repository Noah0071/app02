import streamlit as st
import requests

# ---- Config ----
PUBG_API_KEY = "ใส่ KEY ของคุณที่นี่"
PUBG_BASE = "https://api.pubg.com/shards/steam"
HEADERS = {
    "Authorization": f"Bearer {PUBG_API_KEY}",
    "Accept": "application/vnd.api+json"
}

# ---- Function ----
def get_player_id(player_name):
    url = f"{PUBG_BASE}/players?filter[playerNames]={player_name}"
    r = requests.get(url, headers=HEADERS)
    if r.status_code != 200: return None
    data = r.json()
    if "data" in data and data["data"]:
        return data["data"][0]["id"]
    return None

def get_recent_match_ids(player_id, max_matches=5):
    url = f"{PUBG_BASE}/players/{player_id}"
    r = requests.get(url, headers=HEADERS)
    if r.status_code != 200: return []
    data = r.json()
    matches = data.get("data", {}).get("relationships", {}).get("matches", {}).get("data", [])
    return [m["id"] for m in matches][:max_matches]

def get_match_stats(match_id, player_name):
    url = f"{PUBG_BASE}/matches/{match_id}"
    r = requests.get(url, headers=HEADERS)
    if r.status_code != 200: return None
    mdata = r.json()
    for p in mdata.get("included", []):
        if p["type"] == "participant" and p["attributes"]["stats"]["name"].lower() == player_name.lower():
            return p["attributes"]["stats"]
    return None

def get_avg_stats(player_name, max_matches=5):
    pid = get_player_id(player_name)
    if not pid: return None
    mids = get_recent_match_ids(pid, max_matches=max_matches)
    if not mids: return None
    kills, damage, time = 0, 0, 0
    found = 0
    for mid in mids:
        stats = get_match_stats(mid, player_name)
        if stats:
            kills += stats.get("kills", 0)
            damage += stats.get("damageDealt", 0)
            time += stats.get("timeSurvived", 0)
            found += 1
    if found == 0: return None
    return {
        "matches": found,
        "avg_kills": round(kills/found, 2),
        "avg_damage": round(damage/found, 1),
        "avg_survived": f"{int(time//60//found)}m"
    }

# ---- UI ----
st.set_page_config("PUBG Match Tracker", page_icon="🎮")
st.title("PUBG Recent Match History")

# --- ดูประวัติผู้เล่น ---
player_name = st.text_input("🔍 ค้นหา PUBG Player (ล่าสุด 5 แมตช์)", key="main_player")
if player_name:
    pid = get_player_id(player_name)
    if not pid:
        st.error("ไม่พบชื่อผู้เล่นนี้")
    else:
        mids = get_recent_match_ids(pid, max_matches=5)
        st.subheader(f"5 แมตช์ล่าสุดของ **{player_name}**")
        for mid in mids:
            st.markdown(f"**Match ID**: `{mid}`")
            stats = get_match_stats(mid, player_name)
            if stats:
                st.write({
                    "Kills": stats.get("kills", 0),
                    "Damage": stats.get("damageDealt", 0),
                    "Headshots": stats.get("headshotKills", 0),
                    "TimeSurvived": f"{int(stats.get('timeSurvived',0)//60)}m"
                })
            else:
                st.warning("ไม่พบข้อมูลของผู้เล่นในแมตช์นี้")

# --- 1v1 Compare ---
st.divider()
st.subheader("⚔️ เปรียบเทียบผู้เล่น (1v1)")
c1, c2 = st.columns(2)
with c1:
    p1 = st.text_input("Player 1", key="p1")
with c2:
    p2 = st.text_input("Player 2", key="p2")
if st.button("Compare (1v1)"):
    st.write(f"**{p1}** vs **{p2}** (เฉลี่ยจาก 5 แมตช์ล่าสุด)")
    s1 = get_avg_stats(p1)
    s2 = get_avg_stats(p2)
    if not s1 or not s2:
        st.error("ไม่พบข้อมูลครบทั้ง 2 ผู้เล่น")
    else:
        compare = [
            ["Avg Kills", s1["avg_kills"], s2["avg_kills"]],
            ["Avg Damage", s1["avg_damage"], s2["avg_damage"]],
            ["Avg Survived", s1["avg_survived"], s2["avg_survived"]],
        ]
        st.table(compare)

# --- Team vs Team ---
st.divider()
st.subheader("👥 เปรียบเทียบทีม (Team vs Team)")
team1 = st.text_area("รายชื่อทีม 1 (ใส่ชื่อผู้เล่น, คั่นด้วย comma)", "player1,player2")
team2 = st.text_area("รายชื่อทีม 2 (ใส่ชื่อผู้เล่น, คั่นด้วย comma)", "player3,player4")
if st.button("Compare Teams"):
    t1_names = [n.strip() for n in team1.split(",") if n.strip()]
    t2_names = [n.strip() for n in team2.split(",") if n.strip()]
    st.write(f"**Team 1:** {', '.join(t1_names)}")
    st.write(f"**Team 2:** {', '.join(t2_names)}")
    t1_stats, t2_stats = [], []
    for name in t1_names:
        s = get_avg_stats(name)
        if s:
            t1_stats.append(s)
    for name in t2_names:
        s = get_avg_stats(name)
        if s:
            t2_stats.append(s)
    if not t1_stats or not t2_stats:
        st.error("ต้องมีผู้เล่นแต่ละทีมอย่างน้อย 1 คน ที่มีข้อมูล")
    else:
        t1_kills = sum(s["avg_kills"] for s in t1_stats) / len(t1_stats)
        t2_kills = sum(s["avg_kills"] for s in t2_stats) / len(t2_stats)
        t1_dmg = sum(s["avg_damage"] for s in t1_stats) / len(t1_stats)
        t2_dmg = sum(s["avg_damage"] for s in t2_stats) / len(t2_stats)
        st.markdown(f"**Team 1** | Avg Kills: `{t1_kills:.2f}` | Avg Damage: `{t1_dmg:.1f}`")
        st.markdown(f"**Team 2** | Avg Kills: `{t2_kills:.2f}` | Avg Damage: `{t2_dmg:.1f}`")
        # pie chart เปรียบเทียบ kills
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()
        ax.pie([t1_kills, t2_kills], labels=["Team 1", "Team 2"], autopct='%1.1f%%', colors=["#36a2eb", "#f45b69"])
        st.pyplot(fig)

st.info("ระบบนี้ฟรี, ใช้ PUBG API Key จริงในการดึงข้อมูล (บางครั้งอาจตอบช้า)")
