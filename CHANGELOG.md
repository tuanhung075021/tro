# Changelog

Tất cả những thay đổi đáng chú ý của dự án **tro.** sẽ được ghi chép trong tài liệu này.

Định dạng tài liệu dựa trên [Keep a Changelog](https://keepachangelog.com/vi/1.0.0/), và dự án này tuân thủ theo [Semantic Versioning](https://semver.org/lang/vi/).

---

## [Unreleased]

### Changed
- refactor: Cập nhật định danh thương hiệu hệ thống thành **tro.**

### Added
- ci: Thiết lập GitHub Actions tự động kiểm tra License Compliance và Unit Tests trên mỗi commit.

### Planned
- Xây dựng Core Engine tính toán điện bậc thang và định mức theo Thông tư 60/2025/TT-BCT và Quyết định 1279/QĐ-BCT.
- Phát triển RESTful API backend bằng FastAPI phục vụ quản lý phòng, cơ sở và tính tiền điện nước.
- Xây dựng giao diện web React trực quan hóa hóa đơn và đối chiếu tiền điện nước.

---

## [0.1.0] - 2026-09-10

### Added
- **Khung cấu trúc dự án FOSS chuẩn mực**:
  - Khởi tạo cây thư mục chức năng phân tầng: `core/` (engine tính toán), `tests/` (kiểm thử tự động), `backend/app/` (FastAPI backend), `frontend/` (React frontend), `scripts/` (công cụ quản trị).
  - Bổ sung file đánh dấu `.gitkeep` tại tất cả các thư mục rỗng để đảm bảo Git theo dõi đầy đủ.
- **Giấy phép mã nguồn mở**:
  - Ban hành toàn văn giấy phép **MIT License** chuẩn OSI-approved tại file `LICENSE` với thông tin bản quyền: `Copyright (c) 2026 tro Contributors`.
- **Cấu hình loại trừ Git (`.gitignore`)**:
  - Thiết lập bộ quy tắc loại trừ hoàn chỉnh cho hệ sinh thái Python (`__pycache__/`, `*.py[cod]`, `.venv/`, `.pytest_cache/`), Node/Web (`node_modules/`, `dist/`, `.env.local`), cơ sở dữ liệu & nhật ký runtime (`*.db`, `*.sqlite3`, `*.log`), và cấu hình IDE / hệ điều hành (`.vscode/`, `.idea/`, `Thumbs.db`, `.DS_Store`).
- **Công cụ quản lý & kiểm tra License Header (`scripts/add_license_headers.py`)**:
  - Xây dựng script bằng 100% Python Standard Library, không phụ thuộc gói ngoài.
  - Tự động quét và phát hiện file mã nguồn (`.py`, `.sh`, `.js`, `.ts`, `.tsx`, `.css`) thiếu License Header.
  - Tự động chèn khối comment MIT License Header tương ứng theo chuẩn ngôn ngữ (`#` cho Python/Shell và `/* ... */` cho JS/TS/CSS).
  - Hỗ trợ cờ `--check` phục vụ quy trình CI/CD và kiểm tra tuân thủ trước khi commit (exit code `0` khi hợp lệ, `1` khi phát hiện vi phạm).
  - Tự động bỏ qua các thư mục rác và thư mục hệ thống: `.git`, `node_modules`, `.venv`, `dist`, `__pycache__`, `document`.
  - Bảo toàn Shebang line, khai báo mã hóa PEP 263, định dạng dòng CRLF/LF và bảng mã ký tự.
- **Bộ kiểm thử đơn vị cơ sở (`tests/test_license_headers.py`)**:
  - Xây dựng bộ test toàn diện gồm 34 trường hợp kiểm thử cho công cụ License Header, bao gồm kiểm tra phát hiện thiếu header, chèn header, xử lý UTF-8 BOM, non-UTF-8 encodings, CRLF/LF preservation, và CLI exit code.
- **Bộ tài liệu dự án FOSS khởi đầu**:
  - Bổ sung `README.md` toàn diện với căn cứ pháp lý (QĐ 1279/QĐ-BCT, TT 60/2025/TT-BCT, NĐ 133/2026/NĐ-CP, NQ 204/2025/QH15), sơ đồ kiến trúc, hướng dẫn cài đặt trên máy sạch và hướng dẫn chạy kiểm thử.
  - Bổ sung `CONTRIBUTING.md` hướng dẫn đóng góp chuẩn mực cho cộng đồng FOSS.
  - Bổ sung `CHANGELOG.md` theo chuẩn Keep a Changelog.
