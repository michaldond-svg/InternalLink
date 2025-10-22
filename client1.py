# ייבוא ספריות והגדרות התחברות
# לבניית ממשק גרפי ולתיבת הודעות
import tkinter as tk
from tkinter import messagebox
# ליצירת חיבור TCP לשרת
import socket
# לקריאה וכתיבה של נתוני JSON
import json
# לקריאת משתני סביבה
import os
# קורא משתני סביבה להגדרת כתובת השרת ופורט, אם לא מוגדרים, משתמש ב־localhost ופורט 9999
SERVER_HOST = os.getenv('REG_SERVER_HOST', '127.0.0.1')
SERVER_PORT = int(os.getenv('REG_SERVER_PORT', 9999))

# פונקציה לשליחת בקשה לשרת
def send_request(payload: dict, timeout=5):# שניות — כמה זמן להמתין לחיבור
    with socket.create_connection((SERVER_HOST, SERVER_PORT), timeout=timeout) as s:
        s.sendall((json.dumps(payload) + '\n').encode('utf-8'))
        # קורא תגובה מהשרת — מקבל בייטים עד שנמצא תו \n (סיום שורה)
        # מפצל לפי השורה הראשונה שקיבל, ומפרש את זה כ־JSON
        # מחזיר מילון פייתון (dict) עם התשובה מהשרת
        buff = b''
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            buff += chunk
            if b'\n' in buff:
                line, _ = buff.split(b'\n', 1)
                return json.loads(line.decode('utf-8'))
    return {'success': False, 'message': 'No response from server.'}

#בונה את חלון האפליקציה הראשי.
class RegistrationClientApp:
    def __init__(self, root):
        self.root = root
        root.title('Register (Client)')
        root.geometry('360x300')
        # מציג תגית טקסט עם כתובת השרת
        tk.Label(root, text='Server: {}:{}' .format(SERVER_HOST, SERVER_PORT)).pack(pady=6)
        # תווית ושדה טקסט להזנת שם משתמש
        tk.Label(root, text='Username:').pack(pady=(6, 0))
        self.username_entry = tk.Entry(root)
        self.username_entry.pack(fill='x', padx=20)
        # תווית ושדה להזנת דוא"ל
        tk.Label(root, text='Email:').pack(pady=(6, 0))
        self.email_entry = tk.Entry(root)
        self.email_entry.pack(fill='x', padx=20)
        # תווית ושדה סיסמה
        tk.Label(root, text='Password:').pack(pady=(6, 0))
        self.password_entry = tk.Entry(root, show='*')
        self.password_entry.pack(fill='x', padx=20)
        # תווית ושדה לאימות סיסמה
        tk.Label(root, text='Confirm Password:').pack(pady=(6, 0))
        self.confirm_entry = tk.Entry(root, show='*')
        self.confirm_entry.pack(fill='x', padx=20)

        tk.Button(root, text='Register', command=self.register).pack(pady=8)
        tk.Button(root, text='Open Login', command=self.open_login).pack() # כפתור לפתיחת חלון התחברות

    # פונקציית ההרשמה
    # מקבל את הערכים שהוזנו בשדות
    def register(self):
        username = self.username_entry.get().strip()
        email = self.email_entry.get().strip()
        password = self.password_entry.get()
        confirm = self.confirm_entry.get()
        # אם אחד מהשדות ריק — מציג אזהרה ומפסיק
        if not username or not email or not password or not confirm:
            messagebox.showwarning('Missing fields', 'Please fill in all fields.')
            return
        # אם הסיסמאות לא זהות — מציג שגיאה
        if password != confirm:
            messagebox.showerror('Password mismatch', 'Passwords do not match.')
            return
        # בדיקת אורך סיסמה מינימלי
        if len(password) < 8:
            messagebox.showwarning('Weak password', 'Use at least 8 characters.')
            return

        payload = {'action': 'register', 'username': username, 'email': email, 'password': password}
       # שולח את הפנייה לשרת
       # מציג הודעה לפי התגובה — הצלחה או שגיאה
       # במידה והחיבור נכשל, מציג שגיאה
        try:
            resp = send_request(payload)
            if resp.get('success'):
                messagebox.showinfo('Success', resp.get('message'))
            else:
                messagebox.showerror('Failed', resp.get('message'))
        except Exception as e:
            messagebox.showerror('Error', f'Could not reach server: {e}')

    # פונקציה לפתיחת חלון התחברות
    def open_login(self):
        login_root = tk.Toplevel(self.root)
        LoginClientApp(login_root)

# יוצר חלון התחברות עם כותרת וגודל
class LoginClientApp:
    def __init__(self, root):
        self.root = root
        root.title('Login (Client)')
        root.geometry('320x180')
        #שדה שם משתמש
        tk.Label(root, text='Username:').pack(pady=(12, 0))
        self.username_entry = tk.Entry(root)
        self.username_entry.pack(fill='x', padx=20)
        # שדה סיסמה מוסתר
        tk.Label(root, text='Password:').pack(pady=(8, 0))
        self.password_entry = tk.Entry(root, show='*')
        self.password_entry.pack(fill='x', padx=20)
        #כפתור התחברות
        tk.Button(root, text='Login', command=self.login).pack(pady=12)

    # קורא את הנתונים שהוזנו
    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        # בודק שהשדות מלאים
        if not username or not password:
            messagebox.showwarning('Missing fields', 'Please fill in all fields.')
            return
        # מייצר בקשת התחברות
        payload = {'action': 'login', 'username': username, 'password': password}
        # שולח בקשה לשרת
        # מציג תוצאה או שגיאה
        try:
            resp = send_request(payload)
            if resp.get('success'):
                messagebox.showinfo('Success', resp.get('message'))
            else:
                messagebox.showerror('Failed', resp.get('message'))
        except Exception as e:
            messagebox.showerror('Error', f'Could not reach server: {e}')

# נקודת התחלת התוכנית
# יוצר חלון Tk הראשי, מפעיל את אפליקציית ההרשמה, מפעיל את הלולאה הראשית
if __name__ == '__main__':
    root = tk.Tk()
    RegistrationClientApp(root)
    root.mainloop()
