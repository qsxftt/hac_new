// Скрипт для установки PWA
let deferredPrompt;
let installButton;

// Регистрация Service Worker
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/static/service-worker.js')
      .then((registration) => {
        console.log('[PWA] Service Worker registered:', registration.scope);
        
        // Проверка обновлений каждые 5 минут
        setInterval(() => {
          registration.update();
        }, 5 * 60 * 1000);
      })
      .catch((error) => {
        console.error('[PWA] Service Worker registration failed:', error);
      });
  });
}

// Обработка события beforeinstallprompt
window.addEventListener('beforeinstallprompt', (e) => {
  console.log('[PWA] beforeinstallprompt event fired');
  
  // Предотвращаем автоматический показ браузерного промпта
  e.preventDefault();
  deferredPrompt = e;
  
  // Показываем кнопку установки
  showInstallButton();
});

// Показать кнопку установки приложения
function showInstallButton() {
  // Ищем или создаем кнопку установки
  installButton = document.getElementById('pwa-install-button');
  
  if (!installButton) {
    // Создаем плавающую кнопку установки
    installButton = document.createElement('button');
    installButton.id = 'pwa-install-button';
    installButton.className = 'pwa-install-btn';
    installButton.innerHTML = `
      <i class="fas fa-download"></i>
      <span>Установить приложение</span>
    `;
    document.body.appendChild(installButton);
    
    // Добавляем стили
    const style = document.createElement('style');
    style.textContent = `
      .pwa-install-btn {
        position: fixed;
        bottom: 20px;
        right: 20px;
        z-index: 9999;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 15px 25px;
        border-radius: 50px;
        font-size: 16px;
        font-weight: 600;
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 10px;
        transition: all 0.3s ease;
        animation: slideInUp 0.5s ease;
      }
      
      .pwa-install-btn:hover {
        transform: translateY(-3px);
        box-shadow: 0 15px 40px rgba(102, 126, 234, 0.6);
      }
      
      .pwa-install-btn i {
        font-size: 20px;
      }
      
      @keyframes slideInUp {
        from {
          transform: translateY(100px);
          opacity: 0;
        }
        to {
          transform: translateY(0);
          opacity: 1;
        }
      }
      
      @media (max-width: 768px) {
        .pwa-install-btn {
          bottom: 80px;
          right: 10px;
          padding: 12px 20px;
          font-size: 14px;
        }
      }
    `;
    document.head.appendChild(style);
  }
  
  installButton.style.display = 'flex';
  installButton.addEventListener('click', installApp);
}

// Установка PWA
async function installApp() {
  if (!deferredPrompt) {
    console.log('[PWA] Install prompt not available');
    return;
  }
  
  // Показываем промпт установки
  deferredPrompt.prompt();
  
  // Ждем выбора пользователя
  const { outcome } = await deferredPrompt.userChoice;
  console.log('[PWA] User choice:', outcome);
  
  if (outcome === 'accepted') {
    console.log('[PWA] App installed');
    // Отправляем событие в аналитику
    if (typeof gtag !== 'undefined') {
      gtag('event', 'pwa_install', {
        event_category: 'engagement',
        event_label: 'PWA Installed'
      });
    }
  }
  
  // Убираем кнопку установки
  if (installButton) {
    installButton.style.display = 'none';
  }
  
  deferredPrompt = null;
}

// Обработка успешной установки
window.addEventListener('appinstalled', (e) => {
  console.log('[PWA] App installed successfully');
  
  // Убираем кнопку установки
  if (installButton) {
    installButton.style.display = 'none';
  }
  
  // Показываем уведомление
  if (typeof showToast !== 'undefined') {
    showToast('Приложение успешно установлено!', 'success');
  }
});

// Проверка, запущено ли приложение в standalone режиме
function isStandalone() {
  return window.matchMedia('(display-mode: standalone)').matches ||
         window.navigator.standalone === true;
}

// Скрываем кнопку установки, если уже в standalone режиме
if (isStandalone()) {
  console.log('[PWA] Running in standalone mode');
  if (installButton) {
    installButton.style.display = 'none';
  }
}

// Обработка обновлений Service Worker
navigator.serviceWorker?.addEventListener('controllerchange', () => {
  console.log('[PWA] New service worker activated');
  
  // Показываем уведомление об обновлении
  if (confirm('Доступна новая версия приложения. Обновить сейчас?')) {
    window.location.reload();
  }
});

// Функция для показа тостов (если нет глобальной)
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  toast.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    background: ${type === 'success' ? '#10b981' : '#6366f1'};
    color: white;
    padding: 15px 20px;
    border-radius: 10px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    z-index: 10000;
    animation: slideInRight 0.3s ease;
  `;
  
  document.body.appendChild(toast);
  
  setTimeout(() => {
    toast.style.animation = 'slideOutRight 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// Обработка офлайн/онлайн состояния
window.addEventListener('online', () => {
  console.log('[PWA] Back online');
  showToast('Соединение восстановлено', 'success');
});

window.addEventListener('offline', () => {
  console.log('[PWA] Gone offline');
  showToast('Нет подключения к интернету', 'warning');
});
