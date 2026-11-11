# CP4 · Eval lần 1

Chạy `python evals/run_evals.py --output eval_before.json` với OpenRouter, model `openai/gpt-4o-mini` cho cả agent và judge, `max_steps=8`. Kết quả trong `eval_before.json`: **22/22 case được chấm, 82,27/100**, không có case `unscored`.

## Danh sách lỗi cần phân tích ở CP5

- **H1 — 60 điểm:** Câu hỏi yêu cầu theo liên kết từ incident GitHub `h02n9572mx9y` tới `xr3myzj7ms51`. Trace chỉ có `get_incident_details` cho `h02n9572mx9y` và incident Cloudflare `yaa0witbl2me`, đều ở model step 1; không đọc incident liên kết. `grade.mechanical` ghi vi phạm yêu cầu tool ở ít nhất 2 model steps và chặn điểm ở 60.
- **H6 — 60 điểm:** Cùng lỗi không theo liên kết `xr3myzj7ms51` sau khi đọc `h02n9572mx9y`. Agent kết luận nguyên nhân không rõ dù phần incident gộp có thể trả lời; trace chỉ có 2 tool calls ở model step 1. `grade.mechanical` chặn điểm ở 60.
- **H7 — 65 điểm:** Tool Cloudflare Spectrum trả `TimeoutError`, nhưng câu trả lời vẫn kết luận Spectrum `operational`. Đây là khẳng định không có bằng chứng, trái với yêu cầu phải báo thiếu dữ liệu.
- **A5 — 75 điểm:** Câu trả lời nói không có incident GitHub Actions năm 2025 trong dữ liệu đã xem, dễ bị hiểu là không có sự cố trong cả năm. Tool chỉ tìm trong tối đa 50 incident gần nhất; không thể kết luận danh sách năm 2025 đầy đủ.
- **E1 — 65 điểm, cần xem lại điểm judge:** Answer thực tế mở đầu bằng câu GitHub Actions đang hoạt động bình thường và không có sự cố hiện tại, dù `grade.reason` nói thiếu kết luận này. Trace chỉ có một `get_status`; answer dẫn trang GitHub Status chung, chưa dẫn URL của incident cụ thể.

Các điểm trên là ước lượng của LLM judge. `completed` chỉ có nghĩa agent dừng bình thường; cần đối chiếu answer và trace với `expected`, như H7 cho thấy. File eval đã được kiểm tra không chứa API key.
