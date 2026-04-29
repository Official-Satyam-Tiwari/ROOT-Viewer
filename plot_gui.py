import customtkinter as ctk
import uproot
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from tkinter import filedialog
import os
import threading
import numpy as np

# Apply minimalist light theme
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

class SimplePlotter(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("ROOT Data Viewer")
        self.geometry("1400x950")
        
        # Refined Minimalist Light Palette
        self.colors = {
            "bg": "#F3F4F6",          
            "sidebar": "#FFFFFF",      
            "accent": "#3B82F6",       
            "accent_hover": "#2563EB",
            "text": "#1F2937",         
            "text_dim": "#6B7280",     
            "border": "#E5E7EB",       
            "plot_bg": "#FFFFFF"       
        }
        
        self.configure(fg_color=self.colors["bg"])
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Application State
        self.file_path = ""
        self.branches = []
        self.is_loading = False
        self.params_visible = False
        self.cbar = None
        
        self.color_map = {
            "Blue": "#3B82F6",
            "Green": "#10B981",
            "Red": "#EF4444",
            "Yellow": "#F59E0B",
            "Purple": "#8B5CF6",
            "Black": "#111827"
        }
        self.cmap_list = ["Blues", "Greens", "Reds", "viridis", "plasma", "magma"]
        self.marker_map = {"Circle": "o", "Square": "s", "Triangle": "^", "Cross": "x", "Star": "*"}
        
        self.setup_ui()
        
    def setup_ui(self):
        # Sidebar (Width 420)
        sidebar = ctk.CTkFrame(self, width=420, corner_radius=0, fg_color=self.colors["sidebar"], border_width=1, border_color=self.colors["border"])
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        
        # Header (Large Text)
        header_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        header_frame.pack(fill="x", pady=(40, 25), padx=30)
        ctk.CTkLabel(header_frame, text="ROOT Viewer", font=ctk.CTkFont(size=32, weight="bold"), text_color=self.colors["text"]).pack(anchor="w")
        ctk.CTkLabel(header_frame, text="Data Visualization", font=ctk.CTkFont(size=16), text_color=self.colors["text_dim"]).pack(anchor="w")
        
        # File Selection
        self.file_btn = ctk.CTkButton(sidebar, text="Load ROOT File", command=self.select_file, fg_color=self.colors["accent"], hover_color=self.colors["accent_hover"], font=ctk.CTkFont(size=18, weight="bold"), height=50, corner_radius=8)
        self.file_btn.pack(pady=(0, 8), padx=30, fill="x")
        self.file_label = ctk.CTkLabel(sidebar, text="No file selected", font=ctk.CTkFont(size=14), text_color=self.colors["text_dim"])
        self.file_label.pack(pady=(0, 25), padx=30, anchor="w")
        
        # Tree Selection 
        self.tree_container = ctk.CTkFrame(sidebar, fg_color="transparent")
        ctk.CTkLabel(self.tree_container, text="Target Tree", font=ctk.CTkFont(size=16, weight="bold"), text_color=self.colors["text"]).pack(anchor="w", padx=30)
        self.tree_dropdown = ctk.CTkComboBox(self.tree_container, values=["-"], font=ctk.CTkFont(size=15), dropdown_font=ctk.CTkFont(size=15), command=self.on_tree_change, corner_radius=6, border_color=self.colors["border"], height=40)
        self.tree_dropdown.pack(pady=(5, 20), padx=30, fill="x")
        
        # Plot Options
        self.options_container = ctk.CTkFrame(sidebar, fg_color="transparent")
        
        ctk.CTkLabel(self.options_container, text="Plot Type", font=ctk.CTkFont(size=16, weight="bold"), text_color=self.colors["text"]).pack(anchor="w", padx=30)
        self.plot_type = ctk.CTkSegmentedButton(self.options_container, values=["1D Hist", "2D Hist", "Scatter", "Overlaid Hist"], font=ctk.CTkFont(size=15), command=self.toggle_mode, selected_color=self.colors["accent"], selected_hover_color=self.colors["accent_hover"], height=40)
        self.plot_type.pack(pady=(5, 20), padx=30, fill="x")
        self.plot_type.set("1D Hist")

        ctk.CTkLabel(self.options_container, text="Primary Branch (X)", font=ctk.CTkFont(size=16, weight="bold"), text_color=self.colors["text"]).pack(anchor="w", padx=30)
        self.branch_dropdown = ctk.CTkComboBox(self.options_container, values=["-"], font=ctk.CTkFont(size=15), dropdown_font=ctk.CTkFont(size=15), corner_radius=6, border_color=self.colors["border"], height=40)
        self.branch_dropdown.pack(pady=(5, 20), padx=30, fill="x")
        
        self.branch_y_label = ctk.CTkLabel(self.options_container, text="Secondary Branch (Y)", font=ctk.CTkFont(size=16, weight="bold"), text_color=self.colors["text"])
        self.branch_y_label.pack(anchor="w", padx=30)
        self.branch_y_dropdown = ctk.CTkComboBox(self.options_container, values=["-"], state="disabled", font=ctk.CTkFont(size=15), dropdown_font=ctk.CTkFont(size=15), corner_radius=6, border_color=self.colors["border"], height=40)
        self.branch_y_dropdown.pack(pady=(5, 20), padx=30, fill="x")
        
        # Parameters Toggle
        self.param_toggle_btn = ctk.CTkButton(self.options_container, text="Show Parameters", font=ctk.CTkFont(size=15, weight="bold"), fg_color="transparent", border_width=1, border_color=self.colors["border"], text_color=self.colors["text_dim"], hover_color=self.colors["bg"], command=self.toggle_parameters, corner_radius=6, height=40)
        self.param_toggle_btn.pack(padx=30, fill="x", pady=(10, 0))
        
        self.param_frame = ctk.CTkFrame(self.options_container, fg_color="transparent")
        
        # Parameter Controls
        self.lbl_bins_x = ctk.CTkLabel(self.param_frame, text="X Bins: 60", font=ctk.CTkFont(size=15), text_color=self.colors["text_dim"])
        self.bins_x_slider = ctk.CTkSlider(self.param_frame, from_=5, to=200, number_of_steps=195, command=lambda v: self.lbl_bins_x.configure(text=f"X Bins: {int(v)}"), button_color=self.colors["accent"])
        self.bins_x_slider.set(60)

        self.lbl_bins_y = ctk.CTkLabel(self.param_frame, text="Y Bins: 60", font=ctk.CTkFont(size=15), text_color=self.colors["text_dim"])
        self.bins_y_slider = ctk.CTkSlider(self.param_frame, from_=5, to=200, number_of_steps=195, command=lambda v: self.lbl_bins_y.configure(text=f"Y Bins: {int(v)}"), button_color=self.colors["accent"])
        self.bins_y_slider.set(60)
        
        self.lbl_size = ctk.CTkLabel(self.param_frame, text="Marker Size: 10", font=ctk.CTkFont(size=15), text_color=self.colors["text_dim"])
        self.size_slider = ctk.CTkSlider(self.param_frame, from_=1, to=150, number_of_steps=149, command=lambda v: self.lbl_size.configure(text=f"Marker Size: {int(v)}"), button_color=self.colors["accent"])
        self.size_slider.set(10)

        self.lbl_line_width = ctk.CTkLabel(self.param_frame, text="Line Width: 1.0", font=ctk.CTkFont(size=15), text_color=self.colors["text_dim"])
        self.line_width_slider = ctk.CTkSlider(self.param_frame, from_=0.0, to=5.0, number_of_steps=50, command=lambda v: self.lbl_line_width.configure(text=f"Line Width: {v:.1f}"), button_color=self.colors["accent"])
        self.line_width_slider.set(1.0)

        self.lbl_alpha = ctk.CTkLabel(self.param_frame, text="Opacity: 0.8", font=ctk.CTkFont(size=15), text_color=self.colors["text_dim"])
        self.alpha_slider = ctk.CTkSlider(self.param_frame, from_=0.1, to=1.0, number_of_steps=9, command=lambda v: self.lbl_alpha.configure(text=f"Opacity: {v:.1f}"), button_color=self.colors["accent"])
        self.alpha_slider.set(0.8)

        self.lbl_color = ctk.CTkLabel(self.param_frame, text="Color Map", font=ctk.CTkFont(size=15), text_color=self.colors["text_dim"])
        self.color_dropdown = ctk.CTkOptionMenu(self.param_frame, values=list(self.color_map.keys()), font=ctk.CTkFont(size=15), dropdown_font=ctk.CTkFont(size=15), corner_radius=6, height=35)
        self.color_dropdown.set("Blue")

        self.lbl_marker = ctk.CTkLabel(self.param_frame, text="Marker Style", font=ctk.CTkFont(size=15), text_color=self.colors["text_dim"])
        self.marker_dropdown = ctk.CTkOptionMenu(self.param_frame, values=list(self.marker_map.keys()), font=ctk.CTkFont(size=15), dropdown_font=ctk.CTkFont(size=15), corner_radius=6, height=35)
        self.marker_dropdown.set("Circle")

        self.lbl_events = ctk.CTkLabel(self.param_frame, text="Event Limit", font=ctk.CTkFont(size=15), text_color=self.colors["text_dim"])
        self.event_entry = ctk.CTkEntry(self.param_frame, font=ctk.CTkFont(size=15), placeholder_text="100000", corner_radius=6, border_color=self.colors["border"], height=35)
        self.event_entry.insert(0, "100000")

        self.scale_frame = ctk.CTkFrame(self.param_frame, fg_color="transparent")
        self.log_x = ctk.CTkCheckBox(self.scale_frame, text="Log X", font=ctk.CTkFont(size=15), checkbox_width=25, checkbox_height=25, border_color=self.colors["border"], hover_color=self.colors["accent"])
        self.log_x.pack(side="left", padx=(0, 15))
        self.log_y = ctk.CTkCheckBox(self.scale_frame, text="Log Y", font=ctk.CTkFont(size=15), checkbox_width=25, checkbox_height=25, border_color=self.colors["border"], hover_color=self.colors["accent"])
        self.log_y.pack(side="left", padx=(0, 15))
        self.show_errors = ctk.CTkCheckBox(self.scale_frame, text="Error Bars", font=ctk.CTkFont(size=15), checkbox_width=25, checkbox_height=25, border_color=self.colors["border"], hover_color=self.colors["accent"])
        self.show_errors.pack(side="left", padx=(0, 15))
        self.norm_hist = ctk.CTkCheckBox(self.scale_frame, text="Norm", font=ctk.CTkFont(size=15), checkbox_width=25, checkbox_height=25, border_color=self.colors["border"], hover_color=self.colors["accent"])
        self.norm_hist.pack(side="left")
        
        # Signature
        self.signature_label = ctk.CTkLabel(sidebar, text="Made by Satyam Tiwari", font=ctk.CTkFont(family="Georgia", size=16, slant="italic"), text_color="#9CA3AF")
        self.signature_label.pack(side="bottom", pady=(0, 30))

        # Action Buttons
        self.btn_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        self.btn_frame.pack(side="bottom", fill="x", pady=10, padx=30)
        
        self.status_label = ctk.CTkLabel(self.btn_frame, text="Ready", font=ctk.CTkFont(size=14), text_color=self.colors["text_dim"])
        self.status_label.pack(pady=(0, 15))

        self.plot_btn = ctk.CTkButton(self.btn_frame, text="Generate Plot", command=self.start_plot_thread, height=60, font=ctk.CTkFont(size=18, weight="bold"), fg_color=self.colors["text"], hover_color="#000000", corner_radius=10)
        self.plot_btn.pack(fill="x")

        # Plot Area
        self.plot_frame = ctk.CTkFrame(self, fg_color=self.colors["plot_bg"], corner_radius=12, border_width=1, border_color=self.colors["border"])
        self.plot_frame.grid(row=0, column=1, padx=25, pady=25, sticky="nsew")
        self.plot_frame.grid_columnconfigure(0, weight=1)
        self.plot_frame.grid_rowconfigure(0, weight=1)
        
        # Matplotlib Figure
        self.fig, self.ax = plt.subplots(figsize=(8, 6), dpi=100)
        self.fig.patch.set_facecolor(self.colors["plot_bg"])
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        
        self.toolbar_frame = ctk.CTkFrame(self.plot_frame, fg_color="transparent")
        self.toolbar_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 10))
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.toolbar_frame)
        self.toolbar.config(background=self.colors["plot_bg"])
        self.toolbar.update()

    def toggle_parameters(self):
        if self.params_visible:
            self.param_frame.pack_forget()
            self.param_toggle_btn.configure(text="Show Parameters")
            self.params_visible = False
        else:
            self.param_frame.pack(fill="x", padx=30, pady=15, after=self.param_toggle_btn)
            self.update_ui_context()
            self.param_toggle_btn.configure(text="Hide Parameters")
            self.params_visible = True

    def select_file(self):
        f = filedialog.askopenfilename(filetypes=[("ROOT files", "*.root")])
        if f:
            self.file_path = f
            self.file_label.configure(text=os.path.basename(f))
            self.load_metadata()

    def load_metadata(self):
        def _load():
            try:
                self.set_loading(True, "Reading ROOT structure...")
                with uproot.open(self.file_path) as file:
                    trees = [k.split(';')[0] for k, v in file.items() if isinstance(v, uproot.TTree)]
                    if trees:
                        self.after(0, lambda: self.tree_dropdown.configure(values=["Select Tree..."] + trees))
                        self.after(0, lambda: self.tree_dropdown.set("Select Tree..."))
                        self.after(0, lambda: self.tree_container.pack(fill="x", pady=(0, 10), after=self.file_label))
                        self.after(0, lambda: self.options_container.pack_forget())
                        self.after(0, self.reset_plot_view)
                self.set_loading(False, "Please select a tree")
            except Exception:
                self.after(0, lambda: self.status_label.configure(text="Error reading file", text_color=self.colors["accent"]))
        
        threading.Thread(target=_load, daemon=True).start()

    def on_tree_change(self, tree_name):
        self.reset_plot_view() # Clear plot immediately on change
        if tree_name == "Select Tree...":
            self.options_container.pack_forget()
            return
        self.load_branches(tree_name)

    def reset_plot_view(self):
        """Clears the plot and safely destroys colorbars."""
        self.ax.clear()
        self.ax.set_title("No Data Selected", fontsize=14, color=self.colors["text_dim"])
        self._safe_remove_colorbar()
        self.canvas.draw_idle()

    def _safe_remove_colorbar(self):
        """Internal helper to wipe colorbar without Matplotlib crashing."""
        if self.cbar is not None:
            try:
                self.cbar.ax.remove() # Physically remove the colorbar axes
            except Exception:
                pass
            self.cbar = None

    def load_branches(self, tree_name):
        def _load():
            try:
                self.set_loading(True, f"Loading branches...")
                with uproot.open(self.file_path) as file:
                    tree = file[tree_name]
                    self.branches = list(tree.keys())
                    self.after(0, lambda: self.branch_dropdown.configure(values=self.branches))
                    self.after(0, lambda: self.branch_y_dropdown.configure(values=self.branches))
                    if self.branches:
                        self.after(0, lambda: self.branch_dropdown.set(self.branches[0]))
                        if len(self.branches) > 1:
                            self.after(0, lambda: self.branch_y_dropdown.set(self.branches[1]))
                        self.after(0, lambda: self.options_container.pack(fill="x"))
                        self.after(0, self.update_ui_context)
                self.set_loading(False, "Ready to plot")
            except Exception:
                self.after(0, lambda: self.status_label.configure(text="Error loading branches", text_color=self.colors["accent"]))
        
        threading.Thread(target=_load, daemon=True).start()

    def toggle_mode(self, mode):
        self.update_ui_context()
        needs_y = (mode in ["2D Hist", "Scatter", "Overlaid Hist"])
        
        if needs_y:
            # Re-pack in specific order to maintain UI layout
            self.branch_y_label.pack(anchor="w", padx=30, after=self.branch_dropdown)
            self.branch_y_dropdown.pack(pady=(5, 20), padx=30, fill="x", after=self.branch_y_label)
            self.branch_y_dropdown.configure(state="normal")
            
            # Context-aware labels
            if mode == "Overlaid Hist":
                self.branch_y_label.configure(text="Overlay Branch")
            else:
                self.branch_y_label.configure(text="Secondary Branch (Y)")
        else:
            self.branch_y_label.pack_forget()
            self.branch_y_dropdown.pack_forget()

    def update_ui_context(self):
        mode = self.plot_type.get()
        for widget in self.param_frame.winfo_children():
            widget.pack_forget()

        if mode in ["1D Hist", "Overlaid Hist"]:
            self.lbl_bins_x.pack(anchor="w", pady=(5, 0))
            self.bins_x_slider.pack(fill="x", pady=(0, 15))
            self.lbl_line_width.pack(anchor="w", pady=(0, 0))
            self.line_width_slider.pack(fill="x", pady=(0, 15))
            self.color_dropdown.configure(values=list(self.color_map.keys()))
            if self.color_dropdown.get() in self.cmap_list: self.color_dropdown.set("Blue")
            self.show_errors.pack(side="left", padx=(0, 15))
            self.norm_hist.pack(side="left", padx=(0, 15))
        elif mode == "2D Hist":
            self.lbl_bins_x.pack(anchor="w", pady=(5, 0))
            self.bins_x_slider.pack(fill="x", pady=(0, 15))
            self.lbl_bins_y.pack(anchor="w", pady=(0, 0))
            self.bins_y_slider.pack(fill="x", pady=(0, 15))
            self.color_dropdown.configure(values=self.cmap_list)
            if self.color_dropdown.get() in self.color_map: self.color_dropdown.set("viridis")
            self.show_errors.pack_forget()
            self.norm_hist.pack_forget()
        else: # Scatter
            self.lbl_size.pack(anchor="w", pady=(5, 0))
            self.size_slider.pack(fill="x", pady=(0, 15))
            self.lbl_marker.pack(anchor="w", pady=(0, 0))
            self.marker_dropdown.pack(fill="x", pady=(0, 15))
            self.color_dropdown.configure(values=list(self.color_map.keys()))
            if self.color_dropdown.get() in self.cmap_list: self.color_dropdown.set("Blue")
            self.show_errors.pack_forget()
            self.norm_hist.pack_forget()

        self.lbl_alpha.pack(anchor="w", pady=(0, 0))
        self.alpha_slider.pack(fill="x", pady=(0, 15))
        self.lbl_color.pack(anchor="w", pady=(0, 0))
        self.color_dropdown.pack(fill="x", pady=(0, 15))
        self.lbl_events.pack(anchor="w", pady=(0, 0))
        self.event_entry.pack(fill="x", pady=(0, 15))
        self.scale_frame.pack(fill="x", pady=(5, 5))

    def set_loading(self, loading, message):
        self.is_loading = loading
        state = "disabled" if loading else "normal"
        self.after(0, lambda: self.plot_btn.configure(state=state))
        self.after(0, lambda: self.status_label.configure(text=message, text_color=self.colors["text_dim"]))

    def parse_inputs(self):
        tree_val = self.tree_dropdown.get()
        if tree_val == "Select Tree...": return None
        try:
            num_str = self.event_entry.get().strip()
            num = int(num_str) if num_str else -1
            return {
                "tree_name": tree_val, "mode": self.plot_type.get(),
                "branch_x": self.branch_dropdown.get(), "branch_y": self.branch_y_dropdown.get(),
                "bins_x": int(self.bins_x_slider.get()), "bins_y": int(self.bins_y_slider.get()),
                "size": int(self.size_slider.get()), "alpha": self.alpha_slider.get(),
                "line_width": self.line_width_slider.get(),
                "marker": self.marker_map.get(self.marker_dropdown.get(), "o"),
                "color_choice": self.color_dropdown.get(), "num": num,
                "norm": self.norm_hist.get(), "errors": self.show_errors.get()
            }
        except ValueError:
            self.status_label.configure(text="Invalid Event Limit", text_color=self.colors["accent"])
            return None

    def start_plot_thread(self):
        if self.is_loading: return
        params = self.parse_inputs()
        if params:
            threading.Thread(target=self.update_plot, args=(params,), daemon=True).start()

    def update_plot(self, params):
        try:
            self.set_loading(True, "Generating Plot...")
            final_color = self.color_map.get(params["color_choice"], params["color_choice"])
            with uproot.open(self.file_path) as file:
                tree = file[params["tree_name"]]
                num = params["num"]
                if params["mode"] == "1D Hist":
                    data = tree[params["branch_x"]].array(library="np", entry_stop=num if num > 0 else None)
                    self.after(0, lambda: self._render_1d(data, params, final_color))
                elif params["mode"] == "2D Hist":
                    data_x = tree[params["branch_x"]].array(library="np", entry_stop=num if num > 0 else None)
                    data_y = tree[params["branch_y"]].array(library="np", entry_stop=num if num > 0 else None)
                    self.after(0, lambda: self._render_2d(data_x, data_y, params, final_color))
                elif params["mode"] == "Overlaid Hist":
                    data_x = tree[params["branch_x"]].array(library="np", entry_stop=num if num > 0 else None)
                    data_y = tree[params["branch_y"]].array(library="np", entry_stop=num if num > 0 else None)
                    self.after(0, lambda: self._render_overlaid(data_x, data_y, params))
                else: 
                    data_x = tree[params["branch_x"]].array(library="np", entry_stop=num if num > 0 else None)
                    data_y = tree[params["branch_y"]].array(library="np", entry_stop=num if num > 0 else None)
                    self.after(0, lambda: self._render_scatter(data_x, data_y, params, final_color))
        except Exception:
            self.after(0, lambda: self.status_label.configure(text="Plot generation failed", text_color=self.colors["accent"]))
        finally:
            self.set_loading(False, "Plot updated successfully")

    def _render_1d(self, data, params, color):
        self.ax.clear()
        self._safe_remove_colorbar()
        branch = params["branch_x"]
        counts, bins, _ = self.ax.hist(data, bins=params["bins_x"], color=color, edgecolor='black', 
                                      linewidth=params["line_width"], alpha=params["alpha"], density=params["norm"])
        
        if params["errors"]:
            bin_centers = (bins[:-1] + bins[1:]) / 2
            raw_counts, _ = np.histogram(data, bins=bins)
            errors = np.sqrt(raw_counts)
            if params["norm"]:
                errors = np.divide(counts, np.sqrt(raw_counts), out=np.zeros_like(counts), where=raw_counts != 0)
            self.ax.errorbar(bin_centers, counts, yerr=errors, fmt='none', ecolor='#1F2937', capsize=2, elinewidth=1)

        self.ax.set_title(f"Distribution of {branch}", fontsize=18, pad=20, color=self.colors["text"], weight="bold")
        self._apply_scaling()
        self._style_plot()
        self.canvas.draw_idle()

    def _render_overlaid(self, data_x, data_y, params):
        self.ax.clear()
        self._safe_remove_colorbar()
        b1, b2 = params["branch_x"], params["branch_y"]
        c1, c2 = self.color_map["Blue"], self.color_map["Red"]
        
        # Hist 1
        n1, bins, _ = self.ax.hist(data_x, bins=params["bins_x"], color=c1, histtype='step', 
                                   linewidth=params["line_width"]+1, label=b1, density=params["norm"], alpha=params["alpha"])
        # Hist 2
        n2, _, _ = self.ax.hist(data_y, bins=bins, color=c2, histtype='step', 
                                linewidth=params["line_width"]+1, label=b2, density=params["norm"], alpha=params["alpha"])
        
        if params["errors"]:
            centers = (bins[:-1] + bins[1:]) / 2
            for d, n, c in [(data_x, n1, c1), (data_y, n2, c2)]:
                raw, _ = np.histogram(d, bins=bins)
                err = np.sqrt(raw)
                if params["norm"]: 
                    err = np.divide(n, np.sqrt(raw), out=np.zeros_like(n), where=raw != 0)
                self.ax.errorbar(centers, n, yerr=err, fmt='none', ecolor=c, capsize=2, alpha=0.6)

        self.ax.set_title(f"Comparison: {b1} vs {b2}", fontsize=18, pad=20, color=self.colors["text"], weight="bold")
        self.ax.legend(frameon=False, fontsize=12)
        self._apply_scaling()
        self._style_plot()
        self.canvas.draw_idle()

    def _render_2d(self, data_x, data_y, params, cmap):
        self.ax.clear()
        self._safe_remove_colorbar()
        branch_x, branch_y = params["branch_x"], params["branch_y"]
        h = self.ax.hist2d(data_x, data_y, bins=[params["bins_x"], params["bins_y"]], cmap=cmap, alpha=params["alpha"])
        self.ax.set_title(f"{branch_x} vs {branch_y}", fontsize=18, pad=20, color=self.colors["text"], weight="bold")
        self.cbar = self.fig.colorbar(h[3], ax=self.ax)
        self.cbar.outline.set_visible(False)
        self._apply_scaling()
        self._style_plot()
        self.canvas.draw_idle()

    def _render_scatter(self, data_x, data_y, params, color):
        self.ax.clear()
        self._safe_remove_colorbar()
        branch_x, branch_y = params["branch_x"], params["branch_y"]
        self.ax.scatter(data_x, data_y, s=params["size"], alpha=params["alpha"], c=color, marker=params["marker"], edgecolors='none')
        self.ax.set_title(f"{branch_x} vs {branch_y}", fontsize=18, pad=20, color=self.colors["text"], weight="bold")
        self._apply_scaling()
        self._style_plot()
        self.canvas.draw_idle()

    def _apply_scaling(self):
        self.ax.set_xscale('log' if self.log_x.get() else 'linear')
        self.ax.set_yscale('log' if self.log_y.get() else 'linear')

    def _style_plot(self):
        self.ax.grid(True, linestyle='-', alpha=0.5, color=self.colors["bg"])
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['left'].set_color(self.colors["border"])
        self.ax.spines['bottom'].set_color(self.colors["border"])
        self.ax.tick_params(colors=self.colors["text_dim"], labelsize=12)
        self.fig.tight_layout()

if __name__ == "__main__":
    app = SimplePlotter()
    app.mainloop()