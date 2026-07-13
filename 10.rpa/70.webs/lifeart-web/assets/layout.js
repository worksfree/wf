// 공통 헤더/푸터 삽입 (반복되는 30여 개 페이지의 유지보수를 위해 분리)
(async function () {
  const [headerHtml, footerHtml] = await Promise.all([
    fetch('/assets/header.html').then(r => r.text()),
    fetch('/assets/footer.html').then(r => r.text()),
  ]);
  const headerSlot = document.getElementById('site-header');
  const footerSlot = document.getElementById('site-footer');
  if (headerSlot) headerSlot.outerHTML = headerHtml;
  if (footerSlot) footerSlot.outerHTML = footerHtml;
  document.dispatchEvent(new CustomEvent('layout:ready'));
})();
