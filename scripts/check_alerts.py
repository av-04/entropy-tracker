import sqlite3

def main():
    conn = sqlite3.connect("C:/Projects/entropy/entropy.db")
    cursor = conn.cursor()
    cursor.execute("SELECT module_path, entropy_score, knowledge_score, dep_score, churn_score, age_score, bus_factor FROM module_entropy WHERE module_path LIKE '%gateway.py' OR module_path LIKE '%tokens.py' OR module_path LIKE '%connector.py' ORDER BY entropy_score DESC LIMIT 15")
    print("path, entropy, kno, dep, churn, age, bus")
    for row in cursor.fetchall():
        print(f"{row[0]}: {row[1]:.1f} | kno:{row[2]:.0f} dep:{row[3]:.0f} churn:{row[4]:.0f} age:{row[5]:.0f} bus:{row[6]}")

if __name__ == "__main__":
    main()
