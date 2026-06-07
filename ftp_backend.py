# ftp_backend.py
import socket, os, threading, time
from tkinter import messagebox

# Nâng cấp lên 1 MB để truyền tải tệp tin dung lượng lớn với tốc độ tối đa
BUFFER_SIZE = 1024 * 1024


class FTPBackend:
  def __init__(self, app):
    self.app = app
    self.cmd_socket = None
    self.is_connected = False
    self.remote_cwd = "/"
    self._lock = threading.Lock()

  # ─── HELPER FUNCTIONS ───
  def _ui(self, func, *args):
    self.app.after(0, lambda: func(*args))

  def _err(self, title, msg):
    self._ui(messagebox.showerror, title, msg)

  def _msg(self, title, msg):
    self._ui(messagebox.showinfo, title, msg)

  def _log(self, kind, text):
    self._ui(self.app._log, kind, text)

  def _check(self):
    return self.is_connected and self.cmd_socket

  # ─── CORE NETWORK ───
  def _recv_response(self):
    if not self.cmd_socket: return ""
    data = b""
    while True:
      try:
        chunk = self.cmd_socket.recv(4096)
        if not chunk: break
        data += chunk
        lines = data.decode("utf-8", errors="ignore").splitlines()
        if any(len(l) >= 4 and l[:3].isdigit() and l[3] == " " for l in reversed(lines)):
          return data.decode("utf-8", errors="ignore")
        self.cmd_socket.settimeout(1.0)
      except socket.timeout:
        break
      except (socket.error, ConnectionError):
        raise
      except Exception:
        break
    return data.decode("utf-8", errors="ignore")

  def _send(self, cmd):
    if not self.cmd_socket: return ""
    try:
      self._log("cmd", cmd)
      self.cmd_socket.sendall((cmd + "\r\n").encode("utf-8"))
      if cmd.upper() == "QUIT": return "221 Goodbye."

      resp = self._recv_response()
      if not resp.strip(): raise ConnectionResetError("Server ngắt phản hồi (Kênh đã đóng).")
      self._log("resp", resp.strip())
      return resp
    except Exception as e:
      if not self.is_connected: return ""
      # Phân loại lỗi mất kết nối giữa chừng
      if isinstance(e, ConnectionResetError):
        msg = "Máy chủ FTP đã đóng kết nối đột ngột.\nCó thể FileZilla Server bị tắt hoặc restart."
      elif isinstance(e, socket.timeout):
        msg = "Hết thời gian chờ phản hồi từ máy chủ.\nKiểm tra lại kết nối mạng hoặc trạng thái server."
      elif isinstance(e, ConnectionRefusedError):
        msg = "Kết nối bị từ chối.\nFileZilla Server có thể đã ngừng hoạt động."
      elif isinstance(e, BrokenPipeError):
        msg = "Đường truyền bị gián đoạn đột ngột.\nKiểm tra lại kết nối mạng."
      else:
        msg = f"Mất kết nối: {e}"
      self._log("err", f"✕ MẤT KẾT NỐI: {msg.splitlines()[0]}")
      self._force_offline()
      self._err("Mất kết nối", msg)
      return ""

  def _force_offline(self):
    # Đặt trạng thái offline ngay lập tức, dọn dẹp socket
    self.is_connected = False
    if self.cmd_socket:
      try: self.cmd_socket.close()
      except: pass
    self.cmd_socket = None
    self.remote_cwd = "/"
    # Cập nhật toàn bộ UI về trạng thái ngắt kết nối
    self._ui(self.app._set_status, False)
    self._ui(self.app.remote_path_var.set, "⚠ Mất kết nối — Nhấn Kết nối để thử lại")
    self._ui(lambda: self.app.tree_remote.delete(*self.app.tree_remote.get_children()))
    self._ui(self.app._hide_xfer)   # ẩn progress bar nếu đang hiện

  def disconnect(self):
    if self.cmd_socket:
      self.is_connected = False
      try:
        self._send("QUIT")
      except:
        pass
      try:
        self.cmd_socket.close()
      except:
        pass
    self._force_offline()
    self._log("info", "🔌 Đã chủ động ngắt kết nối an toàn.")
    self._msg("Ngắt kết nối", "Đã ngắt kết nối khỏi máy chủ FTP.")

  def _pasv_data_sock(self):
    r = self._send("PASV")
    if not r: raise Exception("Lỗi chế độ PASV.")
    s, e = r.find("("), r.find(")")
    nums = list(map(int, r[s + 1:e].split(",")))

    ds = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ds.settimeout(30)

    # 💥 BẬT TỐI ƯU HÓA SOCKET Ở CẤP ĐỘ HỆ ĐIỀU HÀNH (Mở rộng băng thông TCP)
    try:
      ds.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, BUFFER_SIZE)  # Nới rộng bộ đệm nhận mạng
      ds.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, BUFFER_SIZE)  # Nới rộng bộ đệm gửi mạng
      ds.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # Tắt thuật toán Nagle (gửi gói tin đi ngay lập tức)
    except:
      pass

    ds.connect((f"{nums[0]}.{nums[1]}.{nums[2]}.{nums[3]}", (nums[4] << 8) + nums[5]))
    return ds

  # ─── LOGIN & LIST ───
  def connect_login(self, host, port, user, pwd):
    try:
      # ── Bước 1: Mở kết nối TCP ─────────────────────────────────────────
      self._log("info", f"[1/5] Đang kết nối {host}:{port}...")
      self.cmd_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      self.cmd_socket.settimeout(10)
      try:
        self.cmd_socket.connect((host, port))
      except ConnectionRefusedError:
        raise Exception(
          f"Không thể kết nối tới {host}:{port}\n\n"
          "Nguyên nhân có thể:\n"
          "  • FileZilla Server chưa được khởi động\n"
          "  • Sai địa chỉ IP hoặc cổng\n"
          "  • Tường lửa đang chặn kết nối"
        )
      except socket.timeout:
        raise Exception(
          f"Hết thời gian kết nối tới {host}:{port}\n\n"
          "Nguyên nhân có thể:\n"
          "  • Server không phản hồi (quá tải hoặc tắt)\n"
          "  • Địa chỉ IP không đúng\n"
          "  • Kết nối mạng có vấn đề"
        )
      except OSError as ex:
        raise Exception(f"Lỗi mạng khi kết nối: {ex}")

      banner = self.cmd_socket.recv(4096).decode("utf-8", "ignore").strip()
      self._log("resp", banner)

      # ── Bước 2: Đăng nhập ──────────────────────────────────────────────
      resp_user = self._send("USER " + user)
      if "331" not in resp_user:
        raise Exception(
          f"Server từ chối tên đăng nhập '{user}'\n\n"
          f"Phản hồi server: {resp_user.strip()}"
        )

      resp_pass = self._send("PASS " + pwd)
      if "230" not in resp_pass:
        # Phân biệt sai mật khẩu vs các lỗi khác
        if "530" in resp_pass:
          raise Exception(
            "Sai tên đăng nhập hoặc mật khẩu\n\n"
            "Vui lòng kiểm tra lại thông tin đăng nhập trong FileZilla Server."
          )
        raise Exception(
          f"Đăng nhập thất bại\n\n"
          f"Phản hồi server: {resp_pass.strip()}"
        )

      # ── Bước 3: Thiết lập phiên ────────────────────────────────────────
      self.is_connected = True
      self._send("TYPE I")
      self.cmd_socket.settimeout(30)

      r = self._send("PWD")
      self.remote_cwd = r.split('"')[1] if '"' in r else "/"
      self._ui(self.app.remote_path_var.set, self.remote_cwd)
      self._ui(self.app._set_status, True)
      self.list_remote()

    except Exception as e:
      self._force_offline()
      self._log("err", f"✕ Kết nối thất bại: {str(e).splitlines()[0]}")
      self._err("Kết nối thất bại", str(e))

  def list_remote(self):
    if not self._check(): return
    with self._lock:
      try:
        ds = self._pasv_data_sock()
        self.cmd_socket.sendall(b"LIST\r\n")
        if not self._recv_response(): return

        raw = b""
        while chunk := ds.recv(BUFFER_SIZE): raw += chunk
        ds.close()

        self._recv_response()
        self._ui(self.app._display_remote, raw.decode("utf-8", "ignore"))
      except Exception as e:
        self._log("err", f"LỖI LIST: {e}")

  # ─── UPLOAD & DOWNLOAD ───
  def upload(self, filepath):
    if not self._check(): return
    fname = os.path.basename(filepath)
    try:
      with self._lock:
        self._upload_internal(filepath, fname)
      self.list_remote()
      self._msg("Hoàn tất", f"Upload {fname} thành công!")
    except Exception as e:
      self._ui(self.app._hide_xfer)
      self._err("Lỗi upload", str(e))

  def _upload_internal(self, filepath, fname):
    fsize = os.path.getsize(filepath)
    ds = self._pasv_data_sock()
    self.cmd_socket.sendall(f"STOR {fname}\r\n".encode("utf-8"))
    if "150" not in (r1 := self._recv_response()) and "125" not in r1:
      ds.close()
      raise Exception(f"Server từ chối STOR: {r1}")

    self._ui(self.app._show_xfer, f"Đang upload: {fname}")
    sent, last_upd = 0, 0.0

    # Thêm tham số buffering=BUFFER_SIZE để tăng tốc đọc file từ ổ đĩa
    with open(filepath, "rb", buffering=BUFFER_SIZE) as f:
      while chunk := f.read(BUFFER_SIZE):
        ds.sendall(chunk)
        sent += len(chunk)

        # Tối ưu hóa điều kiện kiểm tra (Throttling) giúp giảm tải xử lý CPU
        now = time.time()
        if now - last_upd > 0.15:
          self._ui(self.app._update_progress, (sent / fsize * 100) if fsize else 100)
          last_upd = now

    ds.close()
    self._recv_response()
    self._ui(self.app._hide_xfer)

  def download(self, remote_name, local_path):
    if not self._check(): return
    try:
      with self._lock:
        self._download_internal(remote_name, local_path)
      if self.is_connected:
        self._ui(self.app.refresh_local)
        self._msg("Hoàn tất", f"Đã tải {remote_name} thành công!")
    except Exception as e:
      err = str(e).strip()
      err = err if err and err != "None" else "Mất kết nối mạng giữa chừng."
      self._log("err", f"✕ LỖI DOWNLOAD: {err}")
      self._ui(self.app._hide_xfer)
      self._err("Lỗi download", f"Không thể tải tệp!\n{err}")

  def _download_internal(self, remote_name, local_path):
    size_resp = self._send(f"SIZE {remote_name}")
    if not size_resp: raise ConnectionResetError("Mất kết nối khi gọi SIZE.")
    fsize = int(size_resp.split()[1]) if size_resp.startswith("213") else 0

    ds = self._pasv_data_sock()
    self.cmd_socket.sendall(f"RETR {remote_name}\r\n".encode("utf-8"))
    if "150" not in (r1 := self._recv_response()) and "125" not in r1:
      ds.close()
      raise Exception(f"Từ chối RETR: {r1}")

    self._ui(self.app._show_xfer, f"Đang tải: {remote_name}")
    down, last_upd, err_net = 0, 0.0, None

    try:
      # Thêm tham số buffering=BUFFER_SIZE để tăng tốc ghi file trực tiếp xuống ổ đĩa cực nhanh
      with open(local_path, "wb", buffering=BUFFER_SIZE) as f:
        while chunk := ds.recv(BUFFER_SIZE):
          f.write(chunk)
          down += len(chunk)

          now = time.time()
          if now - last_upd > 0.15:
            self._ui(self.app._update_progress, (down / fsize * 100) if fsize else 50)
            last_upd = now
    except Exception as e:
      err_net = f"Đứt mạng: {e}"
    finally:
      ds.close()

    if err_net:
      if os.path.exists(local_path): os.remove(local_path)
      raise ConnectionResetError(err_net)

    if not self._recv_response():
      if os.path.exists(local_path): os.remove(local_path)
      raise ConnectionResetError("Server sập trước khi tải xong.")
    self._ui(self.app._hide_xfer)

  # ─── ACTIONS & DIRS ───
  def _quick_cmd(self, cmd, expected):
    if not self._check(): return
    try:
      with self._lock:
        if expected not in (r := self._send(cmd)): raise Exception(r)
      self.list_remote()
    except Exception as e:
      self._err("Lỗi", str(e))

  def mkdir(self, name):
    self._quick_cmd(f"MKD {name}", "25")

  def delete_item(self, name, is_dir):
    self._quick_cmd(f"RMD {name}" if is_dir else f"DELE {name}", "250")

  def rename_item(self, old, new):
    if not self._check(): return
    try:
      with self._lock:
        if "350" not in self._send(f"RNFR {old}"): raise Exception("Lỗi RNFR")
        if "250" not in self._send(f"RNTO {new}"): raise Exception("Lỗi RNTO")
      self.list_remote()
    except Exception as e:
      self._err("Lỗi đổi tên", str(e))

  def upload_directory(self, local_path):
    base_dir = os.path.basename(local_path.rstrip(os.sep))
    try:
      with self._lock:
        self._up_dir_rec(local_path, base_dir)
      self.list_remote()
      self._msg("Hoàn tất", f"Upload thư mục '{base_dir}' thành công!")
    except Exception as e:
      self._err("Lỗi", str(e))

  def _up_dir_rec(self, l_path, r_name):
    self._send(f"MKD {r_name}")
    self._send(f"CWD {r_name}")
    for item in os.listdir(l_path):
      p = os.path.join(l_path, item)
      self._up_dir_rec(p, item) if os.path.isdir(p) else self._upload_internal(p, item)
    self._send("CDUP")

  def download_directory(self, r_name, l_base):
    try:
      with self._lock:
        self._dn_dir_rec(r_name, os.path.join(l_base, r_name))
      self._ui(self.app.refresh_local)
      self._msg("Hoàn tất", f"Tải thư mục '{r_name}' thành công!")
    except Exception as e:
      self._err("Lỗi", str(e))

  def _dn_dir_rec(self, r_name, l_path):
    os.makedirs(l_path, exist_ok=True)
    self._send(f"CWD {r_name}")
    ds = self._pasv_data_sock()
    self.cmd_socket.sendall(b"LIST\r\n")
    self._recv_response()
    raw = b""
    while chunk := ds.recv(BUFFER_SIZE): raw += chunk
    ds.close()
    self._recv_response()

    for line in raw.decode("utf-8", "ignore").splitlines():
      if not line.strip() or len(parts := line.split(maxsplit=8)) < 9: continue
      name = parts[8].strip()
      if name in (".", ".."): continue
      sub = os.path.join(l_path, name)
      self._dn_dir_rec(name, sub) if parts[0].startswith("d") else self._download_internal(name, sub)
    self._send("CDUP")