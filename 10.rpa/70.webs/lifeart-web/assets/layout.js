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
  document.dispatchEvent(new CustomEvent('layout:ready'));
})();
