🌐 Dự án Lập trình mạng: Python FTP Client & Server

Đây là một dự án ứng dụng Lập trình mạng, mô phỏng quá trình giao tiếp và truyền tải dữ liệu theo giao thức FTP giữa mô hình Client-Server. Hệ thống được viết hoàn toàn bằng Python, với kiến trúc phân lớp thư mục rõ ràng giữa máy khách (client) và hệ thống lưu trữ trên máy chủ (server).

🚀 Tổng quan Tính năng

Kiến trúc Client-Server: Giao tiếp thông qua các tập lệnh của giao thức FTP tiêu chuẩn.

Tương tác Client (main.py, ftp_backend.py): Giao diện và luồng xử lý chính cho phép người dùng cấu hình kết nối, tải lên (upload), tải xuống (download) và quản lý tập tin trên máy chủ từ xa.

Lưu trữ Cấu hình: Thông tin kết nối FTP được lưu trữ cục bộ dưới dạng file JSON (connections.json) giúp người dùng tái sử dụng nhanh chóng mà không cần nhập lại.

Phân quyền Server Storage: Hệ thống lưu trữ của máy chủ (Server Storage) được phân cấp theo từng phòng ban và quyền hạn rõ ràng như admin, share, và các thư mục người dùng riêng biệt (user/IT, user/KT, user/VP).

📁 Cấu trúc Thư mục

Dự án được thiết kế theo mô hình module hóa, tối ưu khả năng mở rộng:

📦 Do_An_Lap_Trinh_Mang
 ┣ 📂 client/
 ┃ ┗ 📂 main/
 ┃   ┣ 📜 main.py               # Điểm khởi chạy của Client (Xử lý giao diện CLI/Luồng chính)
 ┃   ┣ 📜 ftp_backend.py        # Core xử lý các kết nối mạng, socket và tập lệnh FTP
 ┃   ┣ 📜 constants.py          # Khai báo các hằng số cấu hình toàn cục
 ┃   ┗ 📜 connections.json      # Cơ sở dữ liệu cấu hình phiên kết nối
 ┣ 📂 server/
 ┃ ┗ 📂 storage/
 ┃   ┣ 📂 admin/                # Thư mục lưu trữ riêng của Quản trị viên
 ┃   ┣ 📂 share/                # Thư mục dữ liệu chia sẻ chung
 ┃   ┗ 📂 user/                 # Thư mục phân quyền theo phòng ban
 ┃     ┣ 📂 IT/                 # Dữ liệu phòng CNTT (xlsx, docx, pdf...)
 ┃     ┣ 📂 KT/                 # Dữ liệu phòng Kế toán
 ┃     ┗ 📂 VP/                 # Dữ liệu phòng Văn phòng
 ┗ 📜 README.md                 # Tài liệu mô tả dự án


🛠️ Hướng dẫn Cài đặt & Sử dụng Chi tiết

1. Chuẩn bị Môi trường & Mã nguồn

Yêu cầu hệ thống: Python 3.7 trở lên. Thư viện kết nối sử dụng các gói built-in (ftplib, json, os) nên không cần cài đặt thêm dependency phức tạp cho Client.

Tải mã nguồn:

git clone https://github.com/Tên-Tài-Khoản/Do_An_Lap_Trinh_Mang.git
cd Do_An_Lap_Trinh_Mang


2. Thiết lập FTP Server (Dành cho kiểm thử cục bộ)

Dự án đã định nghĩa sẵn cấu trúc thư mục server/storage/ để làm nơi chứa dữ liệu. Nếu bạn chưa có máy chủ FTP vật lý hoặc VPS, bạn có thể dễ dàng dựng một FTP Server ngay trên máy tính của mình bằng thư viện pyftpdlib để kiểm thử Client:

Cài đặt thư viện tạo server:

pip install pyftpdlib


Di chuyển vào thư mục Storage của server:

cd server/storage


Khởi chạy FTP Server cục bộ (Chạy ở cổng 2121, cho phép quyền ghi -w):

python -m pyftpdlib -p 2121 -w


Lưu ý: Treo cửa sổ terminal này để Server duy trì trạng thái hoạt động.

3. Khởi chạy & Thao tác trên Ứng dụng Client

Mở một cửa sổ Terminal (hoặc Command Prompt) mới, độc lập với cửa sổ đang chạy Server.

Bước 1: Chạy chương trình

# Di chuyển vào thư mục luồng chính của client
cd client/main/

# Khởi chạy ứng dụng
python main.py


Bước 2: Cấu hình kết nối
Nếu bạn đang test bằng server mô phỏng ở trên, hãy nhập IP là 127.0.0.1 (hoặc localhost), Port là 2121, đăng nhập ẩn danh (Anonymous) hoặc bằng tài khoản test.
Dữ liệu đăng nhập thành công sẽ được hệ thống lưu tự động vào connections.json để bạn thao tác nhanh cho lần sau.
Bước 3: Sử dụng các tính năng mạng
Tại giao diện/dòng lệnh của Client, bạn có thể thực hiện các luồng công việc:
Tải file lên (Upload / STOR): Đẩy tài liệu từ máy cá nhân vào các thư mục phòng ban tương ứng (như user/IT/ hoặc user/KT/).
Tải file xuống (Download / RETR): Kéo các file báo cáo, bảng tính (.xlsx, .docx) từ Server về máy.
Duyệt cây thư mục (List / CWD): Hiển thị và di chuyển qua lại giữa các cấp thư mục phân quyền của Admin và User.
