# main.py
import os, threading, json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
import customtkinter as ctk

from constants import C, FONT_MONO, FONT_SANS, FONT_BOLD, FONT_SM, FONT_LABEL, FONT_TITLE
from ftp_backend import FTPBackend

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class LargeInputDialog(ctk.CTkToplevel):
  """Dialog nhập liệu tự xây dựng — không phụ thuộc thuộc tính nội bộ của CTkInputDialog."""
  def __init__(self, title, text, width=480, height=220):
    super().__init__()
    self._result = None
    self.title(title)
    self.geometry(f"{width}x{height}")
    self.resizable(False, False)
    self.grab_set()           # khóa focus vào dialog
    self.attributes("-topmost", True)
    # Căn giữa màn hình
    self.update_idletasks()
    x = (self.winfo_screenwidth()  - width)  // 2
    y = (self.winfo_screenheight() - height) // 2
    self.geometry(f"+{x}+{y}")

    ctk.CTkLabel(self, text=text, font=("Segoe UI", 13), anchor="w").pack(
      fill="x", padx=24, pady=(24, 8))

    self._entry = ctk.CTkEntry(self, font=("Segoe UI", 13), height=42)
    self._entry.pack(fill="x", padx=24, pady=(0, 16))
    self._entry.focus_set()
    self._entry.bind("<Return>", lambda e: self._ok())
    self._entry.bind("<Escape>", lambda e: self._cancel())

    btn_row = ctk.CTkFrame(self, fg_color="transparent")
    btn_row.pack(fill="x", padx=24, pady=(0, 20))
    ctk.CTkButton(btn_row, text="OK",     width=100, command=self._ok).pack(side="right", padx=(8, 0))
    ctk.CTkButton(btn_row, text="Hủy",   width=100,
                  fg_color="transparent", border_width=1, command=self._cancel).pack(side="right")

    self.wait_window()        # chặn đến khi đóng

  def _ok(self):
    self._result = self._entry.get().strip()
    self.destroy()

  def _cancel(self):
    self._result = None
    self.destroy()

  def get_input(self):
    return self._result


class Toast:
  def __init__(self, master, message, duration=2000):
    self.toast = tk.Toplevel(master)
    self.toast.overrideredirect(True)
    self.toast.attributes('-topmost', True)
    self.toast.configure(bg=C["accent"])
    tk.Label(self.toast, text=message, bg=C["accent"], fg="white", padx=20, pady=10, font=FONT_SANS).pack()
    self.toast.update_idletasks()
    self.toast.geometry(
      f"+{master.winfo_rootx() + master.winfo_width() // 2 - self.toast.winfo_width() // 2}+{master.winfo_rooty() + master.winfo_height() - 80}")
    self.toast.after(duration, self.toast.destroy)


class FTPClientApp(ctk.CTk):
  def __init__(self):
    super().__init__()
    self.title("FTPStudio Pro — Premium FTP Client")
    self.geometry("1400x900")
    self.minsize(1000, 750)
    self.configure(fg_color=C["bg"])

    self.remote_path_var = tk.StringVar(value="Chưa kết nối")
    self._drag_data, self._sel_local, self._sel_remote = None, None, None

    self.backend = FTPBackend(self)
    self.local_dir = os.path.abspath(os.getcwd())
    self.history_file = "connections.json"
    self.connections = self._load_history()

    self._setup_treeview_style()
    self._build_ui()
    self.ent_host.focus()

  # --- HELPERS (Giúp main.py ngắn đi rất nhiều) ---
  def _run_bg(self, target, *args):
    """Chạy hàm ngầm trong Thread để không đơ UI"""
    threading.Thread(target=target, args=args, daemon=True).start()

  def _clean_name(self, raw_str):
    """Bóc tách icon thư mục/file ra khỏi tên"""
    return raw_str.replace("📁  ", "").replace("📄  ", "")

  # --- HISTORY ---
  def _load_history(self):
    try:
      return json.load(open(self.history_file)) if os.path.exists(self.history_file) else {"hosts": ["127.0.0.1"],
                                                                                           "users": ["IT1"]}
    except:
      return {"hosts": ["127.0.0.1"], "users": ["IT1"]}

  def _save_history(self):
    try:
      json.dump(self.connections, open(self.history_file, "w"))
    except:
      pass

  def _add_to_history(self, h, u):
    for key, val in [("hosts", h), ("users", u)]:
      if val and val not in self.connections[key]:
        self.connections[key].insert(0, val)
        self.connections[key] = self.connections[key][:10]
    self._save_history()
    self.combo_host['values'], self.combo_user['values'] = self.connections["hosts"], self.connections["users"]

  # --- UI SETUP ---
  def _setup_treeview_style(self):
    st = ttk.Style(self)
    st.theme_use("clam")
    st.configure("FTP.Treeview", background=C["panel"], foreground=C["text"], fieldbackground=C["panel"], rowheight=34,
                 font=FONT_SANS, borderwidth=0)
    st.configure("FTP.Treeview.Heading", background=C["panel2"], foreground=C["text"], font=FONT_BOLD, borderwidth=0,
                 padding=(10, 8))
    st.map("FTP.Treeview", background=[("selected", C["row_sel"])], foreground=[("selected", "white")])

  def _build_ui(self):
    self._build_topbar()
    self._build_log_panel()
    pane = ctk.CTkFrame(self, fg_color="transparent")
    pane.pack(fill="both", expand=True, padx=15, pady=10)
    paned = tk.PanedWindow(pane, orient="horizontal", sashrelief="flat", sashwidth=6, bg=C["bg"])
    paned.pack(fill="both", expand=True)
    self._build_local_pane(paned)
    self._build_remote_pane(paned)
    self._build_action_bar()
    self._build_status_bar()

  def _build_topbar(self):
    bar = ctk.CTkFrame(self, fg_color=C["panel"], height=80, corner_radius=12)
    bar.pack(fill="x", side="top", padx=15, pady=(15, 5))
    bar.pack_propagate(False)
    ctk.CTkLabel(bar, text="⚡ FTPStudio Pro", text_color=C["accent2"], font=("Segoe UI", 18, "bold")).pack(side="left",
                                                                                                           padx=20)
    inp = ctk.CTkFrame(bar, fg_color="transparent")
    inp.pack(side="left", fill="y", padx=10)

    for text, var_name, width, default in [("Host:", "combo_host", 20, "10.109.10.6"),
                                           ("User:", "combo_user", 15, "IT1")]:
      ctk.CTkLabel(inp, text=text, text_color=C["muted"], font=FONT_LABEL).pack(side="left", padx=(12, 4))
      cb = ttk.Combobox(inp, values=self.connections[text.replace(":", "").lower() + "s"], width=width, font=FONT_MONO)
      cb.pack(side="left", padx=2)
      cb.set(default)
      setattr(self, var_name, cb)
    self.ent_host, self.ent_user = self.combo_host, self.combo_user

    ctk.CTkLabel(inp, text="Port:", text_color=C["muted"], font=FONT_LABEL).pack(side="left", padx=(12, 4))
    self.ent_port = ctk.CTkEntry(inp, width=70, height=38, fg_color=C["panel2"])
    self.ent_port.pack(side="left", padx=2)
    self.ent_port.insert(0, "21")

    ctk.CTkLabel(inp, text="Pass:", text_color=C["muted"], font=FONT_LABEL).pack(side="left", padx=(12, 4))
    self.ent_pass = ctk.CTkEntry(inp, width=120, height=38, show="*", fg_color=C["panel2"])
    self.ent_pass.pack(side="left", padx=2)

    self.btn_connect = ctk.CTkButton(bar, text="🔌 Kết nối", width=120, height=40, font=FONT_BOLD, fg_color=C["accent"],
                                     command=self._start_connect)
    self.btn_connect.pack(side="left", padx=20)

    self.status_pill = ctk.CTkFrame(bar, fg_color=C["panel2"], height=40, corner_radius=20)
    self.status_pill.pack(side="right", padx=20)
    self.status_dot = ctk.CTkFrame(self.status_pill, width=14, height=14, corner_radius=7, fg_color=C["border2"])
    self.status_dot.pack(side="left", padx=(14, 8), pady=13)
    self.lbl_status = ctk.CTkLabel(self.status_pill, text="Chưa kết nối", text_color=C["muted"], font=FONT_BOLD)
    self.lbl_status.pack(side="left", padx=(0, 14))

  def _build_log_panel(self):
    log_f = ctk.CTkFrame(self, fg_color="#0A0C10", height=150, corner_radius=8, border_width=1,
                         border_color=C["border"])
    log_f.pack(side="top", fill="x", padx=15, pady=5)
    log_f.pack_propagate(False)
    top = ctk.CTkFrame(log_f, fg_color="transparent", height=30)
    top.pack(fill="x")
    ctk.CTkLabel(top, text="📜 Nhật ký lệnh", font=FONT_BOLD, text_color=C["accent2"]).pack(side="left", padx=10)
    ctk.CTkButton(top, text="Xóa log", width=80, height=25, fg_color=C["panel2"], command=self._clear_log).pack(
      side="right", padx=10)

    self.txt_log = tk.Text(log_f, bg="#0A0C10", fg="#E2E8F0", font=FONT_MONO, state="disabled", relief="flat", padx=12,
                           pady=8)
    self.txt_log.pack(side="left", fill="both", expand=True)
    sb = ttk.Scrollbar(log_f, command=self.txt_log.yview)
    sb.pack(side="right", fill="y")
    self.txt_log.configure(yscrollcommand=sb.set)
    for tag, color in [("cmd", "#60A5FA"), ("resp", "#34D399"), ("info", "white"), ("err", "#F87171")]:
      self.txt_log.tag_configure(tag, foreground=color)
    self._log("info", "✅ FTPStudio Pro sẵn sàng.")

  def _build_local_pane(self, paned):
    frm = ctk.CTkFrame(paned, fg_color=C["panel"], corner_radius=10, border_width=1, border_color=C["border"])
    paned.add(frm, minsize=450)
    hdr = ctk.CTkFrame(frm, fg_color=C["panel2"], height=45, corner_radius=0)
    hdr.pack(fill="x")
    hdr.pack_propagate(False)
    ctk.CTkLabel(hdr, text="💻 MÁY CỤC BỘ", text_color=C["text"], font=FONT_TITLE).pack(side="left", padx=15)
    ctk.CTkButton(hdr, text="⬆ Lên", width=80, height=32, fg_color=C["panel"], command=self._local_up).pack(
      side="right", padx=10)

    self.local_path_bar = ctk.CTkFrame(frm, fg_color=C["panel2"], height=38, corner_radius=0)
    self.local_path_bar.pack(fill="x")

    search = ctk.CTkFrame(frm, fg_color="transparent")
    search.pack(fill="x", padx=10, pady=5)
    ctk.CTkLabel(search, text="🔍", text_color=C["muted"]).pack(side="left")
    self.src_loc = ctk.CTkEntry(search, placeholder_text="Tìm kiếm file...", font=FONT_SANS, height=30)
    self.src_loc.pack(side="left", fill="x", expand=True, padx=5)
    self.src_loc.bind("<KeyRelease>", self._filter_local)

    self.tree_local = self._create_tree(frm)
    self.tree_local.bind("<<TreeviewSelect>>",
                         lambda e: setattr(self, '_sel_local', self.tree_local.item(self.tree_local.focus(), "values")))
    self.tree_local.bind("<Double-1>", self._on_local_dblclick)
    self.tree_local.bind("<ButtonPress-1>", lambda e: setattr(self, '_drag_data', {"s": "local",
                                                                                   "v": self.tree_local.item(
                                                                                     self.tree_local.focus(),
                                                                                     "values")} if self.tree_local.focus() else None))
    self.tree_local.bind("<ButtonRelease-1>", self._on_local_drop)
    self.tree_local.bind("<Button-3>", self._show_local_context)
    self.refresh_local()

  def _build_remote_pane(self, paned):
    frm = ctk.CTkFrame(paned, fg_color=C["panel"], corner_radius=10, border_width=1, border_color=C["border"])
    paned.add(frm, minsize=450)
    hdr = ctk.CTkFrame(frm, fg_color=C["panel2"], height=45, corner_radius=0)
    hdr.pack(fill="x")
    hdr.pack_propagate(False)
    ctk.CTkLabel(hdr, text="🌐 MÁY CHỦ FTP", text_color=C["accent2"], font=FONT_TITLE).pack(side="left", padx=15)
    ctk.CTkButton(hdr, text="⬆ Lên", width=80, height=32, fg_color=C["panel"], command=self._cd_up).pack(side="right",
                                                                                                         padx=10)

    self.remote_path_bar = ctk.CTkFrame(frm, fg_color=C["panel2"], height=38, corner_radius=0)
    self.remote_path_bar.pack(fill="x")
    self._update_remote_breadcrumb("Chưa kết nối")

    search = ctk.CTkFrame(frm, fg_color="transparent")
    search.pack(fill="x", padx=10, pady=5)
    ctk.CTkLabel(search, text="🔍", text_color=C["muted"]).pack(side="left")
    self.src_rem = ctk.CTkEntry(search, placeholder_text="Tìm kiếm trên server...", font=FONT_SANS, height=30)
    self.src_rem.pack(side="left", fill="x", expand=True, padx=5)
    self.src_rem.bind("<KeyRelease>", self._filter_remote)

    self.tree_remote = self._create_tree(frm)
    self.tree_remote.bind("<<TreeviewSelect>>", lambda e: setattr(self, '_sel_remote',
                                                                  self.tree_remote.item(self.tree_remote.focus(),
                                                                                        "values")))
    self.tree_remote.bind("<Double-1>", self._on_remote_dblclick)
    self.tree_remote.bind("<ButtonPress-1>", lambda e: setattr(self, '_drag_data', {"s": "remote",
                                                                                    "v": self.tree_remote.item(
                                                                                      self.tree_remote.focus(),
                                                                                      "values")} if self.tree_remote.focus() and self.backend.is_connected else None))
    self.tree_remote.bind("<ButtonRelease-1>", self._on_remote_drop)
    self.tree_remote.bind("<Button-3>", self._show_remote_context)

  def _create_tree(self, parent):
    cont = ctk.CTkFrame(parent, fg_color="transparent")
    cont.pack(fill="both", expand=True, padx=2, pady=2)
    tree = ttk.Treeview(cont, columns=("name", "size", "type"), show="headings", style="FTP.Treeview",
                        selectmode="extended")
    tree.heading("name", text="Tên tệp tin / Thư mục")
    tree.column("name", width=300, stretch=True)
    tree.heading("size", text="Kích thước")
    tree.column("size", width=120, anchor="e")
    tree.heading("type", text="Loại")
    tree.column("type", width=100, anchor="center")
    tree.pack(side="left", fill="both", expand=True)
    ttk.Scrollbar(cont, orient="vertical", command=tree.yview).pack(side="right", fill="y")
    return tree

  def _build_action_bar(self):
    # 1. Hạ chiều cao thanh xuống 52px (cũ là 65px) cho gọn gàng
    bar = ctk.CTkFrame(self, fg_color=C["panel"], height=52, corner_radius=10)
    bar.pack(fill="x", side="bottom", padx=15, pady=(5, 15))
    bar.pack_propagate(False)

    # 2. Giảm chiều cao nút xuống 36px (cũ là 44px) và tinh chỉnh lại width cân đối
    ctk.CTkButton(bar, text="📤 Upload", width=130, height=36, fg_color=C["accent"], command=self._handle_upload).pack(
      side="left", padx=12, pady=8)
    ctk.CTkButton(bar, text="📥 Download", width=110, height=36, fg_color=C["panel2"], border_width=1,
                  command=self._handle_download).pack(side="left", padx=6, pady=8)

    # 3. Thu nhỏ thanh vạch ngăn cách giữa các cụm nút (height=26px)
    ctk.CTkFrame(bar, width=2, height=26, fg_color=C["border"]).pack(side="left", padx=12, pady=13)

    # 4. Thu nhỏ hàm tạo nút nhanh (width từ 130 -> 115, height từ 44 -> 36)
    def make_btn(txt, cmd, danger=False):
      return ctk.CTkButton(bar, text=txt, width=115, height=36, border_width=1, command=cmd,
                           fg_color=C["danger_bg"] if danger else C["panel2"],
                           text_color=C["danger"] if danger else C["text"],
                           border_color=C["danger"] if danger else C["border"])

    # 5. Thêm pady=8 để các nút căn giữa thanh 52px tuyệt đối
    make_btn("📁+ Tạo thư mục", self._handle_mkdir).pack(side="left", padx=6, pady=8)
    make_btn("✏️ Đổi tên", self._handle_rename).pack(side="left", padx=6, pady=8)
    make_btn("❌ Xóa", self._handle_delete, True).pack(side="left", padx=6, pady=8)
    make_btn("🔄 Làm mới Remote", self._handle_refresh_rem).pack(side="right", padx=12, pady=8)
  def _build_status_bar(self):
    # Thanh trạng thái chính cố định height=46 vững chắc
    self.status_bar = ctk.CTkFrame(self, fg_color=C["panel2"], height=46, corner_radius=0)
    self.status_bar.pack(side="bottom", fill="x")
    self.status_bar.pack_propagate(False)

    # 1. Chữ trạng thái bên trái ngoài cùng
    self.lbl_status_info = ctk.CTkLabel(self.status_bar, text="Sẵn sàng", font=FONT_SM, text_color=C["muted"])
    self.lbl_status_info.pack(side="left", padx=15)

    # 2. Chữ "Hoàn tất" bên phải ngoài cùng
    self.lbl_status_stats = ctk.CTkLabel(self.status_bar, text="", font=FONT_SM, text_color=C["accent2"])
    self.lbl_status_stats.pack(side="right", padx=15)

    # Khởi tạo sẵn các thành phần tải file TRỰC TIẾP trong status_bar (Chưa dùng pack nên tạm ẩn)
    self.lbl_xfer = ctk.CTkLabel(self.status_bar, text="", font=FONT_SM, text_color=C["text"])

    self.prog_bar = ctk.CTkProgressBar(self.status_bar, height=22,  # Dày 22px to rõ ràng, đẹp mắt
      corner_radius=11, fg_color=C["border"], progress_color=C["accent2"])
    self.prog_bar.set(0)

    self.lbl_xfer_pct = ctk.CTkLabel(self.status_bar, text="0%", font=FONT_BOLD, text_color=C["accent2"])


  # --- LOGIC GIAO DIỆN ---
  def _log(self, kind, msg):
    pref = {"info": "• Trạng thái: ", "cmd": "» Lệnh:       ", "resp": "« Phản hồi:   ", "err": "✕ Lỗi:        "}
    self.txt_log.configure(state="normal")
    self.txt_log.insert("end", f"{pref.get(kind, '              ')}{msg}\n", kind)
    self.txt_log.see("end")
    self.txt_log.configure(state="disabled")

  def _clear_log(self):
    self.txt_log.configure(state="normal")
    self.txt_log.delete(1.0, tk.END)
    self.txt_log.configure(state="disabled")

  def _set_status(self, conn: bool):
    self.status_dot.configure(fg_color=C["accent2"] if conn else C["border2"])
    self.lbl_status.configure(text="Đã kết nối" if conn else "Chưa kết nối",
                              text_color=C["accent2"] if conn else C["muted"])
    self.btn_connect.configure(text="Ngắt kết nối" if conn else "Kết nối",
                               fg_color=C["danger"] if conn else C["accent"])
    if conn: Toast(self, "Kết nối FTP thành công!")

  def _start_connect(self):
    if self.backend.is_connected:
      self.backend.disconnect()
    else:
      self._add_to_history(h := self.ent_host.get().strip(), u := self.ent_user.get().strip())
      self._run_bg(self.backend.connect_login, h, int(self.ent_port.get().strip() or 21), u,
                   self.ent_pass.get().strip())

  # Đã sửa lại tường minh
  def refresh_local(self):
    self.tree_local.delete(*self.tree_local.get_children())
    items = []
    for n in sorted(os.listdir(self.local_dir),
                    key=lambda x: (not os.path.isdir(os.path.join(self.local_dir, x)), x.lower())):
      full_path = os.path.join(self.local_dir, n)
      if os.path.exists(full_path):
        is_dir = os.path.isdir(full_path)
        icon = "📁" if is_dir else "📄"
        size_str = "" if is_dir else f"{os.path.getsize(full_path):,} B"
        type_str = "Thư mục" if is_dir else "Tệp tin"
        items.append((f"{icon}  {n}", size_str, type_str, n.lower()))

    for i in items:
      self.tree_local.insert("", "end", values=i[:3])

    self._update_local_breadcrumb()
    self._filter_local()

  def _display_remote(self, raw):
    self.tree_remote.delete(*self.tree_remote.get_children())
    for l in raw.splitlines():
      if not l.strip() or len(p := l.split(maxsplit=8)) < 9: continue
      is_dir = p[0].startswith("d")
      self.tree_remote.insert("", "end", values=(
        f"{'📁' if is_dir else '📄'}  {p[8].strip()}", "" if is_dir else f"{int(p[4]):,} B",
        "Thư mục" if is_dir else "Tệp tin"))
    self._filter_remote()

  def _filter_local(self, e=None):
    self._filter_tree(self.tree_local, self.src_loc.get().strip().lower())

  def _filter_remote(self, e=None):
    self._filter_tree(self.tree_remote, self.src_rem.get().strip().lower())

  def _filter_tree(self, tree, term):
    for c in tree.get_children():
      tree.reattach(c, "", "end") if term in self._clean_name(tree.item(c, "values")[0]).lower() else tree.detach(c)

  # --- BREADCRUMBS & NAVIGATION ---
  def _local_up(self):
    if (p := os.path.dirname(self.local_dir)) != self.local_dir:
      self.local_dir = p
      self.refresh_local()

  # Đã sửa lại tường minh
  def _cd_up(self):
    if not self.backend.is_connected: return
    parent_dir = os.path.dirname(self.backend.remote_cwd) or "/"
    if "250" in self.backend._send(f"CWD {parent_dir}"):
      self.backend.remote_cwd = parent_dir
      self._update_remote_breadcrumb(parent_dir)
      self._run_bg(self.backend.list_remote)

  def _on_local_dblclick(self, _):
    if not self._sel_local: return
    full = os.path.join(self.local_dir, self._clean_name(self._sel_local[0]))
    if os.path.isdir(full):
      self.local_dir = full
      self.refresh_local()

  def _on_remote_dblclick(self, _):
    if self._sel_remote and self._sel_remote[2] == "Thư mục" and self.backend.is_connected:
      new_p = f"{self.backend.remote_cwd.rstrip('/')}/{self._clean_name(self._sel_remote[0])}"
      if "250" in self.backend._send(f"CWD {new_p}"):
        self.backend.remote_cwd = new_p
        self._update_remote_breadcrumb(new_p)
        self._run_bg(self.backend.list_remote)

  def _update_local_breadcrumb(self):
    for w in self.local_path_bar.winfo_children(): w.destroy()
    ctk.CTkLabel(self.local_path_bar, text="💻 Drives:", font=FONT_BOLD, text_color=C["accent"]).pack(side="left",
                                                                                                      padx=(12, 2))
    import string
    for d in [f"{l}:\\" if os.name == 'nt' else f"{l}:" for l in string.ascii_uppercase]:
      if os.path.exists(d):
        ctk.CTkButton(self.local_path_bar, text=d, font=FONT_BOLD,
                      text_color=C["accent"] if os.path.splitdrive(self.local_dir)[0].upper() == d.upper() else C[
                        "muted"], fg_color="transparent", hover_color=C["panel"], width=0, height=26,
                      command=lambda x=d: self._jump_loc(x)).pack(side="left", padx=2)
    ctk.CTkLabel(self.local_path_bar, text="|", text_color=C["border2"]).pack(side="left", padx=6)
    acc = ""
    # Đã sửa vòng lặp để tránh xung đột scope
    for i, part in enumerate(p for p in os.path.normpath(self.local_dir).split(os.sep) if p):
      acc = os.path.join(acc, part) if i > 0 else part
      if i > 0: ctk.CTkLabel(self.local_path_bar, text=">", text_color=C["border2"]).pack(side="left", padx=2)
      ctk.CTkButton(self.local_path_bar, text=part, font=FONT_MONO, fg_color="transparent", text_color=C["text"],
                    hover_color=C["panel"], width=0, height=26, command=lambda x=acc: self._jump_loc(x)).pack(
        side="left")

  def _update_remote_breadcrumb(self, full_p):
    for w in self.remote_path_bar.winfo_children(): w.destroy()
    ctk.CTkLabel(self.remote_path_bar, text="🌐", font=("Segoe UI", 13)).pack(side="left", padx=(12, 4))
    if full_p in ["Chưa kết nối", ""]:
      ctk.CTkLabel(self.remote_path_bar, text=full_p, text_color=C["accent2"], font=FONT_MONO).pack(side="left", padx=5)
      return

    ctk.CTkButton(self.remote_path_bar, text="Root", font=FONT_MONO, text_color=C["accent2"], fg_color="transparent",
                  hover_color=C["panel"], width=0, height=26, command=lambda: self._jump_rem("/")).pack(side="left",
                                                                                                        padx=1)
    acc = ""
    for p in [x for x in full_p.split("/") if x]:
      acc += "/" + p
      ctk.CTkLabel(self.remote_path_bar, text=">", text_color=C["border2"]).pack(side="left", padx=2)
      ctk.CTkButton(self.remote_path_bar, text=p, font=FONT_MONO, text_color=C["accent2"], fg_color="transparent",
                    hover_color=C["panel"], width=0, height=26, command=lambda x=acc: self._jump_rem(x)).pack(
        side="left")

  def _jump_loc(self, t):
    if os.path.isdir(t):
      self.local_dir = t
      self.refresh_local()

  def _jump_rem(self, t):
    if self.backend.is_connected and "250" in self.backend._send(f"CWD {t}"):
      self.backend.remote_cwd = t
      self._update_remote_breadcrumb(t)
      self._run_bg(self.backend.list_remote)

  # --- KÉO THẢ & CONTEXT MENU ---
  def _on_local_drop(self, e):
    if not self._drag_data or self._drag_data.get("s") != "local" or not self.backend.is_connected: return
    try:
      if self.tree_remote.winfo_rootx() <= e.x_root <= self.tree_remote.winfo_rootx() + self.tree_remote.winfo_width() and self.tree_remote.winfo_rooty() <= e.y_root <= self.tree_remote.winfo_rooty() + self.tree_remote.winfo_height():
        n, t = self._clean_name(self._drag_data["v"][0]), self._drag_data["v"][2]
        self._run_bg(self.backend.upload_directory if t == "Thư mục" else self.backend.upload,
                     os.path.join(self.local_dir, n))
    except:
      pass
    self._drag_data = None

  def _on_remote_drop(self, e):
    if not self._drag_data or self._drag_data.get("s") != "remote" or not self.backend.is_connected: return
    try:
      if self.tree_local.winfo_rootx() <= e.x_root <= self.tree_local.winfo_rootx() + self.tree_local.winfo_width() and self.tree_local.winfo_rooty() <= e.y_root <= self.tree_local.winfo_rooty() + self.tree_local.winfo_height():
        n, t = self._clean_name(self._drag_data["v"][0]), self._drag_data["v"][2]
        if t == "Thư mục":
          target = filedialog.askdirectory(title=f"Lưu '{n}'", initialdir=self.local_dir)
          if target:
            self._run_bg(self.backend.download_directory, n, target)
        else:
          self._run_bg(self.backend.download, n, os.path.join(self.local_dir, n))
    except:
      pass
    self._drag_data = None

  def _show_local_context(self, e):
    m = tk.Menu(self, tearoff=0, bg=C["panel"], fg=C["text"])
    m.add_command(label="📂 Mở thư mục", command=lambda: os.startfile(self.local_dir) if os.name == 'nt' else None)
    m.add_command(label="📋 Copy đường dẫn", command=lambda: self.clipboard_append(self.local_dir))
    m.add_separator()
    m.add_command(label="🔄 Làm mới", command=self.refresh_local)
    m.post(e.x_root, e.y_root)

  def _show_remote_context(self, e):
    if not self.backend.is_connected or not self.tree_remote.focus(): return
    n, t = self._clean_name(self.tree_remote.item(self.tree_remote.focus(), "values")[0]), \
           self.tree_remote.item(self.tree_remote.focus(), "values")[2]
    m = tk.Menu(self, tearoff=0, bg=C["panel"], fg=C["text"])
    m.add_command(label="🔽 Tải xuống", command=lambda: self._handle_download(n, t == "Thư mục"))
    m.add_separator()
    m.add_command(label="✏️ Đổi tên", command=lambda: self._handle_rename(n))
    m.add_command(label="❌ Xóa", command=lambda: self._handle_delete(n, t == "Thư mục"))
    m.post(e.x_root, e.y_root)

  # --- XỬ LÝ NÚT BẤM (ACTIONS) - Đã sửa lại tường minh ---
  def _handle_upload(self):
    if not self.backend.is_connected:
      return messagebox.showwarning("Cảnh báo", "Chưa kết nối!")

    m = tk.Menu(self, tearoff=0, bg=C["panel"], fg=C["text"])

    def choose_and_upload_file():
      p = filedialog.askopenfilename(initialdir=self.local_dir)
      if p:
        self._run_bg(self.backend.upload, p)

    def choose_and_upload_dir():
      p = filedialog.askdirectory(initialdir=self.local_dir)
      if p:
        self._run_bg(self.backend.upload_directory, p)

    m.add_command(label="📄 Tải lên File lẻ", command=choose_and_upload_file)
    m.add_command(label="📁 Tải lên Cả Thư mục", command=choose_and_upload_dir)
    m.post(self.winfo_pointerx(), self.winfo_pointery())

  def _handle_download(self, name=None, is_dir=None):
    if not self.backend.is_connected:
      return messagebox.showwarning("Cảnh báo", "Chưa kết nối!")
    if not name and not self._sel_remote:
      return messagebox.showwarning("Chọn mục", "Chưa chọn file/folder remote!")

    n = name or self._clean_name(self._sel_remote[0])
    d = is_dir if is_dir is not None else (self._sel_remote[2] == "Thư mục")

    if d:
      target_path = filedialog.askdirectory(title=f"Lưu '{n}'", initialdir=self.local_dir)
      if target_path:
        self._run_bg(self.backend.download_directory, n, target_path)
    else:
      target_path = filedialog.asksaveasfilename(initialdir=self.local_dir, initialfile=n)
      if target_path:
        self._run_bg(self.backend.download, n, target_path)

  def _handle_mkdir(self):
    if not self.backend.is_connected: return
    if n := LargeInputDialog("Tạo thư mục", "Nhập tên:").get_input():
      self._run_bg(self.backend.mkdir, n)

  def _handle_rename(self, name=None):
    if not self.backend.is_connected: return
    n = name or (self._clean_name(self._sel_remote[0]) if self._sel_remote else None)
    if not n: return messagebox.showwarning("Chọn mục", "Chưa chọn mục!")
    if new := LargeInputDialog("Đổi tên", f"Tên mới cho '{n}':", 550, 300).get_input():
      if new != n: self._run_bg(self.backend.rename_item, n, new)

  def _handle_delete(self, name=None, is_dir=None):
    if not self.backend.is_connected: return
    n = name or (self._clean_name(self._sel_remote[0]) if self._sel_remote else None)
    d = is_dir if is_dir is not None else (self._sel_remote[2] == "Thư mục" if self._sel_remote else False)
    if n and messagebox.askyesno("Xác nhận", f"Xóa {n}?"):
      self._run_bg(self.backend.delete_item, n, d)

  def _handle_refresh_rem(self):
    if self.backend.is_connected:
      self._jump_rem("/")

  # --- TRẠNG THÁI & PROGRESS BAR ---
  def _show_xfer(self, label):
    if len(label) > 25:
        label = label[:22] + "..."

    self.lbl_status_stats.configure(text="") # Dọn chữ hoàn tất cũ nếu có
    self.lbl_xfer.configure(text=f"⚡ {label}")
    self.lbl_xfer_pct.configure(text="0%")
    self.prog_bar.set(0)

    # Thứ tự pack trong cùng một dòng quyết định vị trí:
    # Pack 2 đầu trước, thanh Progress Bar ở giữa sẽ fill và expand chiếm trọn vùng trống còn lại!
    self.lbl_xfer.pack(side="left", padx=(10, 15))
    self.lbl_xfer_pct.pack(side="right", padx=(15, 15))
    self.prog_bar.pack(side="left", fill="x", expand=True)

  def _hide_xfer(self):
    # Gỡ bỏ trạng thái hiển thị của các thành phần tải file
    self.prog_bar.pack_forget()
    self.lbl_xfer.pack_forget()
    self.lbl_xfer_pct.pack_forget()

    # Hiển thị chữ thông báo hoàn tất ở góc phải
    self.lbl_status_stats.configure(text="✔ Hoàn tất")
    self.after(2500, lambda: self.lbl_status_stats.configure(text=""))

  def _update_progress(self, pct):
    self.prog_bar.set(pct / 100)
    self.lbl_xfer_pct.configure(text=f"{int(pct)}%")


if __name__ == "__main__":
  FTPClientApp().mainloop()