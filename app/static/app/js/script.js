// Khởi tạo các Icon Lucide
document.addEventListener('DOMContentLoaded', () => {
  lucide.createIcons();
});

// Chức năng Xử lý Ẩn / Hiện Mật khẩu
const passwordInput = document.getElementById('password');
const togglePasswordBtn = document.getElementById('togglePasswordBtn');

if (togglePasswordBtn && passwordInput) {
  togglePasswordBtn.addEventListener('click', () => {
    const isPassword = passwordInput.type === 'password';

    passwordInput.type = isPassword ? 'text' : 'password';
    togglePasswordBtn.setAttribute(
      'aria-label',
      isPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'
    );
    togglePasswordBtn.innerHTML = isPassword
      ? '<i data-lucide="eye-off" id="eyeIcon"></i>'
      : '<i data-lucide="eye" id="eyeIcon"></i>';

    if (window.lucide) {
      lucide.createIcons();
    }
  });
}
  // Giả lập gửi thông tin lên backend/API
  // console.log('Dữ liệu Đăng nhập:', {
  //   account: email,
  //   password: password,
  //   rememberMe: remember
  // });

  // alert(`Đang tiến hành đăng nhập cho tài khoản: ${email}`);