# CLAUDE.md

## Chọn subagent cho skill/task

Đây là quyền mặc định đã được cấp trước, không phải giới hạn cần hỏi lại mỗi lần:

- Có toàn quyền tự chọn và spawn subagent phù hợp khi thực thi skill hoặc task trong project này, không cần xác nhận trước.
- Chọn agent theo mô tả khớp nhất với việc cần làm: `Explore` cho tìm kiếm/khảo sát rộng, `Plan` cho thiết kế implementation, `general-purpose` cho task đa bước hoặc cần tách khỏi context chính, `claude-code-guide` cho câu hỏi về Claude Code/SDK/API.
- Không spawn subagent cho việc nhỏ mà làm trực tiếp  (đọc/sửa 1-2 file) — subagent chỉ đáng dùng khi việc đủ lớn/độc lập để bù chi phí cold-start.
- Khi một skill tự gợi ý dùng subagent để verify hoặc mở rộng phạm vi (vd: research trước khi build), được phép làm theo mà không cần hỏi thêm.
- Ngoại lệ: task rủi ro cao (destructive, ảnh hưởng hệ thống/tài khoản ngoài project) vẫn phải xác nhận với user trước — quyền tự chọn agent không thay thế nguyên tắc an toàn hành động.

## Chọn model cho workflow và subagent

| model | cost | intelligence | taste |
|---|---|---|---|
| gpt-5.5 | 9 | 8 | 5 |
| sonnet-5 | 5 | 5 | 7 |
| opus-4.8 | 4 | 7 | 8 |
| fable-5 | 2 | 9 | 9 |

Cách áp dụng:

- Đây là mặc định, không phải giới hạn. Có quyền ghi đè sẵn: nếu output của model rẻ hơn không đạt chuẩn, rerun/redo bằng model mạnh hơn mà không cần hỏi lại. Đánh giá theo chất lượng output, không phải theo giá — đội chi phí lên vẫn rẻ hơn là ship ra sản phẩm dở.
- Cost chỉ là yếu tố phân xử cuối cùng; khi các trục xung đột với bất kỳ thứ gì sẽ ship ra: intelligence > taste > cost.
- Việc bulk/cơ học (implementation theo spec rõ ràng, phân tích dữ liệu, migration): dùng gpt-5.5 — gần như miễn phí.
- Bất kỳ thứ gì user-facing (UI, copy, thiết kế API) cần taste ≥ 7.
- Review plan/implementation: fable-5 hoặc opus-4.8, có thể thêm gpt-5.5 như một góc nhìn độc lập.
- Không bao giờ dùng Haiku.
- Cơ chế: gpt-5.5 chỉ gọi được qua Codex CLI (`codex exec` / `codex review`), đã cài sẵn trong project này. Project này CHƯA có skill `codex-implementation`/`codex-review`/`codex-computer-use` — khi cần gọi gpt-5.5 cho việc gì đó (investigation, data analysis...), chạy trực tiếp `codex exec -s read-only "<prompt>"` qua Bash/PowerShell với prompt tự chứa đủ ngữ cảnh.
- Claude models (sonnet-5, opus-4.8, fable-5) chạy qua tham số `model` của Agent tool.
