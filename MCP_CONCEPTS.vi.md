# MCP là gì? Tại sao chúng ta cần nó? 🤖🔌

Chào mừng bạn! Nếu bạn mới làm quen với AI hoặc dự án này, tài liệu này sẽ giải thích những khái niệm cơ bản một cách dễ hiểu nhất.

## 1. MCP là cái gì? (Hiểu đơn giản)

**MCP (Model Context Protocol)** giống như một cái **"cổng USB"** cho trí tuệ nhân tạo (AI).

Hãy tưởng tượng:

- **AI (như ChatGPT, Claude, Gemini)** là một bộ não cực kỳ thông minh, nhưng nó bị "nhốt" trong máy chủ của Google/OpenAI. Nó không biết gì về dữ liệu nội bộ, file Excel, hay cơ sở dữ liệu của công ty bạn.
- **Dữ liệu của bạn (Oracle Database)** là kho báu chứa thông tin quan trọng.

👉 **MCP Server** chính là **người phiên dịch** đứng ở giữa. Nó giúp AI "kết nối" được với dữ liệu của bạn một cách an toàn để đọc, tìm kiếm và phân tích dữ liệu giúp bạn.

## 2. Server này dùng để làm gì?

Dự án này (`mcp-oracle-server`) là một công cụ giúp AI "nói chuyện" được với hệ quản trị cơ sở dữ liệu **Oracle** của chúng ta.

Thay vì bạn phải tự viết câu lệnh SQL phức tạp, bạn có thể ra lệnh cho AI bằng tiếng Việt:

> _"Tìm cho tôi tất cả hóa đơn chưa thanh toán của khách hàng tên Tuấn trong tháng này."_

Khi đó, quy trình sẽ diễn ra như sau:

1. AI nhận câu lệnh của bạn.
2. AI nhờ **MCP Server** này kiểm tra xem bảng "Hóa đơn" nằm ở đâu.
3. AI nhờ **MCP Server** chạy lệnh tìm kiếm dữ liệu an toàn.
4. AI tổng hợp kết quả và trả lời bạn.

## 3. Nó có an toàn không? 🛡️

**Rất an toàn.** Chúng tôi đã thiết lập nhiều lớp bảo vệ:

- **Chỉ đọc (Read-only)**: Mặc định AI thường chỉ được đọc dữ liệu để trả lời câu hỏi.
- **Hỏi ý kiến**: Nếu AI muốn sửa đổi dữ liệu (như thêm mới, xóa), nó **bắt buộc** phải hỏi ý kiến bạn và chờ bạn bấm "Chấp nhận" thì mới được làm.
- **Chặn lệnh nguy hiểm**: Các lệnh như "Xóa toàn bộ dữ liệu" (DROP DATABASE) bị cấm hoàn toàn.

## 4. Tôi cần làm gì?

Bạn chỉ cần làm theo hướng dẫn trong file **[README.vi.md](README.vi.md)** để cài đặt một lần duy nhất. Sau đó, bạn có thể mở các công cụ AI (như Cursor, Windsurf, Claude Desktop) và bắt đầu làm việc với dữ liệu nhanh hơn gấp 10 lần!

---

[Quay lại trang chính](README.vi.md)
