# Kiến trúc Elastic Cloud DB & Vector Search

Tài liệu này mô tả chi tiết cách hệ thống tích hợp và sử dụng **Elasticsearch** như một Vector Database để phục vụ tính năng RAG (Retrieval-Augmented Generation) trong việc tạo bài tập.

## 1. Tổng quan

Chúng tôi sử dụng **Elasticsearch (trên Elastic Cloud)** không chỉ để tìm kiếm văn bản thông thường (Full-text search) mà còn để lưu trữ và tìm kiếm vector (Dense Vector Search). Điều này cho phép tìm kiếm ngữ nghĩa (Semantic Search) kết hợp với từ khóa (Hybrid Search).

### Mục đích chính:
*   Lưu trữ ngân hàng bài tập, ví dụ mẫu từ sách giáo khoa và các nguồn tài liệu uy tín.
*   Cung cấp context (ngữ cảnh) cho LLM khi tạo bài tập mới, đảm bảo bài tập sát với chương trình học thực tế.

## 2. Thiết kế Schema (Index Mapping)

Index trong Elasticsearch được cấu hình để hỗ trợ lưu trữ vector embeddings cùng với metadata phong phú.

**Tên Index mặc định**: `search-math` (có thể config qua `ELASTICSEARCH_EXERCISE_INDEX`).

### Cấu trúc Document:

| Field Name | Type | Description |
| :--- | :--- | :--- |
| `text` | `text` | Nội dung chính của bài tập/ví dụ (được dùng cho BM25 search). |
| `vector` | `dense_vector` | Embeddings 1536 chiều (tương thích OpenAI `text-embedding-3-small` hoặc tương đương). Sử dụng metric `cosine`. |
| `metadata` | `object` | Chứa các thông tin bổ trợ để lọc. |
| `grade` | `keyword` | Lớp học (VD: "4", "5", "12"). Lưu ở top-level để query nhanh. |
| `subject` | `keyword` | Môn học (VD: "toán", "văn"). |
| `topic` | `text` | Chủ đề (VD: "Hình học", "Phân số"). |
| `difficulty`| `keyword` | Độ khó (VD: "Dễ", "Trung bình", "Khó"). |

**Mapping Configuration:**
```json
{
  "mappings": {
    "properties": {
      "text": { "type": "text" },
      "vector": {
        "type": "dense_vector",
        "dims": 1536,
        "index": true,
        "similarity": "cosine"
      },
      "metadata": { "type": "object" },
      // Các field keyword/text khác...
    }
  }
}
```

## 3. Cơ chế Tìm kiếm (Search Strategy)

Hệ thống sử dụng chiến lược **Hybrid Search** (Tìm kiếm lại) để đạt độ chính xác cao nhất, kết hợp giữa sức mạnh hiểu ngữ nghĩa của Vector và sự chính xác chi tiết của Keyword.

Logic được implement tại: `agent/services/vector_db/elasticsearch/elasticsearch_db.py` và `rag_node.py`.

### 3.1. Hybrid Search Logic

Truy vấn cuối cùng gửi xuống Elasticsearch là sự kết hợp của 2 phần:

1.  **Semantic Search (kNN - k-Nearest Neighbors)**:
    *   **Input**: Query Vector (được embed từ câu hỏi của người dùng).
    *   **Trọng số (Boost)**: `0.6` (Ưu tiên ngữ nghĩa).
    *   **Mục tiêu**: Tìm các bài tập có ý nghĩa tương đồng, ví dụ tìm "bài toán tính tổng" sẽ ra các bài về phép cộng dù không chứa từ "tính tổng".

2.  **Keyword Search (BM25 - Multi-match)**:
    *   **Input**: Query Text.
    *   **Fields**: `text`, `topic`.
    *   **Trọng số (Boost)**: `0.4`.
    *   **Mục tiêu**: Đảm bảo từ khóa quan trọng (VD: "phân số", "diện tích") xuất hiện trong kết quả.

### 3.2. Cơ chế Lọc (Filters)

Trước khi tìm kiếm, hệ thống áp dụng các bộ lọc cứng (Hard Filters) để đảm bảo kết quả trả về đúng phạm vi giáo dục yêu cầu.

*   **Grade Filter**: Bắt buộc. Chỉ tìm dữ liệu của khối lớp tương ứng (VD: Lớp 4).
*   **Subject Filter**: Bắt buộc. Chỉ tìm dữ liệu của môn học tương ứng.
*   **Topic/Difficulty Filter**: Nếu người dùng chỉ định cụ thể.

### 3.3. Quy trình thực thi tại RAG Node

1.  **Build Query**: Dựa vào yêu cầu người dùng (VD: "Toán lớp 4 bài phân số nâng cao"), node tạo ra câu query text: *"Bài tập Toán lớp 4 về chủ đề phân số mức độ nâng cao"*.
2.  **Embedding**: Gửi query text qua Embedding Service để lấy vector.
3.  **Execute Hybrid Search**: Gọi `vector_db.hybrid_search()` với vector và text.
4.  **Ranking & Selection**:
    *   Elasticsearch trả về danh sách ứng viên (candidate pool) có điểm số (score) cao nhất.
    *   Hệ thống lấy Top-K (VD: 5) kết quả tốt nhất.
    *   *Logic phụ*: Nếu tìm thấy quá nhiều kết quả tốt (nhiều hơn Top-K), hệ thống có thể random trong nhóm tốt nhất để tăng tính đa dạng cho bài tập sinh ra.

## 4. Cấu hình & Quản lý Kết nối

*   **Quản lý**: Class `VectorDBManager` (Singleton) quản lý vòng đời kết nối.
*   **Driver**: Sử dụng thư viện `elasticsearch[async]` (Python).
*   **Authentication**: Hỗ trợ Basic Auth (Username/Password) hoặc API Key.
*   **Connection**: Kết nối Async để đảm bảo hiệu năng cao trong môi trường IO-bound.

## 5. Mở rộng trong tương lai

*   **Re-ranking**: Có thể thêm bước Re-ranker model (như Cohere Rerank) sau bước Hybrid Search để sắp xếp lại kết quả chính xác hơn nữa.
*   **Metadata Filtering nâng cao**: Thêm các filter như "Dạng bài" (Trắc nghiệm/Tự luận) hoặc "Nguồn" (Sách GK/Đề thi).
