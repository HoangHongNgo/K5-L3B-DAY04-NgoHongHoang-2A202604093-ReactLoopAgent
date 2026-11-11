# Ghi chú phân tích · Day 04

Họ và tên: Ngô Hồng Hoàng
MSSV: 2A202604093

## 1. Case được chọn

- ID case: **H6**.
- Câu trả lời của agent: nêu GitHub Actions `operational`, mô tả incident `h02n9572mx9y` đã resolved, rồi kết luận các cập nhật không chỉ định nguyên nhân rõ ràng. Answer chỉ trỏ tới incident gộp `xr3myzj7ms51` mà không đọc nó; URL nguồn của incident đã đọc cũng không được dẫn trực tiếp.
- Điểm ở lần chạy 1: **60/100**. `grade.mechanical` ghi `tool_steps=1`, yêu cầu ít nhất 2 và chặn điểm ở 60.

## 2. Bằng chứng trong trace

Trace trong `eval_before.json` (rút gọn):

```text
step 1: get_status(github, actions)
step 1: get_incident_details(github, h02n9572mx9y)
  update: "Please refer to the combined summary in this related incident:
           https://www.githubstatus.com/incidents/xr3myzj7ms51"
step 2: final answer
  Không có get_incident_details(github, xr3myzj7ms51).
```

Nguyên nhân có thể: prompt chỉ yêu cầu dẫn nguồn chung; loop chấp nhận final answer ngay khi model trả `finish='stop'`, không kiểm tra yêu cầu "theo liên kết" hay URL incident đã quan sát. Vì chưa đọc incident gộp, kết luận về nguyên nhân thiếu bằng chứng.

## 3. Thay đổi đã thực hiện

- Sửa gì, ở đâu: trong `agent.py`, bổ sung hướng dẫn đọc incident được dẫn tới khi câu hỏi yêu cầu. Trước khi chấp nhận final answer, loop kiểm tra các liên kết incident cùng provider trong tool result đã được đọc hay chưa; nếu chưa, ghi `validation_missing_followup` và yêu cầu model gọi `get_incident_details` trong giới hạn `max_steps`. Loop cũng ghi `validation_missing_source` và yêu cầu sửa answer nếu đã đọc incident thành công nhưng không dẫn ít nhất một URL từ tool result. Tool lỗi không kích hoạt yêu cầu URL.
- Vì sao chọn thay đổi này: H6 có liên kết rõ ràng nhưng agent bỏ qua và thiếu URL nguồn. Kiểm tra ở loop giúp phát hiện final answer thiếu bước điều tra; kiểm tra URL hoàn thành contract nguồn trong `tests/test_validation.py`. URL chỉ chứng minh một nguồn đã được dẫn, không chứng minh mọi nhận định trong answer đều có căn cứ.
- Kiểm tra: `python -m unittest discover -s tests -v` qua **47/47** test, gồm test mới cho liên kết và ba test kiểm tra nguồn.
- Chạy thử riêng H6 sau sửa (`cp5_h6_probe.json`): trace có `validation_missing_followup` ở step 2, rồi `get_incident_details(github, xr3myzj7ms51)` ở step 3. `grade.mechanical` không còn vi phạm; điểm H6 là **75/100** trong lần thử này. Judge vẫn nêu giới hạn về diễn giải nguyên nhân và dữ liệu bị cắt. Đây chỉ là một case, chưa phải eval lần 2 toàn bộ.

## 4. So sánh hai lần chạy

`eval_after.json` đã chấm đủ 22/22 case. Cùng provider/model cho agent và judge (`openrouter`, `openai/gpt-4o-mini`), `max_steps=8` và dataset `core`. Sau lỗi HTTP 402, request OpenRouter được đặt `max_tokens=1024` cho cả agent và judge; lần trước không đặt giới hạn này. Vì thế hai lần chạy **khác nhau ở giới hạn output thực tế**, dù các tham số eval chính giữ nguyên. `config` của file sau ghi rõ `agent_max_tokens` và `judge_max_tokens`.

| Chỉ số | `eval_before.json` | `eval_after.json` |
|---|---:|---:|
| Case được chấm | 22/22 | 22/22 |
| Điểm trung bình ± độ lệch chuẩn giữa các case | 82,27 ± 13,46 | 83,18 ± 13,28 |
| Phương sai giữa các case (điểm²) | 181,20 | 176,24 |
| Case H6 được chọn | 60/100 | 80/100 (tăng 20) |
| Model calls: agent + judge | 50 + 22 = 72 | 53 + 22 = 75 |
| Token: agent + judge | 42.378 + 41.277 = 83.655 | 56.843 + 42.935 = 99.778 |
| Chi phí OpenRouter: agent + judge | $0,01023555 + $0,00759915 = $0,01783470 | $0,01277130 + $0,00785685 = $0,02062815 |

- Cải thiện quan sát được: H6 tăng 60 → 80. Trace ghi `validation_missing_followup` ở step 2 rồi đọc incident gộp ở step 3; không còn vi phạm yêu cầu tool calls ở hai model steps. Answer sau sửa nêu nguyên nhân là thay đổi cấu hình dịch vụ định tuyến sự kiện nội bộ và dẫn URL của hai incident. E2 tăng 75 → 100, H1 tăng 60 → 75, H5 tăng 75 → 100.
- Lỗi còn lại hoặc mới xuất hiện: judge H6 vẫn cho 80 và nhận xét answer chưa nêu rõ trạng thái hiện tại của GitHub Actions; nhận xét về nguyên nhân của incident gộp cũng chưa khớp với answer, nên cần đối chiếu thủ công. A5 giảm 75 → 55 và vẫn không có đủ bằng chứng để xác nhận danh sách sự cố năm 2025. A2 giảm 100 → 80, E4 giảm 100 → 75, H8 giảm 80 → 70. Các thay đổi điểm này không chứng minh giới hạn token gây ra chúng; đầu ra model và judge có thể dao động giữa các lần chạy.
- Không có case `unscored`, status `error` hay model response với `finish='length'` trong lượt sau. Output lớn nhất là 946 tokens ở agent và 169 tokens ở judge, dưới giới hạn 1.024. Lượt chạy HTTP 402 trước đó được giữ riêng trong `eval_after_failed_402.json` để đối chiếu sự cố hạ tầng.
- Hai chỉ số phân tán trên dùng công thức phương sai và độ lệch chuẩn của **toàn bộ 22 điểm case** (chia cho 22). Điểm trung bình tăng 0,91 và độ lệch chuẩn giảm 0,18. Đây không phải sai số của điểm trung bình hay độ dao động giữa các lần chạy độc lập.

## 5. Giới hạn

- Điểm judge là ước lượng; cùng model `openai/gpt-4o-mini` làm agent và judge có thể tạo thiên lệch. Điểm từng case dao động giữa các lần chạy: H6 sau sửa được 75 và 80 trong hai lần thử riêng.
- Snapshot và tool chỉ truy xuất một phần incident; tìm không thấy trong 50 incident gần nhất không chứng minh sự cố không tồn tại. Update có thể bị cắt, nên không thể khẳng định đã thấy toàn bộ nguyên nhân hoặc timeline.
- Một lần chạy mỗi phiên bản không chứng minh độ ổn định. Judge dùng cùng model với agent nên điểm có thể thiên lệch hoặc dao động. Hai phiên bản cũng khác `max_tokens` do điều kiện tín dụng của OpenRouter, nên chưa thể quy toàn bộ chênh lệch điểm và chi phí cho thay đổi trong `agent.py`.
