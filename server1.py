# הגדרות ותצורה
import socketserver # ספריה שמאפשרת להקים שרתים
import json #לעבודה עם נתונים בפורמט
import mysql.connector # ספרייה של MySQL לחיבור לבסיס נתונים
import bcrypt # ספרייה להצפנת סיסמאות בצורה מאובטחת
import os #לשימוש במשתני סביבה וקבצי מערכת
from datetime import datetime, timezone #  לעבודה עם תאריכים וזמנים

#  מילון עם פרטי ההתחברות
DB_CONFIG = {
    'host': os.getenv('REG_DB_HOST', 'localhost'),
    'port': int(os.getenv('REG_DB_PORT', 3307)),
    'user': os.getenv('REG_DB_USER', 'root'),
    'password': os.getenv('REG_DB_PASS', 'MySQL!Kurkin1975'),
    'database': os.getenv('REG_DB_NAME', 'login')
}
USERS_TABLE = 'users' #  שם טבלת המשתמשים בבסיס הנתונים

# מחזירה חיבור חדש לבסיס הנתונים עם הפרמטרים שב־DB_CONFIG.
def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

# מוודאת שהטבלה users קיימת, ואם לא — יוצרת אותה
def ensure_users_table():
    sql = f"""
    CREATE TABLE IF NOT EXISTS {USERS_TABLE} (
        id INT AUTO_INCREMENT PRIMARY KEY, # מזהה משתמש (אוטומטי).
        username VARCHAR(150) NOT NULL UNIQUE, # שם משתמש (ייחודי)
        email VARCHAR(255) NOT NULL UNIQUE, # דוא״ל (ייחודי)
        password_hash VARCHAR(255) NOT NULL, # הסיסמה בהצפנה
        created_at DATETIME NOT NULL # תאריך יצירה
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    cur.close()
    conn.close()

# בודקת אם כבר קיים משתמש עם אותו שם משתמש או דוא״ל
# אם כן — מחזירה הודעת שגיאה
def register_user(username, email, plain_password):
    ensure_users_table()
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(f"SELECT id FROM {USERS_TABLE} WHERE username=%s OR email=%s LIMIT 1", (username, email))
    if cur.fetchone():
        cur.close()
        conn.close()
        return False, 'Username or email already exists.'

    # מצפינה את הסיסמה עם bcrypt
    # שומרת את המשתמש בבסיס הנתונים
    # מחזירה הצלחה
    pw_hash = bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt())
    cur.execute(f"INSERT INTO {USERS_TABLE} (username, email, password_hash, created_at) VALUES (%s,%s,%s,%s)",
                (username, email, pw_hash.decode('utf-8'), datetime.now(timezone.utc)))
    conn.commit()
    cur.close()
    conn.close()
    return True, 'Registered successfully.'

# בודקת אם המשתמש קיים
# אם קיים — משווה את הסיסמה עם ההאש השמור
def verify_user(username, plain_password):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT password_hash FROM {USERS_TABLE} WHERE username=%s LIMIT 1", (username,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return False, 'User not found.'
    stored = row[0].encode('utf-8')
    if bcrypt.checkpw(plain_password.encode('utf-8'), stored):
     # מחזירה הצלחה או שגיאה.
        return True, 'Login successful.'
    return False, 'Invalid password.'

#  טיפול בחיבורי TCP
class ThreadedTCPHandler(socketserver.StreamRequestHandler):
    def handle(self): # מטפל בכל חיבור של לקוח
        for raw in self.rfile:
            try:
                line = raw.decode('utf-8').strip()
                if not line:
                    continue
                data = json.loads(line)
                action = data.get('action')

                # אם הפעולה היא register:בודק שכל השדות מולאו
                # ומנסה לרשום את המשתמש
                if action == 'register':
                    username = data.get('username','').strip()
                    email = data.get('email','').strip()
                    password = data.get('password','')
                    if not (username and email and password):
                        resp = {'success': False, 'message': 'Missing fields.'}
                    else:
                        ok, msg = register_user(username, email, password)
                        resp = {'success': ok, 'message': msg}
                  # אם הפעולה היא login:בודק שהוזנו שם משתמש וסיסמה,ומוודא מול בסיס הנתונים
                elif action == 'login':
                    username = data.get('username','').strip()
                    password = data.get('password','')
                    if not (username and password):
                        resp = {'success': False, 'message': 'Missing fields.'}
                    else:
                        ok, msg = verify_user(username, password)
                        resp = {'success': ok, 'message': msg}
                # אם הפעולה אינה מוכרת — שולח הודעת שגיאה
                else:
                    resp = {'success': False, 'message': 'Unknown action.'}
            #תופס כל חריגה לא צפויה
            except Exception as e:
                resp = {'success': False, 'message': f'Error: {e}'}
            # שולח חזרה ללקוח תגובה
            out = (json.dumps(resp) + '\n').encode('utf-8')
            try:
                self.wfile.write(out)
           # אם הלקוח סגר את החיבור —מפסיק
            except BrokenPipeError:
                break

# הפעלת השרת
# שרת TCP שמטפל בכל לקוח
class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

# אם הקובץ מורץ כ־main:
# מגדיר את השרת על כל הכתובות (0.0.0.0) בפורט 9999
# מוודא שהטבלה קיימת
# מפעיל את השרת בלולאה אינסופית (serve_forever())
# עוצר ב־Ctrl+C
if __name__ == '__main__':
    HOST, PORT = '0.0.0.0', 9999
    print(f'Starting server on {HOST}:{PORT}...')
    ensure_users_table()
    with ThreadedTCPServer((HOST, PORT), ThreadedTCPHandler) as server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print('Shutting down')
            server.shutdown()