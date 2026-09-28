# T-Car

Android Auto YouTube/IPTV.

## Source build

GitHub Actions giải nén source từ:

- `source/TCAR.zip`
- áp dụng toàn bộ `patches/*.patch` và `patches/*.py`
- build một APK duy nhất của T-Car.

APK này khai báo đồng thời hai bề mặt Android Auto:

- **T-Car** — `CarAppService` / navigation-template surface.
- **T-Car Media** — `MediaBrowserService` với label riêng `T-Car Media`.

Workflow kiểm tra cả source sau patch và manifest đã compile trong APK; build sẽ fail nếu mất một trong hai entry Android Auto.

## Cài APK và hiện T-Car Media trong Android Auto

Với APK sideload (không cài từ nguồn tin cậy như Google Play), Android Auto yêu cầu bật **Unknown sources** cho media app.

1. Mở **Android Auto > Cài đặt**.
2. Vào phần **Giới thiệu / Version**, chạm thông tin phiên bản 10 lần để bật Developer mode.
3. Mở menu **Developer settings** và bật **Unknown sources / Nguồn không xác định**.
4. Cài hoặc cập nhật APK T-Car.
5. Ngắt/kết nối lại Android Auto.
6. Vào **Android Auto > Tùy chỉnh trình khởi chạy**. Danh sách dự kiến có cả **T-Car** và **T-Car Media**.

Nếu **T-Car** xuất hiện nhưng **T-Car Media** không xuất hiện trên một bản sideload, hãy kiểm tra mục **Unknown sources** trước: T-Car Media được Android Auto phát hiện theo luồng media app riêng.

## Lấy APK

Mỗi build thành công được upload tại **Actions > Build T-Car APK > Artifacts** và, khi signing secrets sẵn sàng, được publish trong **Releases**.
