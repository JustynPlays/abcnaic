import sqlite3

conn = sqlite3.connect('c:/xampp2/htdocs/ABC-PWA Ichatbot/db/drcare.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute('SELECT COUNT(*) as count FROM appointments')
count = c.fetchone()[0]
print(f'Total appointments: {count}')

if count > 0:
    c.execute('SELECT id, patient_name, appointment_date, appointment_time, status FROM appointments LIMIT 5')
    rows = c.fetchall()
    print('\nSample appointments:')
    for r in rows:
        print(f'  ID:{r["id"]} {r["patient_name"]} on {r["appointment_date"]} at {r["appointment_time"]} - {r["status"]}')
else:
    print('\nNo appointments found in database.')

conn.close()
