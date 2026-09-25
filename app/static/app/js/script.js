// Khởi tạo các Icon Lucide
document.addEventListener('DOMContentLoaded', () => {
  if (typeof lucide !== 'undefined') {
    lucide.createIcons();
  }
});

// 1. Chức năng Xử lý Ẩn / Hiện Mật khẩu (Trang Đăng nhập / Đăng ký)
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
    
    // Re-render icon
    if (typeof lucide !== 'undefined') {
      lucide.createIcons();
    }
  });
}

// 2. Chức năng Validate Form Đăng nhập
const loginForm = document.getElementById('loginForm');

if (loginForm) {
  loginForm.addEventListener('submit', (e) => {
    const emailInput = document.getElementById('email');
    const email = emailInput ? emailInput.value.trim() : '';
    const password = passwordInput ? passwordInput.value.trim() : '';

    if (!email || !password) {
      e.preventDefault();
      alert('Vui lòng điền đầy đủ thông tin đăng nhập!');
      return;
    }
  });
}