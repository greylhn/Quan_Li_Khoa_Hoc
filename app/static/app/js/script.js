// Khởi tạo các Icon Lucide
document.addEventListener('DOMContentLoaded', () => {
  lucide.createIcons();
});

// 1. Chức năng Xử lý Ẩn / Hiện Mật khẩu
const passwordInput = document.getElementById('password');
const togglePasswordBtn = document.getElementById('togglePasswordBtn');
const eyeIcon = document.getElementById('eyeIcon');

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
  lucide.createIcons();
});

// 2. Chức năng Validate & Submit Form Đăng nhập
const loginForm = document.getElementById('loginForm');

loginForm.addEventListener('submit', (e) => {
  e.preventDefault();

  const email = document.getElementById('email').value.trim();
  const password = passwordInput.value.trim();
  const remember = document.getElementById('remember').checked;

  // Validation đơn giản
  if (!email || !password) {
    alert('Vui lòng điền đầy đủ thông tin đăng nhập!');
    return;
  }

  // Giả lập gửi thông tin lên backend/API
  // console.log('Dữ liệu Đăng nhập:', {
  //   account: email,
  //   password: password,
  //   rememberMe: remember
  // });

  // alert(`Đang tiến hành đăng nhập cho tài khoản: ${email}`);
});