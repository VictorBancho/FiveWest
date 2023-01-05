import sqlite3

conn = sqlite3.connect('bar_db')
cur = conn.cursor()

cur.execute('''
          CREATE TABLE IF NOT EXISTS patrons
          ([patron_id] INTEGER PRIMARY KEY, [patron_name] TEXT, [patron_age] INTEGER, [patron_bodyweight] INTEGER)
          ''')
cur.execute('''
          CREATE TABLE IF NOT EXISTS drinks
          ([drink_id] INTEGER PRIMARY KEY, [drink_name] TEXT, [drink_ABV] INTEGER)
          ''')
cur.execute('''
          CREATE TABLE IF NOT EXISTS alcohols
          ([alcohol_type] TEXT PRIMARY KEY, [drink_ABV] INTEGER)
          ''')


cur.execute('''
          CREATE TABLE IF NOT EXISTS orders
          ([order_id] INTEGER PRIMARY KEY, [patron_id] INTEGER, [drink_id] INTEGER)
          ''')
# cur.execute('''DROP TABLE current''')
cur.execute('''
          CREATE TABLE IF NOT EXISTS current
          ([patron_id] INTEGER PRIMARY KEY, [patron_name] TEXT, [blood_alcohol_con] REAL)
          ''')


# cur.execute("INSERT INTO patrons (patron_id, patron_name, patron_age, patron_bodyweight) VALUES (?, ?, ?, ?)",
#             ('01', 'Greg', '22',  '80' )
#             )

# cur.execute("INSERT INTO patrons (patron_id, patron_name, patron_age, patron_bodyweight) VALUES (?, ?, ?, ?)",
#             ('07', 'Mia', '24',  '100' )
            # )

conn.commit()
conn.close()