# T-Car

Android Auto YouTube/IPTV.

## Source đã test OK

GitHub Actions chỉ build gói source đã đối chiếu với bản chạy ổn:

- File: `source/T-Car_source_ok.zip`
- SHA-256: `6dceee3907a924923ae7521190ece51aecd3a2d2138f2e7abbc4168a02512891`

Gói này là source-only từ bản `youtubepro_background_final`: 116 file runtime/build đã được so sánh và không có khác biệt nội dung. Chỉ bỏ cache/build output/local.properties không cần cho CI.

## Lấy APK

Khi `source/T-Car_source_ok.zip` được commit lên `main`, workflow **Build T-Car APK** tự chạy. APK nằm trong **Actions > Artifacts > T-Car-APK**.
