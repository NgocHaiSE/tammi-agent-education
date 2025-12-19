# Hướng dẫn sử dụng Qwen2.5-Math trong dự án

## Giới thiệu

**Qwen2.5-Math** là model chuyên biệt cho bài toán toán học từ Alibaba Cloud, được tối ưu hóa để giải quyết các bài toán toán học bằng tiếng Anh và tiếng Trung.

### Tính năng nổi bật:
- ✅ Hỗ trợ Chain-of-Thought (CoT) reasoning
- ✅ Hỗ trợ Tool-Integrated Reasoning (TIR) với Python interpreter
- ✅ Hiệu suất cao trên các benchmark toán học (MATH, GSM8K, GaoKao)
- ✅ Hỗ trợ cả tiếng Anh và tiếng Trung
- ✅ Model nhẹ (7B parameters) có thể chạy local với Ollama

### Phiên bản:
- **qwen2.5-math:7b** - Base model (dùng cho few-shot, fine-tuning)
- **qwen2.5-math:7b-instruct** - Instruction-tuned model (khuyên dùng cho chat/generation)

---

## Bước 1: Cài đặt Qwen2.5-Math với Ollama

### 1.1. Kiểm tra Ollama đã cài đặt chưa
```powershell
ollama --version
```

Nếu chưa có, tải Ollama tại: https://ollama.ai/download

### 1.2. Pull model Qwen2.5-Math

Chọn một trong hai phiên bản:

**Phiên bản Instruct (khuyên dùng):**
```powershell
ollama pull qwen2.5-math:7b-instruct
```

**Phiên bản Base:**
```powershell
ollama pull qwen2.5-math:7b
```

### 1.3. Kiểm tra model đã được cài đặt
```powershell
ollama list
```

Bạn sẽ thấy `qwen2.5-math:7b-instruct` hoặc `qwen2.5-math:7b` trong danh sách.

### 1.4. Test model
```powershell
ollama run qwen2.5-math:7b-instruct
```

Thử một câu hỏi toán:
```
>>> Giải phương trình: 2x + 5 = 13
```

---

## Bước 2: Cấu hình trong dự án

Model đã được cấu hình sẵn trong dự án:

### 2.1. File cấu hình LLM (`agent/config/llm_config.json`)

```json
{
  "ollama": {
    "deployments": [
      {
        "name": "qwen25-math-7b-instruct",
        "model": "qwen2.5-math:7b-instruct",
        "base_url_env": "OLLAMA_BASE_URL",
        "api_key": "ollama"
      },
      {
        "name": "qwen25-math-7b",
        "model": "qwen2.5-math:7b",
        "base_url_env": "OLLAMA_BASE_URL",
        "api_key": "ollama"
      }
    ]
  }
}
```

### 2.2. File cấu hình version (`agent/config/versions/v1.yaml`)

Model mặc định đã được đặt là Qwen2.5-Math:

```yaml
llm:
  default_provider: "ollama"
  default_model:
    name: "qwen25-math-7b-instruct"
    provider: "ollama"
  default_backup_models:
    - name: "qwen25-math-7b-instruct"
      provider: "ollama"
    - name: "qwen25-math-7b"
      provider: "ollama"
```

---

## Bước 3: Cấu hình biến môi trường

Đảm bảo file `.env` hoặc `env-config.secret.yaml` có các biến sau:

```bash
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=qwen2.5-math:7b-instruct

# LLM Configuration
LLM_PROVIDER=ollama
DEFAULT_LLM_VERSION=v1
```

---

## Bước 4: Chạy dự án

### 4.1. Khởi động Ollama server (nếu chưa chạy)
```powershell
ollama serve
```

### 4.2. Chạy agent
```powershell
python -m agent.entrypoint.run
```

---

## Bước 5: Sử dụng trong code

### 5.1. Tạo bài tập toán với RAG Node

File `agent/graph/node_services/create_exercise/subgraph/nodes/rag_node.py` đã tự động sử dụng model được cấu hình:

```python
# Model được inject tự động từ graph builder
async def run(self, state: CreateExerciseState) -> Dict[str, Any]:
    # LLM đã được cấu hình là qwen2.5-math:7b-instruct
    response = await self.llm.ainvoke(prompt)
    # ...
```

### 5.2. Sử dụng trực tiếp với LLM Service

```python
from agent.llm_service.llm_config_service import get_llm_service

# Get LLM service với version v1 (sử dụng qwen2.5-math)
llm_service = get_llm_service(version="v1")

# Tạo client với model math
llm_client = llm_service.get_client2(
    "ollama:qwen25-math-7b-instruct",
    temperature=0.1,
    max_tokens=1024
)

# Invoke
response = await llm_client.ainvoke("Giải phương trình: x^2 - 5x + 6 = 0")
print(response.content)
```

---

## Bước 6: Prompt Engineering cho Qwen2.5-Math

### 6.1. Chain-of-Thought (CoT) - Khuyên dùng

```python
messages = [
    {
        "role": "system", 
        "content": "Please reason step by step, and put your final answer within \\boxed{}."
    },
    {
        "role": "user", 
        "content": "Tìm nghiệm của phương trình: 2x + 5 = 13"
    }
]
```

### 6.2. Tool-Integrated Reasoning (TIR) - Advanced

```python
messages = [
    {
        "role": "system", 
        "content": "Please integrate natural language reasoning with programs to solve the problem above, and put your final answer within \\boxed{}."
    },
    {
        "role": "user", 
        "content": "Tính giá trị của biểu thức: sqrt(144) + 2^3"
    }
]
```

### 6.3. Prompt format được tối ưu cho Qwen2-Math trong RAG Node

Prompt đã được thiết kế theo best practices của Qwen2-Math:

```python
prompt = f"""Bạn là giáo viên Toán giỏi ở Việt Nam với chuyên môn cao. 
Nhiệm vụ của bạn là tạo bài tập chất lượng cao cho học sinh.

BẮT BUỘC: Toàn bộ câu hỏi và đáp án phải viết BẰNG TIẾNG VIỆT.

## Nhiệm vụ:
Dựa vào các ví dụ bài tập tham khảo ở trên (nếu có), hãy tạo 5 bài tập Trắc nghiệm Toán 
MỚI và KHÁC BIỆT cho học sinh lớp 8 về chủ đề 'Phương trình bậc nhất'.

## Yêu cầu khi tạo bài tập:

1. **Ngôn ngữ**: Câu hỏi và đáp án phải HOÀN TOÀN BẰNG TIẾNG VIỆT
2. **Số lượng**: Tạo đúng 5 bài tập
3. **Độ khó**: Phù hợp với trình độ học sinh lớp 8
4. **Dạng bài**: Trắc nghiệm
5. **Nội dung**: Liên quan trực tiếp đến chủ đề 'Phương trình bậc nhất'
6. **Tính độc đáo**: 
   - KHÔNG sao chép trực tiếp từ ví dụ tham khảo
   - Tạo nội dung mới với số liệu và tình huống khác biệt
7. **Chất lượng**:
   - Câu hỏi phải rõ ràng, dễ hiểu
   - Đáp án phải chính xác và đầy đủ
   - Nếu là Toán, hãy reasoning từng bước để đảm bảo đáp án đúng

## Format đầu ra (JSON Array):

```json
[
  {
    "question": "Câu hỏi tiếng Việt số 1",
    "answer": "Đáp án tiếng Việt số 1",
    "difficulty": "Dễ"
  },
  {
    "question": "Câu hỏi tiếng Việt số 2",
    "answer": "Đáp án tiếng Việt số 2",
    "difficulty": "Trung bình"
  }
]
```

Bây giờ hãy bắt đầu tạo 5 bài tập. Chỉ trả về JSON array:"""
```

**Lý do thiết kế prompt này:**
- ✅ Clear role definition (giáo viên chuyên môn cao)
- ✅ Explicit language requirement ở đầu
- ✅ Structured requirements với numbering rõ ràng
- ✅ Khuyến khích reasoning cho bài toán Toán
- ✅ Format output rõ ràng với ví dụ cụ thể
- ✅ Không quá dài, tránh làm model bị "confused"

---

## Lưu ý quan trọng

### ⚠️ Giới hạn của Qwen2.5-Math

1. **Chuyên biệt cho toán học**: Model này được tối ưu hóa riêng cho bài toán toán học. Không nên dùng cho các tác vụ khác như chat thường, dịch thuật, hay viết văn.

2. **Ngôn ngữ**: Model hỗ trợ tốt tiếng Anh và tiếng Trung. Với tiếng Việt có thể cần prompt engineering cẩn thận hơn.

3. **Format đầu ra**: Model được train để output trong format có `\boxed{}` cho đáp án cuối cùng.

### 💡 Tips sử dụng

1. **Luôn dùng system message**: Thêm system message để hướng dẫn model reasoning step-by-step

2. **Kiểm tra format output**: Sử dụng `_parse_llm_response()` để parse JSON một cách robust

3. **Temperature thấp**: Dùng temperature 0.1-0.3 cho bài toán toán học để output stable

4. **Fallback models**: Đã cấu hình backup models trong trường hợp primary model fail

---

## Tài liệu tham khảo

- **Hugging Face**: https://huggingface.co/Qwen/Qwen2.5-Math-7B
- **GitHub**: https://github.com/QwenLM/Qwen2.5-Math
- **Blog**: https://qwenlm.github.io/blog/qwen2.5-math/
- **Ollama**: https://ollama.ai/library/qwen2.5-math

---

## Troubleshooting

### Lỗi: "model not found"
```powershell
# Pull lại model
ollama pull qwen2.5-math:7b-instruct
```

### Lỗi: "connection refused"
```powershell
# Kiểm tra Ollama server
ollama serve

# Kiểm tra port
netstat -an | findstr 11434
```

### Model chậm/hết RAM
```powershell
# Dùng phiên bản nhẹ hơn (1.5B)
ollama pull qwen2.5-math:1.5b-instruct

# Hoặc cấu hình quantization
ollama pull qwen2.5-math:7b-instruct-q4_0
```

### Output không đúng format JSON
- Kiểm tra prompt có yêu cầu rõ ràng format JSON
- Sử dụng fallback parser trong `_fallback_parse()`
- Tăng max_tokens nếu output bị cắt

---

## Performance Benchmarks

Model Qwen2.5-Math-7B-Instruct đạt:
- **MATH**: 83.6 (CoT) / 85.3 (TIR)
- **GSM8K**: 91.6
- **GaoKao Math**: 59.3

Đây là performance rất tốt cho một model 7B có thể chạy local!

---

## Next Steps

1. ✅ Pull model từ Ollama
2. ✅ Kiểm tra cấu hình đã được apply
3. ✅ Test với một vài câu hỏi toán đơn giản
4. ✅ Chạy dự án và kiểm tra RAG node
5. ⭐ Fine-tune prompt để tối ưu cho tiếng Việt
6. ⭐ Thử nghiệm với TIR mode nếu cần tính toán phức tạp

Chúc bạn sử dụng thành công! 🚀
