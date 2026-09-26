# T-Car

Android Auto YouTube/IPTV.

## Bản nguồn dùng để build

Workflow chỉ chấp nhận file đã test chạy ổn:

- Đường dẫn: `source/youtubepro_background_final.zip`
- SHA-256: `824899f63343f1e2da6d84b491ec5b4fd6fb5087ffbfde9384c932a658b98f7f`

Nếu checksum không đúng, GitHub Actions sẽ dừng trước khi build.

## Build APK

1. Upload `youtubepro_background_final.zip` vào thư mục `source/` và giữ đúng tên.
2. Push/commit lên nhánh `main`.
3. Workflow **Build T-Car APK** tự chạy.
4. APK được xuất thành `T-Car.apk` trong **Actions > Artifacts** và đồng thời tạo **Release**.

Source build giữ nguyên bản background-playback đã xác nhận chạy ổn; workflow không sửa logic YouTube/IPTV.
