import fastf1
import pandas as pd
import mysql.connector
import yaml

# =========================
# config読み込み
# =========================
def load_config(path="config/config.yml"):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

config = load_config()

# =========================
# FastF1設定
# =========================
fastf1.Cache.enable_cache(config['app']['cache_dir'])

# =========================
# DB接続
# =========================
db = config['database']

conn = mysql.connector.connect(
    host=db['host'],
    port=db['port'],
    user=db['user'],
    password=db['password'],
    database=db['name']
)

cursor = conn.cursor()

# =========================
# timedelta → 秒変換
# =========================
def to_sec(td):
    return td.total_seconds() if pd.notnull(td) else None

# =========================
# DB保存
# =========================
def save_laps(df, season, gp, session):
    for _, row in df.iterrows():
        cursor.execute("""
            INSERT INTO lap_times (
                season, gp_name, session, driver, lap_number,
                lap_time, sector1, sector2, sector3, speed_trap,position
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE
                lap_time=VALUES(lap_time),
                sector1=VALUES(sector1),
                sector2=VALUES(sector2),
                sector3=VALUES(sector3),
                speed_trap=VALUES(speed_trap),
                position=VALUES(position)

        """, (
            season,
            gp,
            session,
            row['Driver'],
            int(row['LapNumber']) if pd.notnull(row['LapNumber']) else None

            to_sec(row['LapTime']),
            to_sec(row['Sector1Time']),
            to_sec(row['Sector2Time']),
            to_sec(row['Sector3Time']),

            row['SpeedST'] if pd.notnull(row['SpeedST']) else None,
            int(row['Position']) if pd.notnull(row['Position']) else None
        ))

    conn.commit()

# =========================
# セッション処理
# =========================
def fetch_session(season, gp, session_code):
    print(f"Loading {season} {gp} [{session_code}]")

    session = fastf1.get_session(season, gp, session_code)
    session.load()

    laps = session.laps

    df = laps[[
        'Driver',
        'LapNumber',
        'LapTime',
        'Sector1Time',
        'Sector2Time',
        'Sector3Time',
        'SpeedST',
        'Position'
    ]].copy()

    save_laps(df, season, gp, session_code)

# =========================
# メイン
# =========================
def main():
    season = config['f1']['season']
    gps = config['f1']['gps']
    sessions = config['f1']['sessions']

    for gp in gps:
        for s in sessions:
            try:
                fetch_session(season, gp, s)
            except Exception as e:
                print(f"Error: {gp} {s} -> {e}")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()