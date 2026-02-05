# Oracle Database MCP Server 🗄️

[English](README.md) | [Tiếng Việt](README.vi.md)

Một **Model Context Protocol (MCP)** server toàn diện cho các thao tác Oracle Database. Server này cho phép các trợ lý AI tương tác với cơ sở dữ liệu Oracle thông qua giao diện an toàn và được định nghĩa rõ ràng.

## 🌟 Tính năng Mới (Multi-Database)

- **Hỗ trợ Đa Cơ sở Dữ liệu**: Kết nối đồng thời nhiều DB (Dev, Prod, Test).
- **Khám phá Thông minh (Smart Discovery)**: Công cụ `locate_table` giúp AI tự tìm bảng dữ liệu nằm ở đâu.
- **Connection Pooling**: Quản lý kết nối hiệu quả cho từng database.

### Các công cụ có sẵn (22+)

#### 🌐 Khám phá & Kết nối (Mới!)

| Công cụ            | Mô tả                                                             |
| ------------------ | ----------------------------------------------------------------- |
| `list_databases`   | Liệt kê các kết nối database đã cấu hình & trạng thái             |
| `locate_table`     | **Tìm kiếm toàn cục**: Tìm xem bảng nằm ở database nào            |
| `get_session_info` | Xem thông tin session chi tiết cho tất cả các pool đang hoạt động |

#### 📋 Thao tác cơ sở dữ liệu cơ bản

_(Tất cả công cụ nay hỗ trợ tham số tùy chọn `database_name`)_

| Công cụ                     | Mô tả                                                |
| --------------------------- | ---------------------------------------------------- |
| `list_tables`               | Liệt kê tất cả các bảng người dùng hiện tại có quyền |
| `describe_table`            | Lấy schema/cấu trúc của một bảng cụ thể              |
| `run_read_only_query`       | Thực thi các truy vấn SELECT an toàn                 |
| `run_query_with_pagination` | SELECT với hỗ trợ phân trang                         |
| `run_modification_query`    | INSERT, UPDATE, DELETE, CREATE, DROP với auto-commit |

#### 🔍 DDL & Kiểm tra sâu (Deep Inspection)

| Công cụ            | Mô tả                                          |
| ------------------ | ---------------------------------------------- |
| `get_object_ddl`   | Lấy DDL/Source code của bảng, view, package... |
| `list_constraints` | Liệt kê khóa chính (PK), khóa ngoại (FK)...    |
| `list_indexes`     | Xem danh sách index và các cột được đánh index |

#### 🔎 Công cụ tìm kiếm

| Công cụ           | Mô tả                                             |
| ----------------- | ------------------------------------------------- |
| `search_in_table` | Tìm kiếm toàn văn bản trên tất cả các cột văn bản |

#### 📊 Hiệu suất & Quản trị (Admin)

| Công cụ              | Mô tả                                       |
| -------------------- | ------------------------------------------- |
| `explain_query_plan` | Phân tích kế hoạch thực thi (Query Plan)    |
| `inspect_locks`      | Xem các session đang bị kẹt (Lock/Blocking) |
| `kill_session`       | Ngắt kết nối session bị treo (Cẩn thận!)    |

#### 📤 Import/Export

| Công cụ               | Mô tả                             |
| --------------------- | --------------------------------- |
| `export_query_to_csv` | Xuất kết quả truy vấn ra file CSV |

## 🚀 Hướng dẫn Cài đặt & Thiết lập

> **Quan trọng**: Hãy làm theo tuần tự 3 bước sau để server hoạt động ổn định.

### Bước 1: Cài đặt Server (`install.bat`)

Chúng tôi đã tối ưu hóa quá trình cài đặt vào một file script duy nhất.

1.  **Tải/Clone** dự án này về máy của bạn.
2.  **Chạy file `install.bat`**:
    - Click đúp chuột vào file `install.bat` trong thư mục dự án.
    - _Hoặc_ chạy từ CMD:
      ```cmd
      cd path\to\mcp-oracle-server
      install.bat
      ```
    - Script này sẽ tự động cài đặt các thư viện Python cần thiết và đăng ký lệnh `mcp-oracle-server`.

### Bước 2: Cấu hình Kết nối Database (`oracle_config.json`)

Mọi thông tin kết nối database sẽ được lưu ở đây. Server hỗ trợ kết nối nhiều DB cùng lúc.

1.  Tìm file `oracle_config.example.json` trong thư mục dự án.
2.  Đổi tên nó thành `oracle_config.json`.
3.  Mở file và cập nhật thông tin database của bạn.

**Ví dụ nội dung `oracle_config.json` chuẩn:**

```json
{
  "databases": [
    {
      "name": "nim059",
      "user": "your_username",
      "password": "your_password",
      "host": "192.168.1.xxx",
      "port": "1521",
      "service_name": "orclpdb"
    },
    {
      "name": "local_dev",
      "user": "sys",
      "password": "password123",
      "dsn": "localhost:1521/orcl",
      "mode": "SYSDBA"
    }
  ],
  "global_settings": {
    "oracle_client_path": "C:\\path\\to\\instantclient_23_0",
    "default_database": "nim059",
    "pool_min": 2,
    "pool_max": 10
  }
}
```

> **Lưu ý**: `oracle_client_path` phải trỏ đúng đến thư mục chứa file `oci.dll`. Trong dự án đã có sẵn thư mục `instantclient_23_0`, bạn nên dùng đường dẫn tuyệt đối như ví dụ trên để tránh lỗi.

### Bước 3: Cấu hình AI Client (`mcp_config.json`)

Để AI (Google Gemini, Antigravity, VS Code) nhận diện được server này, bạn cần khai báo nó trong file cấu hình MCP của client.

**Vị trí file:**

- **Antigravity / Gemini**: `c:\Users\User\.gemini\antigravity\mcp_config.json`

**Nội dung cần thêm vào:**

```json
{
  "mcpServers": {
    "oracle-server": {
      "command": "python",
      "args": ["-m", "mcp_oracle_server"],
      "env": {
        "PYTHONIOENCODING": "utf-8",
        "PYTHONPATH": "D:\\path\\to\\mcp-oracle-server\\src",
        "ORACLE_CONFIG_DIR": "D:\\path\\to\\mcp-oracle-server"
      }
    }
  }
}
```

**Giải thích thông số:**

- `command`: Dùng `python` để đảm bảo chạy đúng môi trường.
- `args`: Chạy module server.
- `PYTHONPATH`: **Rất quan trọng**. Phải trỏ vào thư mục `src` để Python tìm thấy code.
- `ORACLE_CONFIG_DIR`: Chỉ định nơi chứa file `oracle_config.json` (thường là thư mục gốc của dự án).

---

## 📁 Cấu trúc dự án

```
mcp-oracle-server/
├── server.py          # MCP server chính (Multi-DB)
├── config.py          # Quản lý cấu hình (JSON + Env)
├── oracle_config.json # Hồ sơ kết nối Database
├── logger.py          # Ghi log và theo dõi truy vấn
├── .env               # Cấu hình cũ (single DB)
├── instantclient_23_0/ # Oracle Instant Client
└── README.md          # File này
```

## 🔧 Tùy chọn Cấu hình

### `oracle_config.json`

| Khóa       | Mô tả                                               |
| ---------- | --------------------------------------------------- |
| `name`     | Định danh duy nhất cho database (vd: `dev`, `prod`) |
| `dsn`      | Copy chuỗi kết nối (vd: `host:port/service`)        |
| `mode`     | Tùy chọn. Đặt `SYSDBA` cho kết nối admin            |
| `encoding` | Tùy chọn. Mặc định `UTF-8`                          |

### Bảng được bảo vệ

Chỉnh sửa `config.py` để thêm các bảng không nên được sửa đổi:

```python
PROTECTED_TABLES = [
    "SYS",
    "SYSTEM",
    "AUDIT_TRAIL",
    # Thêm các bảng nhạy cảm của bạn ở đây
]
```

## 🔒 Tính năng bảo mật

1. **Ngăn chặn SQL Injection**
   - Tất cả tên bảng được xác thực theo mẫu định danh an toàn
   - Sử dụng parameterized queries trong toàn bộ hệ thống

2. **Hạn chế truy vấn**
   - Các truy vấn SELECT bị chặn không chứa từ khóa DML
   - Các lệnh nguy hiểm (DROP DATABASE, v.v.) bị chặn

3. **Bảng được bảo vệ**
   - Danh sách các bảng có thể cấu hình không thể sửa đổi

4. **Connection Pooling**
   - Kết nối được quản lý và giải phóng đúng cách
   - Không để lộ thông tin xác thực

## 📊 Ví dụ sử dụng

### 1. Khám phá (Dữ liệu của tôi ở đâu?)

```python
# Tìm xem bảng 'EMPLOYEES' nằm ở database nào
locate_table("EMPLOYEES")
# Kết quả: Found in database 'HR_PROD'

# Liệt kê tất cả các môi trường đang kết nối
list_databases()
```

### 2. Truy vấn Đa Database

```python
# Query a specific database
run_read_only_query("SELECT * FROM employees", database_name="HR_PROD")

# List tables in Finance DB
list_tables(database_name="finance_prod")
```

### 3. Truy vấn Cơ bản (Default DB)

```python
# Uses the default_database defined in json
describe_table("PRODUCTS")
```

## 📜 Giấy phép

Giấy phép MIT - Thoải mái sử dụng và chỉnh sửa!

## 🤝 Đóng góp

Chào đón các đóng góp! Vui lòng gửi issues và pull requests.

---

**Được xây dựng với ❤️ cho quản lý cơ sở dữ liệu doanh nghiệp hỗ trợ bởi AI**
