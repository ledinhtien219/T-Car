# THTV branch

Bản THTV tối ưu từ dự án Android hiện tại.

## Thay đổi chính
- Branding THTV; applicationId `com.thtv.app`.
- Foreground MediaBrowserService + MediaSession + WakeLock được giữ cho phát media nền.
- Bổ sung Picture-in-Picture khi rời ứng dụng lúc YouTube/IPTV đang phát.
- WebView YouTube/IPTV dùng renderer priority IMPORTANT để giảm khả năng bị Android thu hồi khi chuyển app.
- Giữ WebView timers hoạt động khi background audio được bật.
- Dọn build/cache/IDE artifacts khỏi bản source sạch.

Lưu ý: YouTube chạy qua WebView nên phát nền vẫn phụ thuộc phiên bản Android System WebView/YouTube. PiP là đường chạy ổn định hơn khi chuyển sang app khác.
