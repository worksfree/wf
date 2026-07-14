// ── 웹접근성(KWCAG 3.3.2 레이블 제공): .form-row 의 라벨↔입력요소를 for/id 로 자동 연결 ──
//   시각적으로만 인접해 있던 라벨을 프로그래밍적으로 연결해 스크린리더가 올바로 읽게 한다.
//   (라벨이 입력을 감싸는 동의 체크박스 등은 이미 연결돼 있으므로 건너뜀)
(function associateFormLabels() {
  var n = 0;
  document.querySelectorAll('.form-row').forEach(function (row) {
    var label = row.querySelector(':scope > label');
    var field = row.querySelector('input, select, textarea');
    if (label && field && !label.contains(field) && !field.id && !label.htmlFor) {
      var id = 'fld-' + (++n) + '-' + Math.random().toString(36).slice(2, 6);
      field.id = id;
      label.setAttribute('for', id);
    }
  });
  // KWCAG 4.1.3(상태 메시지): 폼 성공/오류 메시지를 스크린리더가 자동 낭독하도록 라이브 영역화
  document.querySelectorAll('.form-msg').forEach(function (el) {
    if (!el.getAttribute('aria-live')) { el.setAttribute('role', 'status'); el.setAttribute('aria-live', 'polite'); }
  });

  // KWCAG 3.3.1(오류 정정): 폼의 입력요소를 해당 폼의 상태메시지에 aria-describedby 로 연결
  document.querySelectorAll('form').forEach(function (f) {
    var msg = f.querySelector('.form-msg'); if (!msg) return;
    if (!msg.id) msg.id = 'fmsg-' + Math.random().toString(36).slice(2, 6);
    f.querySelectorAll('input, select, textarea').forEach(function (fld) {
      var d = fld.getAttribute('aria-describedby');
      if (!d || d.indexOf(msg.id) < 0) fld.setAttribute('aria-describedby', d ? d + ' ' + msg.id : msg.id);
    });
  });

  // KWCAG 1.3.1(표의 구성): 데이터 표의 <th> 에 scope 자동 부여 (thead=열, 행 첫 th=행)
  document.querySelectorAll('table').forEach(function (t) {
    t.querySelectorAll('tr').forEach(function (tr) {
      if (tr.closest('thead')) { tr.querySelectorAll('th').forEach(function (th) { if (!th.getAttribute('scope')) th.setAttribute('scope', 'col'); }); return; }
      var kids = Array.prototype.slice.call(tr.children);
      var ths = kids.filter(function (c) { return c.tagName === 'TH'; });
      var tds = kids.filter(function (c) { return c.tagName === 'TD'; });
      if (ths.length && !tds.length) { ths.forEach(function (th) { if (!th.getAttribute('scope')) th.setAttribute('scope', 'col'); }); }
      else if (ths.length) { if (!ths[0].getAttribute('scope')) ths[0].setAttribute('scope', 'row'); }
    });
  });

  // KWCAG 4.1.2(이름·역할·값): 탭 UI 에 ARIA 탭 패턴 부여 + 선택상태 동기화
  document.querySelectorAll('.tab-row').forEach(function (row) {
    row.setAttribute('role', 'tablist');
    var btns = Array.prototype.slice.call(row.querySelectorAll('.tab-btn'));
    btns.forEach(function (b) {
      b.setAttribute('role', 'tab');
      b.setAttribute('aria-selected', b.classList.contains('active') ? 'true' : 'false');
      var panel = b.dataset.tab ? document.getElementById('tab-' + b.dataset.tab) : null;
      if (panel) {
        if (!b.id) b.id = 'tabbtn-' + b.dataset.tab;
        panel.setAttribute('role', 'tabpanel');
        b.setAttribute('aria-controls', panel.id);
        panel.setAttribute('aria-labelledby', b.id);
      }
      b.addEventListener('click', function () {
        btns.forEach(function (x) { x.setAttribute('aria-selected', 'false'); });
        b.setAttribute('aria-selected', 'true');
      });
    });
  });
})();

// 공통 헤더/푸터 삽입 (반복되는 30여 개 페이지의 유지보수를 위해 분리)
//  · 배포 시 deploy.ps1 이 각 페이지에 파트셜을 인라인 주입 → 이 경우 fetch 생략(헤더 깜빡임 제거)
//  · 로컬(localhost 등 미주입)에서는 기존처럼 fetch 로 채운다
(async function () {
  const headerSlot = document.getElementById('site-header');
  const footerSlot = document.getElementById('site-footer');
  const alreadyInlined = headerSlot && headerSlot.children.length > 0;

  if (!alreadyInlined) {
    const [headerHtml, footerHtml] = await Promise.all([
      fetch('/assets/header.html').then(r => r.text()),
      fetch('/assets/footer.html').then(r => r.text()),
    ]);
    if (headerSlot) headerSlot.outerHTML = headerHtml;
    if (footerSlot) footerSlot.outerHTML = footerHtml;
  }
  // ★ 인라인 주입 시 fetch(await)가 없어 이 IIFE가 동기적으로 끝나므로,
  //   페이지 하단 인라인 스크립트(initAdmin 등)가 'layout:ready' 리스너를
  //   등록하기 전에 이벤트가 터지는 레이스가 생긴다. setTimeout(0)으로 다음
  //   매크로태스크에 발화 → 모든 인라인 리스너 등록 후 안전하게 실행되게 한다.
  window.__layoutReady = false;
  setTimeout(function () {
    window.__layoutReady = true;
    document.dispatchEvent(new CustomEvent('layout:ready'));
  }, 0);
})();
