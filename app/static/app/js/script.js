// Khởi tạo các Icon Lucide
document.addEventListener('DOMContentLoaded', () => {
  lucide.createIcons();
});

// Chức năng Xử lý Ẩn / Hiện Mật khẩu
const passwordInput = document.getElementById('password');
const togglePasswordBtn = document.getElementById('togglePasswordBtn');
const eyeIcon = document.getElementById('eyeIcon');

if (togglePasswordBtn && passwordInput && eyeIcon) {
  togglePasswordBtn.addEventListener('click', () => {
    const isPassword = passwordInput.getAttribute('type') === 'password';
    
    if (isPassword) {
      passwordInput.setAttribute('type', 'text');
      eyeIcon.setAttribute('data-lucide', 'eye-off');
    } else {
      passwordInput.setAttribute('type', 'password');
      eyeIcon.setAttribute('data-lucide', 'eye');
    }
    
    lucide.createIcons();
  });
}
  // Giả lập gửi thông tin lên backend/API
  // console.log('Dữ liệu Đăng nhập:', {
  //   account: email,
  //   password: password,
  //   rememberMe: remember
  // });

  // alert(`Đang tiến hành đăng nhập cho tài khoản: ${email}`);