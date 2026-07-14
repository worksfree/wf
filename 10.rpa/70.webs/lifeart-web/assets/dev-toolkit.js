// LifeArt Dev 툴킷 — ?dev=123 으로 활성화, 테스트 계정 원클릭 로그인.
//
// 보안: test-lifeart / pre-test-lifeart / localhost 에서만 동작.
//       production(www.lifeart.ai.kr)에서는 ?dev=123 을 붙여도 절대 뜨지 않음.
//
// 흐름: 툴킷의 테스트 계정 클릭 → 로그인 페이지로 이동하며 이메일/비번 프리필
//       → Enter(또는 로그인 버튼) → 실제 로그인.
(function () {
  var host = location.hostname;
  var DEV_HOSTS_OK = host.startsWith('test-lifeart.')
    || host.startsWith('pre-test-lifeart.')
    || host === 'localhost' || host === '127.0.0.1';
  if (!DEV_HOSTS_OK) return;
  // 단계 5 부터 오픈 (테스트 데이터·Dev 툴킷)
  if (typeof stageAtLeast === 'function' && !stageAtLeast(5)) return;

  // 활성화 상태 유지 (?dev=123 최초 진입 후 세션 내 유지)
  var qs = new URLSearchParams(location.search);
  if (qs.get('dev') === '123') sessionStorage.setItem('lifeart_dev', '1');
  if (sessionStorage.getItem('lifeart_dev') !== '1') return;

  // 테스트 계정 (throwaway — pre-test 환경 전용, 실계정 아님)
  var DEV_ACCOUNTS = [
    { label: '테스트 회원', email: 'lifeart.tester@worksfree.kr',       password: 'LifeArt!test2026' },
    { label: '테스트 관리자', email: 'lifeart.admin.test@worksfree.kr', password: 'LifeArt!admin2026' },
  ];

  // 로그인 페이지면: 프리필 요청이 있으면 폼 채우고 포커스
  if (location.pathname.indexOf('/auth/login') === 0) {
    var pf = sessionStorage.getItem('lifeart_dev_prefill');
    if (pf) {
      sessionStorage.removeItem('lifeart_dev_prefill');
      try {
        var c = JSON.parse(pf);
        var tryFill = function () {
          var form = document.getElementById('login-form');
          if (!form) return setTimeout(tryFill, 100);
          form.email.value = c.email;
          form.password.value = c.password;
          form.password.focus();
        };
        tryFill();
      } catch (e) {}
    }
  }

  function login(acc) {
    // 로그인 페이지가 아니면 이동하면서 프리필 전달
    if (location.pathname.indexOf('/auth/login') !== 0) {
      sessionStorage.setItem('lifeart_dev_prefill', JSON.stringify(acc));
      location.href = '/auth/login/';
      return;
    }
    var form = document.getElementById('login-form');
    if (form) { form.email.value = acc.email; form.password.value = acc.password; form.password.focus(); }
  }

  function render() {
    if (document.getElementById('lifeart-dev-toolkit')) return;
    var box = document.createElement('div');
    box.id = 'lifeart-dev-toolkit';
    box.innerHTML =
      '<div class="ldt-head">🛠 DEV <span class="ldt-env"></span><span class="ldt-x">×</span></div>' +
      '<div class="ldt-body"><div class="ldt-label">테스트 계정 (클릭 → 로그인)</div><div class="ldt-accts"></div>' +
      '<button class="ldt-logout">로그아웃</button></div>';
    document.body.appendChild(box);

    var envName = host.startsWith('pre-test-lifeart.') ? 'pre-test'
                : host.startsWith('test-lifeart.') ? 'test' : 'local';
    box.querySelector('.ldt-env').textContent = envName;

    var accts = box.querySelector('.ldt-accts');
    DEV_ACCOUNTS.forEach(function (acc) {
      var b = document.createElement('button');
      b.className = 'ldt-acct';
      b.innerHTML = '<b>' + acc.label + '</b><span>' + acc.email + '</span>';
      b.onclick = function () { login(acc); };
      accts.appendChild(b);
    });

    box.querySelector('.ldt-logout').onclick = function () {
      if (window.sb) sb.auth.signOut().then(function () { location.href = '/'; });
    };
    box.querySelector('.ldt-x').onclick = function () {
      sessionStorage.removeItem('lifeart_dev'); box.remove();
    };
  }

  var style = document.createElement('style');
  style.textContent =
    '#lifeart-dev-toolkit{position:fixed;right:16px;bottom:16px;z-index:9999;width:230px;' +
    'font-family:-apple-system,sans-serif;background:#2C2C2C;color:#eee;border-radius:10px;' +
    'box-shadow:0 8px 28px rgba(0,0,0,.35);overflow:hidden;font-size:12px}' +
    '#lifeart-dev-toolkit .ldt-head{background:#1a1a1a;color:#C4A962;padding:8px 12px;font-weight:700;' +
    'display:flex;align-items:center;gap:6px}' +
    '#lifeart-dev-toolkit .ldt-env{background:#C4A962;color:#1a1a1a;font-size:10px;padding:1px 6px;border-radius:4px}' +
    '#lifeart-dev-toolkit .ldt-x{margin-left:auto;cursor:pointer;font-size:16px;color:#888}' +
    '#lifeart-dev-toolkit .ldt-body{padding:12px}' +
    '#lifeart-dev-toolkit .ldt-label{color:#999;margin-bottom:8px}' +
    '#lifeart-dev-toolkit .ldt-acct{display:block;width:100%;text-align:left;background:#3a3a3a;border:none;' +
    'color:#eee;padding:8px 10px;border-radius:6px;margin-bottom:6px;cursor:pointer}' +
    '#lifeart-dev-toolkit .ldt-acct:hover{background:#C4A962;color:#1a1a1a}' +
    '#lifeart-dev-toolkit .ldt-acct b{display:block;font-size:12px}' +
    '#lifeart-dev-toolkit .ldt-acct span{display:block;font-size:10px;opacity:.7}' +
    '#lifeart-dev-toolkit .ldt-logout{width:100%;background:none;border:1px solid #555;color:#bbb;' +
    'padding:6px;border-radius:6px;cursor:pointer;margin-top:4px}';
  document.head.appendChild(style);

  if (document.body) render();
  else document.addEventListener('DOMContentLoaded', render);
})();
