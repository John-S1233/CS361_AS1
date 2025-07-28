import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from tkinter import ttk
import speech_recognition as sr
import openai
from dotenv import load_dotenv

KEY_PATH = "API_KEY.txt"

with open(KEY_PATH, 'r') as file:
    key = file.readline().strip()

openai.api_key = key

class TranscriptionApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Audio Transcriber & LLM Assistant")
        self.geometry('1920x1080')

        # Flags & data
        self.running = False
        self.paused = False
        self.sessions = [] 
        self.current_transcript = []

        self._build_widgets()

    def _build_widgets(self):
        menubar = tk.Menu(self)
        history_menu = tk.Menu(menubar, tearoff=0)
        history_menu.add_command(label="View Sessions…", command=self.show_history)
        menubar.add_cascade(label="History", menu=history_menu)
        self.config(menu=menubar)

        top_frame = ttk.Frame(self)
        top_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(fill=tk.X, padx=10, pady=5)

        # Transcript display
        self.text_area = tk.Text(top_frame, height=15)
        self.text_area.pack(fill=tk.BOTH, expand=True)

        # LLM response display
        self.llm_area = tk.Text(top_frame, height=10, bg="#f0f0f0")
        self.llm_area.pack(fill=tk.BOTH, expand=True, pady=(5,0))

        # Control buttons
        self.start_btn = ttk.Button(bottom_frame, text="Start", command=self.start_transcription)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        self.pause_btn = ttk.Button(bottom_frame, text="Pause", state=tk.DISABLED, command=self.toggle_pause)
        self.pause_btn.pack(side=tk.LEFT, padx=5)
        self.save_btn = ttk.Button(bottom_frame, text="Save", state=tk.DISABLED, command=self.save_transcript)
        self.save_btn.pack(side=tk.LEFT, padx=5)
        self.summarize_btn = ttk.Button(bottom_frame, text="Summarize", state=tk.DISABLED, command=self.summarize_transcript)
        self.summarize_btn.pack(side=tk.LEFT, padx=5)
        self.ask_btn = ttk.Button(bottom_frame, text="Ask LLM…", state=tk.DISABLED, command=self.ask_llm)
        self.ask_btn.pack(side=tk.LEFT, padx=5)
        self.note_btn = ttk.Button(bottom_frame, text="Notepad…", command=self.open_notepad)
        self.note_btn.pack(side=tk.RIGHT, padx=5)

    def start_transcription(self):
        self.running = True
        self.start_btn.config(state=tk.DISABLED)
        self.pause_btn.config(state=tk.NORMAL)
        self.save_btn.config(state=tk.NORMAL)
        self.summarize_btn.config(state=tk.NORMAL)
        self.ask_btn.config(state=tk.NORMAL)
        threading.Thread(target=self.transcribe_loop, daemon=True).start()

    def toggle_pause(self):
        self.paused = not self.paused
        self.pause_btn.config(text="Resume" if self.paused else "Pause")

    def transcribe_loop(self):
        recognizer = sr.Recognizer()
        mic = sr.Microphone()
        with mic as source:
            recognizer.adjust_for_ambient_noise(source)
        while self.running:
            if self.paused:
                continue
            try:
                with mic as source:
                    audio = recognizer.listen(source, timeout=5)
                text = recognizer.recognize_google(audio)
                self.current_transcript.append(text)
                self.text_area.insert(tk.END, text + "\n")
                self.text_area.see(tk.END)
            except sr.WaitTimeoutError:
                continue
            except sr.UnknownValueError:
                continue
            except Exception as e:
                messagebox.showerror("Error", str(e))
                break

    def save_transcript(self):
        path = filedialog.asksaveasfilename(defaultextension='.txt',
                                            filetypes=[('Text Files','*.txt')])
        if not path:
            return
        # Gather transcript
        transcript = "\n".join(self.current_transcript)
        # Gather log
        log = self.llm_area.get("1.0", tk.END).strip()

        with open(path, 'w') as f:
            f.write("=== Transcript ===\n")
            f.write(transcript + "\n\n")
            f.write("=== LLM Log ===\n")
            f.write(log + "\n")
        messagebox.showinfo("Saved", f"Transcript and log saved to {path}")

    def summarize_transcript(self):
        if not self.current_transcript:
            return
        transcript_text = "\n".join(self.current_transcript)
        self.llm_area.insert(tk.END, "Generating summary...\n")
        threading.Thread(target=self._call_summarize, args=(transcript_text,), daemon=True).start()

    def _call_summarize(self, text):
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": f"Summarize the following conversation: {text}"}]
        )
        summary = response.choices[0].message.content.strip()
        self.llm_area.insert(tk.END, "Summary:\n" + summary + "\n")
        self.sessions.append((list(self.current_transcript), summary))

    def ask_llm(self):
        query = simpledialog.askstring("Ask LLM", "Enter your question:")
        if not query:
            return
        combined = "\n".join(self.current_transcript) + "\nUser question: " + query
        self.llm_area.insert(tk.END, f"Q: {query}\n")
        threading.Thread(target=self._call_query, args=(combined,), daemon=True).start()

    def _call_query(self, text):
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": text}]
        )
        answer = response.choices[0].message.content.strip()
        self.llm_area.insert(tk.END, "A: " + answer + "\n")

    def show_history(self):
        dlg = tk.Toplevel(self)
        dlg.title("Session History")
        listbox = tk.Listbox(dlg, width=80)
        listbox.pack(fill=tk.BOTH, expand=True)
        for idx, (_, summary) in enumerate(self.sessions, 1):
            listbox.insert(tk.END, f"Session {idx}: {summary[:60]}...")

    def open_notepad(self):
        note_win = tk.Toplevel(self)
        note_win.title("Notepad")
        text = tk.Text(note_win)
        text.pack(fill=tk.BOTH, expand=True)

if __name__ == '__main__':
    TranscriptionApp().mainloop()
