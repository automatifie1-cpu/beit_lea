"""
ממשק גרפי לבדיקת הצ'אט AI.
מאפשר לסמלץ שיחה עם הבוט כאילו אתה משתמש רשום.
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
from ai_chat import chat_with_ai, process_confirmation
import conversation_state as conv_state

# הגדרות ברירת מחדל
DEFAULT_PHONE = "972542543420"
DEFAULT_NAME = "גיא"
DEFAULT_LANG = "he"


class ChatGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("בדיקת צ'אט AI - בית לאה")
        self.root.geometry("600x700")
        self.root.configure(bg="#1a1a2e")
        
        # משתנים
        self.phone_number = DEFAULT_PHONE
        self.user_name = DEFAULT_NAME
        self.language = DEFAULT_LANG
        
        self.setup_ui()
        
    def setup_ui(self):
        # סגנון
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TFrame", background="#1a1a2e")
        style.configure("TLabel", background="#1a1a2e", foreground="white", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10, "bold"))
        style.configure("TEntry", font=("Segoe UI", 10))
        
        # מסגרת ראשית
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # כותרת
        title_label = tk.Label(
            main_frame, 
            text="🤖 בדיקת צ'אט AI - בית לאה",
            font=("Segoe UI", 16, "bold"),
            bg="#1a1a2e",
            fg="#00d4ff"
        )
        title_label.pack(pady=(0, 10))
        
        # הגדרות משתמש
        settings_frame = ttk.LabelFrame(main_frame, text="הגדרות משתמש", padding=10)
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        # שם
        ttk.Label(settings_frame, text="שם:").grid(row=0, column=0, padx=5, sticky="e")
        self.name_entry = ttk.Entry(settings_frame, width=20)
        self.name_entry.insert(0, DEFAULT_NAME)
        self.name_entry.grid(row=0, column=1, padx=5)
        
        # טלפון
        ttk.Label(settings_frame, text="טלפון:").grid(row=0, column=2, padx=5, sticky="e")
        self.phone_entry = ttk.Entry(settings_frame, width=20)
        self.phone_entry.insert(0, DEFAULT_PHONE)
        self.phone_entry.grid(row=0, column=3, padx=5)
        
        # שפה
        ttk.Label(settings_frame, text="שפה:").grid(row=0, column=4, padx=5, sticky="e")
        self.lang_combo = ttk.Combobox(settings_frame, values=["he", "en"], width=5, state="readonly")
        self.lang_combo.set("he")
        self.lang_combo.grid(row=0, column=5, padx=5)
        
        # כפתור איפוס שיחה
        reset_btn = ttk.Button(settings_frame, text="🔄 איפוס שיחה", command=self.reset_conversation)
        reset_btn.grid(row=0, column=6, padx=10)
        
        # אזור הצ'אט
        chat_frame = ttk.LabelFrame(main_frame, text="שיחה", padding=10)
        chat_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.chat_display = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            font=("Segoe UI", 11),
            bg="#16213e",
            fg="white",
            insertbackground="white",
            state=tk.DISABLED,
            height=20
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        
        # תגיות לעיצוב
        self.chat_display.tag_configure("user", foreground="#00ff88", justify="right")
        self.chat_display.tag_configure("bot", foreground="#00d4ff", justify="left")
        self.chat_display.tag_configure("system", foreground="#ffaa00", justify="center")
        self.chat_display.tag_configure("pending", foreground="#ff6b6b", justify="left")
        
        # אזור קלט
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X)
        
        self.message_entry = ttk.Entry(input_frame, font=("Segoe UI", 12))
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.message_entry.bind("<Return>", lambda e: self.send_message())
        
        send_btn = ttk.Button(input_frame, text="שלח 📤", command=self.send_message)
        send_btn.pack(side=tk.RIGHT)
        
        # סטטוס
        self.status_label = tk.Label(
            main_frame,
            text="מצב: מוכן לשיחה",
            font=("Segoe UI", 9),
            bg="#1a1a2e",
            fg="#888"
        )
        self.status_label.pack(pady=(10, 0))
        
        # הודעת פתיחה
        self.add_system_message("ברוכים הבאים! הקלד הודעה כדי להתחיל שיחה עם הבוט.")
        
    def add_message(self, sender: str, message: str, tag: str):
        """הוספת הודעה לתצוגה"""
        self.chat_display.configure(state=tk.NORMAL)
        
        if tag == "user":
            prefix = f"\n👤 {sender}: "
        elif tag == "bot":
            prefix = f"\n🤖 בוט: "
        elif tag == "pending":
            prefix = f"\n⏳ פנייה מזוהה: "
        else:
            prefix = f"\n⚙️ "
            
        self.chat_display.insert(tk.END, prefix, tag)
        self.chat_display.insert(tk.END, message + "\n", tag)
        self.chat_display.see(tk.END)
        self.chat_display.configure(state=tk.DISABLED)
        
    def add_system_message(self, message: str):
        """הודעת מערכת"""
        self.chat_display.configure(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"\n{'─'*50}\n", "system")
        self.chat_display.insert(tk.END, f"📌 {message}\n", "system")
        self.chat_display.insert(tk.END, f"{'─'*50}\n", "system")
        self.chat_display.see(tk.END)
        self.chat_display.configure(state=tk.DISABLED)
        
    def send_message(self):
        """שליחת הודעה"""
        message = self.message_entry.get().strip()
        if not message:
            return
            
        # עדכון הגדרות
        self.user_name = self.name_entry.get() or DEFAULT_NAME
        self.phone_number = self.phone_entry.get() or DEFAULT_PHONE
        self.language = self.lang_combo.get() or DEFAULT_LANG
        
        # הצג הודעת משתמש
        self.add_message(self.user_name, message, "user")
        self.message_entry.delete(0, tk.END)
        
        # עדכון סטטוס
        self.status_label.config(text="מצב: מעבד...", fg="#ffaa00")
        self.root.update()
        
        # שלח לעיבוד ב-thread נפרד
        threading.Thread(target=self.process_message, args=(message,), daemon=True).start()
        
    def process_message(self, message: str):
        """עיבוד ההודעה עם AI"""
        try:
            current_state = conv_state.get_state(self.phone_number)
            
            if current_state == "confirming_request":
                # מחכים לאישור
                response_text, is_confirmed, request_text = process_confirmation(
                    self.phone_number,
                    message,
                    self.language
                )
                
                self.root.after(0, lambda: self.add_message("בוט", response_text, "bot"))
                
                if is_confirmed and request_text:
                    self.root.after(0, lambda: self.add_system_message(f"✅ פנייה נשלחה בהצלחה:\n\"{request_text}\""))
                    
            else:
                # שיחה רגילה
                response_text, pending_request = chat_with_ai(
                    self.phone_number,
                    message,
                    self.user_name,
                    self.language
                )
                
                self.root.after(0, lambda: self.add_message("בוט", response_text, "bot"))
                
                if pending_request:
                    self.root.after(0, lambda: self.add_message("", f"\"{pending_request}\"", "pending"))
                    
            # עדכון סטטוס
            state = conv_state.get_state(self.phone_number)
            state_text = {
                "chatting": "שיחה פעילה",
                "confirming_request": "מחכה לאישור פנייה",
                "completed": "הושלם"
            }.get(state, state)
            
            self.root.after(0, lambda: self.status_label.config(text=f"מצב: {state_text}", fg="#00ff88"))
            
        except Exception as e:
            error_msg = f"שגיאה: {str(e)}"
            self.root.after(0, lambda: self.add_system_message(f"❌ {error_msg}"))
            self.root.after(0, lambda: self.status_label.config(text="מצב: שגיאה", fg="#ff0000"))
            
    def reset_conversation(self):
        """איפוס השיחה"""
        self.phone_number = self.phone_entry.get() or DEFAULT_PHONE
        conv_state.clear_conversation(self.phone_number)
        
        self.chat_display.configure(state=tk.NORMAL)
        self.chat_display.delete(1.0, tk.END)
        self.chat_display.configure(state=tk.DISABLED)
        
        self.add_system_message("השיחה אופסה. אפשר להתחיל מחדש!")
        self.status_label.config(text="מצב: מוכן לשיחה", fg="#888")


def main():
    root = tk.Tk()
    app = ChatGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
