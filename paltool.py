import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image, ImageTk
import json
import os

# --- Constants for Palette Export ---
PALETTE_LINE_SIZE = 16
PADDING_COLOR = (0, 0, 0)  # Black (R, G, B)

# --- GPL Palette Generation ---
def generate_gpl_content(palette_name, colors, columns):
    if not colors:
        return ""
    gpl_header = f"GIMP Palette\nName: {palette_name}\nColumns: {columns}\n#\n"
    color_lines = [f"{r:>3} {g:>3} {b:>3}\t#{r:02x}{g:02x}{b:02x}" for r, g, b in colors]
    return gpl_header + "\n".join(color_lines)

# --- Custom Dialog for Export Options ---
class ExportDialog(tk.Toplevel):
    def __init__(self, parent, initial_name="My Palette"):
        super().__init__(parent)
        self.transient(parent)
        self.title("Export Options")
        
        self.result = None

        self.name_var = tk.StringVar(value=initial_name)
        self.pad_var = tk.BooleanVar(value=True)

        body = tk.Frame(self)
        self.initial_focus = self.create_widgets(body)
        body.pack(padx=10, pady=10)

        self.grab_set() # Modal dialog

        if not self.initial_focus:
            self.initial_focus = self

        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.geometry(f"+{parent.winfo_rootx()+50}+{parent.winfo_rooty()+50}")
        self.initial_focus.focus_set()
        self.wait_window(self)

    def create_widgets(self, master):
        tk.Label(master, text="Palette Name:").grid(row=0, column=0, sticky="w", pady=2)
        name_entry = tk.Entry(master, textvariable=self.name_var, width=30)
        name_entry.grid(row=0, column=1, padx=5)

        pad_check = tk.Checkbutton(master, text=f"Pad/Truncate each line to {PALETTE_LINE_SIZE} colors", variable=self.pad_var)
        pad_check.grid(row=1, columnspan=2, sticky="w", pady=5)
        
        button_frame = tk.Frame(master)
        button_frame.grid(row=2, columnspan=2, pady=10)
        
        ok_button = tk.Button(button_frame, text="OK", width=10, command=self.ok)
        ok_button.pack(side=tk.LEFT, padx=5)
        cancel_button = tk.Button(button_frame, text="Cancel", width=10, command=self.cancel)
        cancel_button.pack(side=tk.LEFT, padx=5)
        
        self.bind("<Return>", lambda e: self.ok())
        self.bind("<Escape>", lambda e: self.cancel())

        return name_entry

    def ok(self):
        self.result = {
            "name": self.name_var.get(),
            "pad": self.pad_var.get()
        }
        self.destroy()

    def cancel(self):
        self.result = None
        self.destroy()

# --- Main Application Class ---
class PaletteExtractorApp:
    # ... (all other methods from v3 are here, unchanged) ...
    # Find the "export_palette" function in your code and replace it with the one below.
    
    def __init__(self, root):
        self.root = root
        self.root.title("PNG Palette Extractor v4")
        self.root.geometry("900x700")
        self.pil_image = None
        self.tk_image = None
        self.image_path = None
        self.selections = []
        self.zoom_level = 1.0
        self.start_x, self.start_y = None, None
        self.current_selection_rect = None
        self.undo_stack = []
        self.redo_stack = []
        self.create_menu()
        self.create_widgets()
        self.setup_bindings()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        self.file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="Open Image...", command=self.open_image)
        self.file_menu.add_command(label="Save Selections", command=self.save_selections, state=tk.DISABLED)
        self.file_menu.add_command(label="Export Palette...", command=self.export_palette, state=tk.DISABLED)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.on_close)
        self.edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=self.edit_menu)
        self.edit_menu.add_command(label="Undo (Ctrl+Z)", command=self.undo, state=tk.DISABLED)
        self.edit_menu.add_command(label="Redo (Ctrl+Y)", command=self.redo, state=tk.DISABLED)
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Clear Selections", command=self.clear_selections, state=tk.DISABLED)
        self.view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=self.view_menu)
        self.view_menu.add_command(label="Zoom In (Ctrl+)", command=lambda: self.zoom(1.25), state=tk.DISABLED)
        self.view_menu.add_command(label="Zoom Out (Ctrl-)", command=lambda: self.zoom(0.8), state=tk.DISABLED)
        self.view_menu.add_command(label="Reset Zoom (Ctrl+0)", command=lambda: self.zoom(1.0, reset=True), state=tk.DISABLED)

    def create_widgets(self):
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)
        image_frame = tk.Frame(main_frame)
        image_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.canvas = tk.Canvas(image_frame, bg="gray")
        self.v_scrollbar = tk.Scrollbar(image_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.h_scrollbar = tk.Scrollbar(image_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.config(yscrollcommand=self.v_scrollbar.set, xscrollcommand=self.h_scrollbar.set)
        self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        palette_outer_frame = tk.Frame(main_frame, height=150)
        palette_outer_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)
        palette_label = tk.Label(palette_outer_frame, text="Extracted Palettes:", anchor="w")
        palette_label.pack(fill=tk.X)
        self.palette_canvas = tk.Canvas(palette_outer_frame, borderwidth=1, relief="sunken")
        self.palette_frame = tk.Frame(self.palette_canvas)
        scrollbar = tk.Scrollbar(palette_outer_frame, orient="vertical", command=self.palette_canvas.yview)
        self.palette_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.palette_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.palette_canvas.create_window((0,0), window=self.palette_frame, anchor="nw")
        self.palette_frame.bind("<Configure>", lambda e: self.palette_canvas.configure(scrollregion=self.palette_canvas.bbox("all")))
        self.status_var = tk.StringVar(value="Open an image to begin.")
        status_bar = tk.Label(self.root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def setup_bindings(self):
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_release)
        self.root.bind("<Control-plus>", lambda e: self.zoom(1.25))
        self.root.bind("<Control-minus>", lambda e: self.zoom(0.8))
        self.root.bind("<Control-0>", lambda e: self.zoom(1.0, reset=True))
        self.canvas.bind("<Control-MouseWheel>", self.on_mouse_wheel_zoom)
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-y>", lambda e: self.redo())

    def _push_to_undo(self, action):
        self.undo_stack.append(action)
        self.redo_stack.clear()
        self.update_menu_states()

    def undo(self):
        if not self.undo_stack: return
        action_type, data = self.undo_stack.pop()
        if action_type == 'add':
            self.selections.remove(data)
            self.redo_stack.append(('add', data))
        elif action_type == 'clear':
            current_selections = list(self.selections)
            self.selections = data
            self.redo_stack.append(('clear', current_selections))
        self.refresh_ui()
        self.status_var.set("Undo successful.")

    def redo(self):
        if not self.redo_stack: return
        action_type, data = self.redo_stack.pop()
        if action_type == 'add':
            self.selections.append(data)
            self.selections.sort(key=lambda s: s['num'])
            self.undo_stack.append(('add', data))
        elif action_type == 'clear':
            current_selections = list(self.selections)
            self.selections = data
            self.undo_stack.append(('clear', current_selections))
        self.refresh_ui()
        self.status_var.set("Redo successful.")

    def refresh_ui(self):
        self.redraw_canvas()
        self.update_palette_display()
        self.update_menu_states()

    def update_menu_states(self):
        has_selections = len(self.selections) > 0
        state = tk.NORMAL if has_selections else tk.DISABLED
        self.edit_menu.entryconfig("Clear Selections", state=state)
        self.file_menu.entryconfig("Save Selections", state=state)
        self.file_menu.entryconfig("Export Palette...", state=state)
        self.edit_menu.entryconfig("Undo (Ctrl+Z)", state=tk.NORMAL if self.undo_stack else tk.DISABLED)
        self.edit_menu.entryconfig("Redo (Ctrl+Y)", state=tk.NORMAL if self.redo_stack else tk.DISABLED)

    def open_image(self, *args):
        path = filedialog.askopenfilename(filetypes=[("PNG Files", "*.png"), ("All Files", "*.*")])
        if not path: return
        self.clear_all()
        self.image_path = path
        try:
            self.pil_image = Image.open(self.image_path).convert("RGB")
            self.zoom_level = 1.0
            self.refresh_ui()
            self.status_var.set(f"Loaded {os.path.basename(self.image_path)}. Click and drag to select.")
            self.view_menu.entryconfig("Zoom In (Ctrl+)", state=tk.NORMAL)
            self.view_menu.entryconfig("Zoom Out (Ctrl-)", state=tk.NORMAL)
            self.view_menu.entryconfig("Reset Zoom (Ctrl+0)", state=tk.NORMAL)
            self.load_selections()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open image: {e}")
            self.image_path = None

    def process_selection(self, x1, y1, x2, y2):
        try:
            cropped_image = self.pil_image.crop((x1, y1, x2, y2))
            colors = cropped_image.getcolors(maxcolors=1024*1024)
            if colors is None:
                messagebox.showwarning("Too Many Colors", "The selected region has too many unique colors.")
                return
            unique_colors = sorted([data[1] for data in colors], key=lambda c: 0.299*c[0] + 0.587*c[1] + 0.114*c[2])
            selection_index = (max([s['num'] for s in self.selections]) + 1) if self.selections else 1
            new_selection = {"box": (x1, y1, x2, y2), "palette": unique_colors, "num": selection_index, "rect_id": None, "text_id": None}
            self.selections.append(new_selection)
            self._push_to_undo(('add', new_selection))
            self.refresh_ui()
            self.status_var.set(f"Selection {selection_index} added with {len(unique_colors)} colors.")
        except Exception as e:
            messagebox.showerror("Processing Error", f"An error occurred: {e}")

    def clear_selections(self):
        if not self.selections: return
        self._push_to_undo(('clear', list(self.selections)))
        self.selections.clear()
        self.refresh_ui()
        self.status_var.set("Selections cleared.")

    def clear_all(self):
        self.pil_image = None
        self.tk_image = None
        self.image_path = None
        self.selections.clear()
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.canvas.delete("all")
        self.update_palette_display()
        self.update_menu_states()

    def on_close(self):
        if self.selections:
            self.save_selections()
        self.root.destroy()

    def on_mouse_wheel_zoom(self, event):
        if self.pil_image is None: return
        factor = 1.1 if event.delta > 0 else 0.9
        self.zoom(factor)
        return "break"

    def get_json_path(self):
        if not self.image_path: return None
        return os.path.splitext(self.image_path)[0] + ".json"

    def zoom(self, factor, reset=False):
        if not self.pil_image: return
        if reset: self.zoom_level = 1.0
        else: self.zoom_level = max(0.1, min(self.zoom_level * factor, 8.0))
        self.redraw_canvas()

    def redraw_canvas(self):
        if not self.pil_image: return
        w, h = int(self.pil_image.width * self.zoom_level), int(self.pil_image.height * self.zoom_level)
        resized_pil = self.pil_image.resize((w, h), Image.Resampling.NEAREST if self.zoom_level > 1 else Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(resized_pil)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        for sel in self.selections:
            x1, y1, x2, y2 = sel['box']
            zx1, zy1, zx2, zy2 = x1*self.zoom_level, y1*self.zoom_level, x2*self.zoom_level, y2*self.zoom_level
            sel['rect_id'] = self.canvas.create_rectangle(zx1, zy1, zx2, zy2, outline="cyan", width=2)
            sel['text_id'] = self.canvas.create_text(zx1 + 5, zy1 + 5, text=sel['num'], fill="cyan", anchor="nw", font=("Arial", 12, "bold"))

    def on_mouse_press(self, event):
        if not self.pil_image: return
        self.start_x, self.start_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        self.current_selection_rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline="red", dash=(4, 2))

    def on_mouse_drag(self, event):
        if not self.current_selection_rect: return
        cur_x, cur_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        self.canvas.coords(self.current_selection_rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_mouse_release(self, event):
        if not self.current_selection_rect: return
        end_x, end_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        self.canvas.delete(self.current_selection_rect)
        self.current_selection_rect = None
        x1_orig, y1_orig = min(self.start_x, end_x) / self.zoom_level, min(self.start_y, end_y) / self.zoom_level
        x2_orig, y2_orig = max(self.start_x, end_x) / self.zoom_level, max(self.start_y, end_y) / self.zoom_level
        if (x2_orig - x1_orig) < 2 or (y2_orig - y1_orig) < 2: return
        self.process_selection(int(x1_orig), int(y1_orig), int(x2_orig), int(y2_orig))

    def update_palette_display(self):
        for widget in self.palette_frame.winfo_children(): widget.destroy()
        for sel in self.selections:
            line_frame = tk.Frame(self.palette_frame)
            line_frame.pack(fill=tk.X, pady=2)
            tk.Label(line_frame, text=f"{sel['num']}:", width=3, anchor="w").pack(side=tk.LEFT, padx=(5,0))
            for r, g, b in sel["palette"]:
                tk.Label(line_frame, bg=f"#{r:02x}{g:02x}{b:02x}", width=2, height=1, relief="raised", borderwidth=1).pack(side=tk.LEFT)

    def save_selections(self):
        json_path = self.get_json_path()
        if not json_path: return
        data_to_save = [sel['box'] for sel in self.selections]
        try:
            with open(json_path, 'w') as f: json.dump(data_to_save, f, indent=2)
            self.status_var.set(f"Selections saved to {os.path.basename(json_path)}")
        except Exception as e: messagebox.showerror("Save Error", f"Failed to save selections: {e}")

    def load_selections(self):
        json_path = self.get_json_path()
        if not json_path or not os.path.exists(json_path): return
        try:
            with open(json_path, 'r') as f: boxes = json.load(f)
            original_push = self._push_to_undo
            self._push_to_undo = lambda action: None
            for box in boxes:
                self.process_selection(box[0], box[1], box[2], box[3])
            self._push_to_undo = original_push
            self.undo_stack.clear()
            self.redo_stack.clear()
            self.update_menu_states()
            self.status_var.set(f"Loaded {len(boxes)} selections from {os.path.basename(json_path)}")
        except Exception as e:
            messagebox.showwarning("Load Warning", f"Could not load selections file: {e}")
    
    # --- vvv THIS IS THE CORRECTED AND IMPROVED FUNCTION vvv ---
    def export_palette(self):
        if not self.selections:
            messagebox.showwarning("No Palette", "You haven't selected any regions yet.")
            return

        # Use the custom dialog to get export settings
        dialog = ExportDialog(self.root, initial_name="My Palette")
        settings = dialog.result
        
        if not settings or not settings["name"]:
            self.status_var.set("Export cancelled.")
            return

        palette_name = settings["name"]
        should_pad = settings["pad"]
        
        final_palette = []
        columns = 8 # Default column count for non-padded export

        if should_pad:
            # --- CORRECT PADDING LOGIC ---
            columns = PALETTE_LINE_SIZE
            for selection in self.selections:
                line_palette = list(selection['palette'])
                line_palette = line_palette[:PALETTE_LINE_SIZE] # Truncate
                
                # Pad with the default color
                num_to_pad = PALETTE_LINE_SIZE - len(line_palette)
                line_palette.extend([PADDING_COLOR] * num_to_pad)
                
                final_palette.extend(line_palette)
            # DO NOT REMOVE DUPLICATES
        else:
            # --- Original logic: unique colors from all selections ---
            combined_palette = [color for sel in self.selections for color in sel['palette']]
            final_palette = list(dict.fromkeys(combined_palette))

        file_path = filedialog.asksaveasfilename(
            title="Save GIMP Palette",
            defaultextension=".gpl",
            filetypes=[("GIMP Palette", "*.gpl"), ("All Files", "*.*")],
            initialfile=f"{palette_name.replace(' ', '_')}.gpl"
        )

        if not file_path:
            return
            
        gpl_content = generate_gpl_content(palette_name, final_palette, columns)
        
        try:
            with open(file_path, 'w') as f:
                f.write(gpl_content)
            messagebox.showinfo("Success", f"Palette successfully saved to:\n{file_path}")
            self.status_var.set(f"Palette exported with {len(final_palette)} total colors.")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save palette file: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = PaletteExtractorApp(root)
    root.mainloop()
