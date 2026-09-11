# Hướng dẫn đóng góp (Contributing Guidelines)

Cảm ơn bạn đã quan tâm đến dự án mã nguồn mở **tro.**! Chúng tôi luôn hoan nghênh các đóng góp từ cộng đồng, từ việc sửa lỗi nhỏ, cải thiện tài liệu đến việc đề xuất các tính năng mới.

---

## 1. Quy trình làm việc với Git & GitHub

Dự án áp dụng mô hình phân nhánh **Fork & Feature Branch**:

1. **Fork repository** về tài khoản GitHub của bạn và clone về máy cục bộ:
   ```bash
   git clone https://github.com/<your-username>/tro.git
   cd tro
   ```
2. **Đồng bộ với upstream**:
   ```bash
   git remote add upstream https://github.com/tuanhung075021/tro.git
   git fetch upstream
   ```
3. **Tạo nhánh mới** cho thay đổi của bạn từ `main`:
   ```bash
   git checkout main
   git pull upstream main
   git checkout -b feature/ten-tinh-nang
   # hoặc: git checkout -b fix/mo-ta-loi
   ```

---

## 2. Tiêu chuẩn viết thông điệp Commit

Kho mã nguồn áp dụng chuẩn [Conventional Commits](https://www.conventionalcommits.org/) để duy trì lịch sử rõ ràng và hỗ trợ phát hành phiên bản tự động:

```text
<type>(<scope>): <mô tả ngắn gọn bằng thể mệnh lệnh>
```

**Các tiền tố thường dùng:**
- `feat`: Thêm tính năng mới (ví dụ: `feat(core): implement progressive tariff calculation`)
- `fix`: Sửa lỗi (ví dụ: `fix(core): handle meter rollover logic`)
- `docs`: Cập nhật tài liệu (ví dụ: `docs(readme): add installation guide`)
- `test`: Thêm hoặc cập nhật test (ví dụ: `test(calc): add test case for 1.25 quota`)
- `refactor`: Tái cấu trúc mã nguồn không làm thay đổi hành vi
- `chore`: Tác vụ bảo trì, cấu hình dự án

---

## 3. Tiêu chuẩn mã nguồn & Bản quyền (License Compliance)

Dự án phát hành theo giấy phép **MIT**. Nhằm đảm bảo tính minh bạch pháp lý của phần mềm nguồn mở, mỗi tệp mã nguồn mới (`.py`, `.ts`, `.tsx`, `.js`, `.css`, `.sh`) cần có phần khai báo bản quyền chuẩn (SPDX Header) ở đầu tệp:

- **Python / Shell**:
  ```python
  # Copyright (c) 2026 tro. Contributors
  # SPDX-License-Identifier: MIT
  ```
- **JavaScript / TypeScript / CSS**:
  ```javascript
  /*
   * Copyright (c) 2026 tro. Contributors
   * SPDX-License-Identifier: MIT
   */
  ```

Kho mã nguồn cung cấp sẵn công cụ hỗ trợ kiểm tra và định dạng tự động:
```bash
# Kiểm tra nhanh tính hợp lệ trước khi tạo Pull Request
python scripts/add_license_headers.py --check

# Tự động chèn header nếu còn thiếu
python scripts/add_license_headers.py
```
*(Mẹo: Bạn có thể tích hợp lệnh trên vào Git pre-commit hook để tự động kiểm tra trước mỗi commit).*

---

## 4. Kiểm thử tự động (Testing)

Trước khi gửi đóng góp, vui lòng đảm bảo tất cả bài kiểm thử đều vượt qua thành công:
```bash
python -m unittest discover -s tests -p "test_*.py"
```
Khi triển khai logic tính toán mới, vui lòng bổ sung các ca kiểm thử tương ứng vào thư mục `tests/`.

---

## 5. Quy trình gửi Pull Request (PR)

1. Đẩy nhánh của bạn lên fork:
   ```bash
   git push origin feature/ten-tinh-nang
   ```
2. Mở Pull Request từ nhánh của bạn vào nhánh `main` của repository gốc.
3. Mô tả rõ mục đích của thay đổi, các vấn đề liên quan (nếu có, ví dụ `Closes #12`), và xác nhận đã vượt qua các bước kiểm thử.

---

## 6. Báo lỗi & Góp ý (Issue Tracker)

Dự án sử dụng **GitHub Issues** để tiếp nhận phản hồi:
- **Báo lỗi (Bug Report)**: Vui lòng mô tả chi tiết lỗi gặp phải, các bước tái hiện, kết quả thực tế và kết quả mong đợi.
- **Đề xuất tính năng (Feature Request)**: Chia sẻ nhu cầu thực tế và giải pháp bạn đề xuất.
